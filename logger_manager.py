import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

class DailyLogManager:
    """Gestionnaire de logs quotidiens avec rotation automatique"""
    
    def __init__(self, config):
        self.config = config
        self.log_dir = Path(config.LOG_DIR)
        self.log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        self.log_format = config.LOG_FORMAT
        self.max_days = config.LOG_MAX_DAYS
        self.file_prefix = config.LOG_FILE_PREFIX
        self._setup_log_directory()
        
    def _setup_log_directory(self):
        """Crée le répertoire de logs s'il n'existe pas"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer les sous-répertoires pour l'organisation
        self.daily_dir = self.log_dir / 'daily'
        self.error_dir = self.log_dir / 'errors'
        self.archive_dir = self.log_dir / 'archive'
        
        self.daily_dir.mkdir(exist_ok=True)
        self.error_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)
    
    def get_daily_log_filename(self, date: Optional[datetime] = None) -> str:
        """Génère le nom du fichier de log quotidien"""
        if date is None:
            date = datetime.now()
        return f"{self.file_prefix}_{date.strftime('%Y-%m-%d')}.log"
    
    def get_daily_log_path(self, date: Optional[datetime] = None) -> Path:
        """Retourne le chemin complet du fichier de log quotidien"""
        return self.daily_dir / self.get_daily_log_filename(date)
    
    def setup_logger(self, name: str = 'SiteMonitor') -> logging.Logger:
        """Configure le logger avec rotation quotidienne"""
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Éviter les doublons de handlers
        logger.handlers.clear()
        
        # Handler pour les logs quotidiens (tous les logs)
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.get_daily_log_path(),
            when='midnight',
            interval=1,
            backupCount=self.max_days,
            encoding='utf-8'
        )
        daily_handler.setLevel(self.log_level)
        daily_handler.setFormatter(self._get_formatter())
        logger.addHandler(daily_handler)
        
        # Handler pour les erreurs uniquement (fichier séparé)
        error_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.error_dir / f"errors_{datetime.now().strftime('%Y-%m-%d')}.log",
            when='midnight',
            interval=1,
            backupCount=self.max_days,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_formatter())
        logger.addHandler(error_handler)
        
        # Handler pour la console (optionnel en production)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Seulement WARNING et plus en console
        console_handler.setFormatter(self._get_formatter())
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_formatter(self) -> logging.Formatter:
        """Retourne le formateur selon la configuration"""
        if self.log_format == 'json':
            return JsonFormatter()
        elif self.log_format == 'detailed':
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
        else:  # simple
            return logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
    
    def write_status_summary(self, date_str: str, summary: dict):
        """Écrit un résumé quotidien de l'état du monitoring"""
        summary_file = self.daily_dir / f"summary_{date_str}.json"
        
        # Charger le résumé existant s'il existe
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                existing_summary = json.load(f)
            existing_summary.update(summary)
            summary = existing_summary
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def get_status_for_date(self, date_str: str) -> Optional[dict]:
        """Récupère le résumé d'une date spécifique"""
        summary_file = self.daily_dir / f"summary_{date_str}.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def cleanup_old_logs(self):
        """Nettoie les logs plus anciens que max_days"""
        import time
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=self.max_days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        for directory in [self.daily_dir, self.error_dir]:
            for file in directory.glob('*.log'):
                if file.stat().st_mtime < cutoff_timestamp:
                    try:
                        # Archiver avant de supprimer
                        archive_path = self.archive_dir / file.name
                        file.rename(archive_path)
                    except Exception as e:
                        logging.warning(f"Impossible d'archiver {file}: {e}")


class JsonFormatter(logging.Formatter):
    """Formateur JSON pour les logs"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info and record.exc_info[0]:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


class MonitoringLogger:
    """Logger spécifique pour le monitoring avec statistiques"""
    
    def __init__(self, log_manager: DailyLogManager, site_url: str):
        self.log_manager = log_manager
        self.site_url = site_url
        self.logger = log_manager.setup_logger('MonitorStatus')
        self.daily_stats = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'site_url': site_url,
            'total_checks': 0,
            'success_count': 0,
            'failure_count': 0,
            'warning_count': 0,
            'last_check': None,
            'last_status': None,
            'checks': []
        }
        self._load_daily_stats()
    
    def _load_daily_stats(self):
        """Charge les statistiques du jour si elles existent"""
        today = datetime.now().strftime('%Y-%m-%d')
        existing = self.log_manager.get_status_for_date(today)
        if existing:
            self.daily_stats = existing
    
    def _save_daily_stats(self):
        """Sauvegarde les statistiques du jour"""
        self.log_manager.write_status_summary(
            self.daily_stats['date'],
            self.daily_stats
        )
    
    def log_check(self, status: str, details: dict = None):
        """Enregistre un check avec son statut"""
        now = datetime.now()
        
        # Mise à jour des statistiques
        self.daily_stats['total_checks'] += 1
        if status == 'OK':
            self.daily_stats['success_count'] += 1
            self.logger.info(f"✅ CHECK OK - {self.site_url}")
        elif status == 'WARNING':
            self.daily_stats['warning_count'] += 1
            self.logger.warning(f"⚠️ CHECK WARNING - {self.site_url}")
        else:
            self.daily_stats['failure_count'] += 1
            self.logger.error(f"❌ CHECK FAILED - {self.site_url} - Erreur: {details}")
        
        self.daily_stats['last_check'] = now.isoformat()
        self.daily_stats['last_status'] = status
        
        # Ajouter le check à l'historique
        check_record = {
            'timestamp': now.isoformat(),
            'status': status,
            'details': details or {}
        }
        self.daily_stats['checks'].append(check_record)
        
        # Garder seulement les 1000 derniers checks en mémoire
        if len(self.daily_stats['checks']) > 1000:
            self.daily_stats['checks'] = self.daily_stats['checks'][-1000:]
        
        self._save_daily_stats()
    
    def get_daily_summary(self) -> str:
        """Retourne un résumé textuel de la journée"""
        stats = self.daily_stats
        uptime = (stats['success_count'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 0
        
        summary = f"""
        📊 Résumé du {stats['date']}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━
        Site: {stats['site_url']}
        Checks totaux: {stats['total_checks']}
        ✅ Succès: {stats['success_count']}
        ⚠️ Warnings: {stats['warning_count']}
        ❌ Échecs: {stats['failure_count']}
        📈 Uptime: {uptime:.2f}%
        🕐 Dernier check: {stats['last_check']}
        📌 Dernier statut: {stats['last_status']}
        """
        return summary
    
    def write_hourly_log(self, status: str, response_time: float = None):
        """Écrit un log horaire avec le statut"""
        now = datetime.now()
        log_entry = f"{now.strftime('%Y-%m-%d %H:%M:%S')} | Site: {self.site_url} | Status: {status}"
        
        if response_time:
            log_entry += f" | Response Time: {response_time:.2f}s"
        
        hourly_file = self.log_manager.daily_dir / f"hourly_{now.strftime('%Y-%m-%d_%H')}.log"
        with open(hourly_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')