import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Service de notification par email"""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 smtp_user: str, smtp_password: str,
                 from_email: str, to_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_email = to_email
        
    def send_alert(self, monitor_results: Dict):
        """Envoie une alerte par email aux destinataires"""
        if monitor_results['global_status'] == 'OK':
            logger.info("Aucune alerte à envoyer - statut OK")
            return
            
        subject = self._create_subject(monitor_results)
        body = self._create_body(monitor_results)
        
        # Convertir en liste si c'est une chaîne unique (rétrocompatibilité)
        recipients = self.to_email if isinstance(self.to_email, list) else [self.to_email]
        
        for recipient in recipients:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.from_email
                msg['To'] = recipient
                
                msg.attach(MIMEText(body, 'html', 'utf-8'))
                
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                    logger.info(f"Email d'alerte envoyé à {recipient}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email à {recipient}: {str(e)}")
                
    def _create_subject(self, results: Dict) -> str:
        """Crée le sujet de l'email selon le type d'erreur"""
        status = results['global_status']
        url = results['url']
        
        if status == 'ERROR':
            return f"🔴 ALERTE: Site {url} en erreur"
        elif status == 'WARNING':
            return f"🟡 ATTENTION: Problème détecté sur {url}"
        return f"Information: {url}"
    
    def _create_body(self, results: Dict) -> str:
        """Crée le corps HTML de l'email"""
        http = results['http_check']
        ssl = results['ssl_check']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .error {{ color: red; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
                .ok {{ color: green; }}
                table {{ border-collapse: collapse; width: 100%; }}
                td, th {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>Rapport de surveillance - {timestamp}</h2>
            
            <h3>Site surveillé: {results['url']}</h3>
            <p>Statut global: <span class="{results['global_status'].lower()}">{results['global_status']}</span></p>
            
            <h3>Vérification HTTP</h3>
            <table>
                <tr><td>Statut</td><td class="{http['status'].lower()}">{http['status']}</td></tr>
                <tr><td>Code HTTP</td><td>{http.get('status_code', 'N/A')}</td></tr>
                <tr><td>Temps de réponse</td><td>{http.get('response_time', 'N/A')}s</td></tr>
                <tr><td>Erreur</td><td class="error">{http.get('error', 'Aucune')}</td></tr>
            </table>
        """
        
        if ssl:
            body += f"""
            <h3>Vérification SSL</h3>
            <table>
                <tr><td>Statut</td><td class="{ssl['status'].lower()}">{ssl['status']}</td></tr>
                <tr><td>Émetteur</td><td>{ssl.get('issuer', 'N/A')}</td></tr>
                <tr><td>Date d'expiration</td><td>{ssl.get('expiry_date', 'N/A')}</td></tr>
                <tr><td>Jours restants</td><td>{ssl.get('days_remaining', 'N/A')}</td></tr>
                <tr><td>Erreur</td><td class="error">{ssl.get('error', 'Aucune')}</td></tr>
            </table>
            """
            
        body += """
            <hr>
            <p style="font-size: 12px; color: gray;">
                Cet email a été envoyé automatiquement par le service de monitoring.
            </p>
        </body>
        </html>
        """
        
        return body