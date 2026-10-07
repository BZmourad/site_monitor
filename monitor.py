import requests
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SiteMonitor:
    """Moniteur de site web avec vérification HTTP et SSL"""
    
    def __init__(self, url: str, timeout: int = 30, check_ssl: bool = True):
        self.url = url
        self.timeout = timeout
        self.check_ssl = check_ssl
        self.parsed_url = urlparse(url)
        self.hostname = self.parsed_url.hostname
        
    def check_http(self) -> Dict:
        """Vérifie si le site répond correctement en HTTP/HTTPS"""
        result = {
            'status': 'OK',
            'status_code': None,
            'response_time': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            start_time = datetime.now()
            response = requests.get(
                self.url,
                timeout=self.timeout,
                verify=self.check_ssl,
                allow_redirects=True
            )
            end_time = datetime.now()
            
            result['response_time'] = (end_time - start_time).total_seconds()
            result['status_code'] = response.status_code
            
            if response.status_code >= 400:
                result['status'] = 'ERROR'
                result['error'] = f"Erreur HTTP {response.status_code}: {response.reason}"
            elif response.status_code >= 300:
                result['status'] = 'WARNING'
                result['error'] = f"Redirection {response.status_code}"
                
        except requests.exceptions.SSLError as e:
            result['status'] = 'SSL_ERROR'
            result['error'] = f"Erreur SSL: {str(e)}"
        except requests.exceptions.ConnectionError as e:
            result['status'] = 'CONNECTION_ERROR'
            result['error'] = f"Erreur de connexion: {str(e)}"
        except requests.exceptions.Timeout as e:
            result['status'] = 'TIMEOUT'
            result['error'] = f"Timeout après {self.timeout}s: {str(e)}"
        except requests.exceptions.RequestException as e:
            result['status'] = 'ERROR'
            result['error'] = f"Erreur de requête: {str(e)}"
            
        return result
    
    def check_ssl_certificate(self) -> Optional[Dict]:
        """Vérifie le certificat SSL du site"""
        if not self.check_ssl or self.parsed_url.scheme != 'https':
            return None
            
        result = {
            'status': 'OK',
            'expiry_date': None,
            'issuer': None,
            'days_remaining': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection(
                (self.hostname, 443), 
                timeout=self.timeout
            ) as sock:
                with context.wrap_socket(sock, server_hostname=self.hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Date d'expiration
                    expiry_date = datetime.strptime(
                        cert['notAfter'], 
                        '%b %d %H:%M:%S %Y %Z'
                    )
                    result['expiry_date'] = expiry_date.isoformat()
                    result['days_remaining'] = (expiry_date - datetime.now()).days
                    
                    # Émetteur
                    issuer = dict(x[0] for x in cert['issuer'])
                    result['issuer'] = issuer.get('organizationName', 'Unknown')
                    
                    # Vérification de l'expiration
                    if result['days_remaining'] < 0:
                        result['status'] = 'EXPIRED'
                        result['error'] = "Le certificat SSL a expiré"
                    elif result['days_remaining'] < 30:
                        result['status'] = 'WARNING'
                        result['error'] = f"Le certificat expire dans {result['days_remaining']} jours"
                        
        except ssl.SSLError as e:
            result['status'] = 'SSL_ERROR'
            result['error'] = f"Erreur SSL: {str(e)}"
        except socket.timeout:
            result['status'] = 'TIMEOUT'
            result['error'] = f"Timeout lors de la vérification SSL"
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = f"Erreur lors de la vérification SSL: {str(e)}"
            
        return result
    
    def check_all(self) -> Dict:
        """Effectue toutes les vérifications"""
        results = {
            'url': self.url,
            'http_check': self.check_http(),
            'ssl_check': self.check_ssl_certificate()
        }
        
        # Détermine le statut global
        statuses = [results['http_check']['status']]
        if results['ssl_check']:
            statuses.append(results['ssl_check']['status'])
            
        if 'ERROR' in statuses or 'SSL_ERROR' in statuses or 'CONNECTION_ERROR' in statuses:
            results['global_status'] = 'ERROR'
        elif 'WARNING' in statuses:
            results['global_status'] = 'WARNING'
        else:
            results['global_status'] = 'OK'
            
        return results