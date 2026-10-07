#!/usr/bin/env python3
"""
Service de surveillance de site web
Vérifie périodiquement l'état d'un site et envoie des alertes par email
Avec logs quotidiens détaillés
"""

import time
import schedule
import sys
from datetime import datetime
from config import Config
from monitor import SiteMonitor
from notifier import EmailNotifier
from logger_manager import DailyLogManager, MonitoringLogger

class MonitoringService:
    """Service principal de monitoring"""
    
    def __init__(self):
        self.config = Config()
        
        # Initialisation du gestionnaire de logs
        self.log_manager = DailyLogManager(self.config)
        self.logger = self.log_manager.setup_logger()
        
        # Un monitor logger par site
        self.monitor_loggers = {}
        for site_url in self.config.SITE_URL:
            self.monitor_loggers[site_url] = MonitoringLogger(
                self.log_manager, 
                site_url
            )
        
        # Un monitor par site
        self.monitors = {}
        for site_url in self.config.SITE_URL:
            self.monitors[site_url] = SiteMonitor(
                url=site_url,
                timeout=self.config.REQUEST_TIMEOUT,
                check_ssl=self.config.CHECK_SSL
            )
        
        self.notifier = EmailNotifier(
            smtp_host=self.config.SMTP_HOST,
            smtp_port=self.config.SMTP_PORT,
            smtp_user=self.config.SMTP_USER,
            smtp_password=self.config.SMTP_PASSWORD,
            from_email=self.config.FROM_EMAIL,
            to_email=self.config.TO_EMAIL
        )
        
        # Compteur d'échecs par site
        self.failure_counts = {url: 0 for url in self.config.SITE_URL}
        self.max_consecutive_failures = 1
        self.start_time = datetime.now()
        
    def test_email_configuration(self):
        """Teste la configuration email"""
        self.logger.info("Test de la configuration email...")
        try:
            import smtplib
            with smtplib.SMTP(self.config.SMTP_HOST, self.config.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                self.logger.info("✅ Configuration email OK")
                return True
        except Exception as e:
            self.logger.error(f"❌ Erreur de configuration email: {e}")
            return False
    
    def test_site_connectivity(self):
        """Teste la connectivité initiale de tous les sites"""
        all_ok = True
        for site_url in self.config.SITE_URL:
            self.logger.info(f"Test de connectivité vers {site_url}...")
            import requests
            try:
                response = requests.get(
                    site_url, 
                    timeout=10,
                    verify=self.config.CHECK_SSL
                )
                self.logger.info(f"✅ {site_url} accessible - Code HTTP: {response.status_code}")
            except Exception as e:
                self.logger.error(f"❌ Erreur de connexion vers {site_url}: {e}")
                all_ok = False
        return all_ok
    
    def run_check(self):
        """Exécute une vérification complète sur tous les sites"""
        for site_url in self.config.SITE_URL:
            self.logger.debug(f"Début de la vérification pour {site_url}")
            
            try:
                monitor = self.monitors[site_url]
                monitor_logger = self.monitor_loggers[site_url]
                
                results = monitor.check_all()
                status = results['global_status']
                
                # Logger le résultat
                details = {
                    'http_status': results['http_check'].get('status_code'),
                    'response_time': results['http_check'].get('response_time'),
                    'error': results['http_check'].get('error')
                }
                monitor_logger.log_check(status, details)
                
                # Log horaire détaillé
                if status == 'OK':
                    monitor_logger.write_hourly_log(
                        status, 
                        results['http_check'].get('response_time')
                    )
                else:
                    monitor_logger.write_hourly_log(status)
                
                if status != 'OK':
                    self.failure_counts[site_url] += 1
                    count = self.failure_counts[site_url]
                    self.logger.warning(f"Problème sur {site_url} (échec {count}/{self.max_consecutive_failures})")
                    
                    if count >= self.max_consecutive_failures:
                        self.notifier.send_alert(results)
                        self.logger.info(f"Alerte email envoyée pour {site_url}")
                    else:
                        self.logger.info(f"En attente de {self.max_consecutive_failures} échecs pour {site_url}")
                else:
                    if self.failure_counts[site_url] > 0:
                        self.logger.info(f"✅ {site_url} rétabli après échecs")
                        recovery_results = results.copy()
                        recovery_results['global_status'] = 'RECOVERY'
                        self.notifier.send_alert(recovery_results)
                    self.failure_counts[site_url] = 0
                
                self._log_results(results)
                
            except Exception as e:
                self.logger.error(f"Erreur lors de la vérification de {site_url}: {str(e)}", exc_info=True)
                self.failure_counts[site_url] += 1
                if site_url in self.monitor_loggers:
                    self.monitor_loggers[site_url].log_check('ERROR', {'error': str(e)})
    
    def _log_results(self, results):
        """Affiche les résultats détaillés dans les logs"""
        http = results['http_check']
        self.logger.debug(f"HTTP - Status: {http['status']}, Code: {http.get('status_code')}, "
                         f"Temps: {http.get('response_time', 'N/A')}s")
        
        if results['ssl_check']:
            ssl = results['ssl_check']
            self.logger.debug(f"SSL - Status: {ssl['status']}, "
                            f"Expire: {ssl.get('expiry_date', 'N/A')}, "
                            f"Jours restants: {ssl.get('days_remaining', 'N/A')}")
    
    def print_daily_summary(self):
        """Affiche le résumé quotidien pour tous les sites"""
        for site_url in self.config.SITE_URL:
            summary = self.monitor_loggers[site_url].get_daily_summary()
            self.logger.info(summary)
    
    def start(self):
        """Démarre le service de monitoring"""
        # Valide la configuration
        errors = self.config.validate()
        if errors:
            self.logger.error("Erreurs de configuration:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return
        
        self.logger.info("=" * 50)
        self.logger.info("🚀 Démarrage du service de monitoring")
        self.logger.info("=" * 50)
        self.logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sites = ', '.join(self.config.SITE_URL)
        self.logger.info(f"🌐 Sites à surveiller ({len(self.config.SITE_URL)}): {sites}")
        self.logger.info(f"⏱️  Intervalle: {self.config.CHECK_INTERVAL}s")
        self.logger.info(f"🔒 Vérification SSL: {'Activée' if self.config.CHECK_SSL else 'Désactivée'}")
        emails = ', '.join(self.config.TO_EMAIL)
        self.logger.info(f"📧 Alertes envoyées à: {emails}")
        self.logger.info(f"📁 Répertoire des logs: {self.config.LOG_DIR}")
        self.logger.info(f"📝 Conservation des logs: {self.config.LOG_MAX_DAYS} jours")
        self.logger.info("=" * 50)
        
        # Tests initiaux
        self.logger.info("\n🔍 Tests de configuration...")
        email_ok = self.test_email_configuration()
        site_ok = self.test_site_connectivity()
        
        if not email_ok:
            self.logger.warning("⚠️ Les notifications email ne fonctionneront pas!")
        
        if not site_ok:
            self.logger.warning("⚠️ Au moins un site semble inaccessible!")
        
        # Planification des tâches
        schedule.every(self.config.CHECK_INTERVAL).seconds.do(self.run_check)
        
        # Résumé quotidien à 23h59
        schedule.every().day.at("23:59").do(self.print_daily_summary)
        
        # Nettoyage des vieux logs une fois par jour
        schedule.every().day.at("00:00").do(self.log_manager.cleanup_old_logs)
        
        self.logger.info("\n✅ Service démarré - Surveillance en cours...")
        self.logger.info("Appuyez sur Ctrl+C pour arrêter\n")
        
        # Première vérification immédiate
        self.run_check()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("\n" + "=" * 50)
            self.logger.info("Arrêt du service demandé")
            
            # Afficher le résumé final
            self.print_daily_summary()
            
            uptime = datetime.now() - self.start_time
            self.logger.info(f"⏱️ Durée d'exécution: {uptime}")
            self.logger.info("Service arrêté")
            self.logger.info("=" * 50)
            sys.exit(0)

def main():
    """Point d'entrée principal"""
    service = MonitoringService()
    service.start()

if __name__ == "__main__":
    main()