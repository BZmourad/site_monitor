import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration chargée depuis les variables d'environnement"""
    
    # URL du site à surveiller
    SITE_URL = [url.strip() for url in os.getenv('SITE_URL', 'https://example.com').split(',') if url.strip()]
    
    # Intervalle de vérification en secondes
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))
    
    # Configuration SMTP
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER)
    #TO_EMAIL = os.getenv('TO_EMAIL', '')
    TO_EMAIL = [email.strip() for email in os.getenv('TO_EMAIL', '').split(',') if email.strip()]
    
    # Timeout pour les requêtes
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    
    # Vérification SSL
    CHECK_SSL = os.getenv('CHECK_SSL', 'true').lower() == 'true'
    
    # Configuration des logs
    LOG_DIR = os.getenv('LOG_DIR', './logs')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'detailed')
    LOG_MAX_DAYS = int(os.getenv('LOG_MAX_DAYS', 30))
    LOG_FILE_PREFIX = os.getenv('LOG_FILE_PREFIX', 'monitor')
    
    @classmethod
    def validate(cls):
        """Valide la configuration"""
        errors = []
        
        if not cls.SITE_URL or len(cls.SITE_URL) == 0:
            errors.append("SITE_URL est requis (au moins une URL)")
        
        if not cls.SMTP_USER or not cls.SMTP_PASSWORD:
            errors.append("Configuration email SMTP incomplète")
            
        if not cls.TO_EMAIL or len(cls.TO_EMAIL) == 0:
            errors.append("TO_EMAIL est requis (au moins un email)")
            
        return errors