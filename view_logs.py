#!/usr/bin/env python3
"""
Script pour consulter et analyser les logs de monitoring
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse
from logger_manager import DailyLogManager
from config import Config

class LogViewer:
    def __init__(self):
        self.config = Config()
        self.log_manager = DailyLogManager(self.config)
    
    def show_today_summary(self):
        """Affiche le résumé du jour"""
        today = datetime.now().strftime('%Y-%m-%d')
        summary = self.log_manager.get_status_for_date(today)
        
        if summary:
            print(f"\n📊 Résumé du {today}")
            print("=" * 40)
            print(f"Site: {summary['site_url']}")
            print(f"Checks totaux: {summary['total_checks']}")
            print(f"✅ Succès: {summary['success_count']}")
            print(f"⚠️ Warnings: {summary['warning_count']}")
            print(f"❌ Échecs: {summary['failure_count']}")
            
            if summary['total_checks'] > 0:
                uptime = (summary['success_count'] / summary['total_checks']) * 100
                print(f"📈 Uptime: {uptime:.2f}%")
            
            print(f"🕐 Dernier check: {summary['last_check']}")
            print(f"📌 Dernier statut: {summary['last_status']}")
            
            # Afficher les 5 derniers checks
            if 'checks' in summary and summary['checks']:
                print(f"\n📋 Derniers checks:")
                for check in summary['checks'][-5:]:
                    status_emoji = "✅" if check['status'] == 'OK' else "❌" if check['status'] == 'ERROR' else "⚠️"
                    print(f"  {status_emoji} {check['timestamp']} - {check['status']}")
        else:
            print(f"❌ Pas de données pour aujourd'hui ({today})")
    
    def show_date_summary(self, date_str):
        """Affiche le résumé d'une date spécifique"""
        summary = self.log_manager.get_status_for_date(date_str)
        
        if summary:
            print(f"\n📊 Résumé du {date_str}")
            print("=" * 40)
            print(f"Site: {summary['site_url']}")
            print(f"Checks totaux: {summary['total_checks']}")
            print(f"✅ Succès: {summary['success_count']}")
            print(f"⚠️ Warnings: {summary['warning_count']}")
            print(f"❌ Échecs: {summary['failure_count']}")
            
            if summary['total_checks'] > 0:
                uptime = (summary['success_count'] / summary['total_checks']) * 100
                print(f"📈 Uptime: {uptime:.2f}%")
        else:
            print(f"❌ Pas de données pour le {date_str}")
    
    def show_recent_errors(self, hours=24):
        """Affiche les erreurs récentes"""
        error_file = self.log_manager.error_dir / f"errors_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        if error_file.exists():
            cutoff = datetime.now() - timedelta(hours=hours)
            
            print(f"\n🔴 Erreurs des dernières {hours} heures:")
            print("=" * 40)
            
            with open(error_file, 'r', encoding='utf-8') as f:
                error_count = 0
                for line in f:
                    try:
                        # Extraire la date du log
                        log_date = datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S,%f')
                        if log_date > cutoff:
                            print(line.strip())
                            error_count += 1
                    except:
                        pass
                
                if error_count == 0:
                    print("✅ Aucune erreur récente")
                else:
                    print(f"\nTotal: {error_count} erreurs")
        else:
            print("✅ Aucun fichier d'erreurs trouvé")
    
    def show_live_logs(self, follow=False):
        """Affiche les logs en direct"""
        log_file = self.log_manager.get_daily_log_path()
        
        if not log_file.exists():
            print(f"❌ Fichier de log non trouvé: {log_file}")
            return
        
        print(f"📝 Affichage des logs en direct de {log_file}")
        print("Appuyez sur Ctrl+C pour arrêter\n")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            if follow:
                # Aller à la fin du fichier
                f.seek(0, 2)
                
                try:
                    while True:
                        line = f.readline()
                        if line:
                            print(line.strip())
                        else:
                            import time
                            time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\n✅ Arrêt de l'affichage des logs")
            else:
                # Afficher les 50 dernières lignes
                lines = f.readlines()
                for line in lines[-50:]:
                    print(line.strip())

def main():
    parser = argparse.ArgumentParser(description='Visualiseur de logs de monitoring')
    parser.add_argument('--today', action='store_true', help='Afficher le résumé du jour')
    parser.add_argument('--date', type=str, help='Afficher le résumé d\'une date (YYYY-MM-DD)')
    parser.add_argument('--errors', type=int, nargs='?', const=24, help='Afficher les erreurs récentes (heures)')
    parser.add_argument('--live', action='store_true', help='Afficher les logs en direct')
    parser.add_argument('--follow', action='store_true', help='Suivre les logs en continu')
    
    args = parser.parse_args()
    viewer = LogViewer()
    
    if args.today:
        viewer.show_today_summary()
    elif args.date:
        viewer.show_date_summary(args.date)
    elif args.errors is not None:
        viewer.show_recent_errors(args.errors)
    elif args.live or args.follow:
        viewer.show_live_logs(follow=args.follow)
    else:
        # Par défaut, afficher le résumé du jour
        viewer.show_today_summary()

if __name__ == "__main__":
    main()