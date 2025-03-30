#!/usr/bin/env python3
#
# Falcon-Defender - Module d'alerte
#

import json
import logging
import os
import smtplib
import socket
import requests
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .encryption import AESEncryptor

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class FalconAlert:
    """
    Classe pour envoyer des alertes lors de la détection de drones.
    """
    def __init__(self, config_file=None):
        """
        Initialise le gestionnaire d'alertes.
        """
        self.config = self._load_config(config_file)
        self.alert_history = []
        
        # Initialise le chiffreur pour les communications sécurisées
        if self.config.get("encryption_key"):
            try:
                key = bytes.fromhex(self.config["encryption_key"])
                self.cipher = AESEncryptor(key)
            except Exception as e:
                logging.error(f"Erreur lors de l'initialisation du chiffrement: {str(e)}")
                self.cipher = None
        else:
            self.cipher = None
            
    def _load_config(self, config_file=None):
        """
        Charge la configuration depuis un fichier ou utilise les valeurs par défaut.
        """
        default_config = {
            "email": {
                "enabled": False,
                "server": "smtp.example.com",
                "port": 587,
                "username": "user@example.com",
                "password": "",
                "recipients": ["admin@example.com"]
            },
            "api": {
                "enabled": False,
                "url": "https://api.example.com/incidents",
                "key": "",
                "headers": {"Content-Type": "application/json"}
            },
            "siem": {
                "enabled": False,
                "syslog_server": "127.0.0.1",
                "syslog_port": 514,
                "facility": 23  # Local7
            },
            "throttling": {
                "same_drone_seconds": 300,  # 5 minutes entre alertes pour le même drone
                "max_alerts_per_hour": 20    # Limite les alertes par heure
            },
            "encryption_key": None
        }
        
        # Si un fichier de configuration est spécifié, charge-le
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Fusionne avec la configuration par défaut
                for category in default_config:
                    if category in user_config:
                        if isinstance(default_config[category], dict) and isinstance(user_config[category], dict):
                            default_config[category].update(user_config[category])
                        else:
                            default_config[category] = user_config[category]
                            
                logging.info(f"Configuration chargée depuis {config_file}")
                
            except Exception as e:
                logging.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        
        return default_config
    
    def can_send_alert(self, drone_id):
        """
        Vérifie si une alerte peut être envoyée selon les règles de limitation.
        """
        current_time = datetime.now()
        
        # Vérifie si une alerte a déjà été envoyée pour ce drone récemment
        for alert in self.alert_history:
            if alert["drone_id"] == drone_id:
                time_diff = (current_time - alert["timestamp"]).total_seconds()
                if time_diff < self.config["throttling"]["same_drone_seconds"]:
                    logging.info(f"Alerte pour le drone {drone_id} limitée (dernière il y a {time_diff:.1f}s)")
                    return False
        
        # Vérifie le nombre total d'alertes dans la dernière heure
        one_hour_ago = current_time.timestamp() - 3600
        recent_alerts = [a for a in self.alert_history if a["timestamp"].timestamp() > one_hour_ago]
        
        if len(recent_alerts) >= self.config["throttling"]["max_alerts_per_hour"]:
            logging.warning(f"Limite d'alertes par heure atteinte ({len(recent_alerts)})")
            return False
        
        return True
    
    def record_alert(self, drone_id, alert_type):
        """
        Enregistre une alerte dans l'historique.
        """
        self.alert_history.append({
            "drone_id": drone_id,
            "type": alert_type,
            "timestamp": datetime.now()
        })
        
        # Nettoie l'historique des alertes anciennes (> 24h)
        one_day_ago = datetime.now().timestamp() - 86400
        self.alert_history = [a for a in self.alert_history if a["timestamp"].timestamp() > one_day_ago]
    
    def send_email_alert(self, subject, body, recipients=None):
        """
        Envoie une alerte par email.
        """
        if not self.config["email"]["enabled"]:
            logging.info("Alertes email désactivées dans la configuration")
            return False
        
        try:
            # Prépare le message
            msg = MIMEMultipart()
            msg["From"] = self.config["email"]["username"]
            msg["To"] = ", ".join(recipients or self.config["email"]["recipients"])
            msg["Subject"] = subject
            
            # Ajoute le corps du message
            msg.attach(MIMEText(body, "plain"))
            
            # Connexion au serveur SMTP
            server = smtplib.SMTP(self.config["email"]["server"], self.config["email"]["port"])
            server.starttls()
            
            # Authentification
            if self.config["email"]["username"] and self.config["email"]["password"]:
                server.login(self.config["email"]["username"], self.config["email"]["password"])
            
            # Envoi du message
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Alerte email envoyée: {subject}")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'alerte email: {str(e)}")
            return False
    
    def send_api_alert(self, data):
        """
        Envoie une alerte à une API externe.
        """
        if not self.config["api"]["enabled"]:
            logging.info("Alertes API désactivées dans la configuration")
            return False
        
        try:
            # Prépare les données
            payload = json.dumps(data)
            
            # Chiffre si nécessaire
            if self.cipher:
                payload = self.cipher.encrypt_to_base64(payload)
            
            # Prépare les en-têtes
            headers = self.config["api"]["headers"]
            if self.config["api"]["key"]:
                headers["Authorization"] = f"Bearer {self.config['api']['key']}"
            
            # Envoie la requête
            response = requests.post(
                self.config["api"]["url"],
                data=payload,
                headers=headers,
                timeout=10
            )
            
            if response.ok:
                logging.info(f"Alerte API envoyée: {response.status_code}")
                return True
            else:
                logging.error(f"Erreur lors de l'envoi de l'alerte API: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'alerte API: {str(e)}")
            return False
    
    def send_syslog_alert(self, message, severity=5):  # 5 = Notice
        """
        Envoie une alerte à un serveur Syslog (pour intégration SIEM).
        """
        if not self.config["siem"]["enabled"]:
            logging.info("Alertes Syslog désactivées dans la configuration")
            return False
        
        try:
            # Format Syslog RFC 5424
            priority = (self.config["siem"]["facility"] * 8) + severity
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            hostname = socket.gethostname()
            
            # Format du message
            syslog_msg = f"<{priority}>1 {timestamp} {hostname} falcon-defender - - - {message}"
            
            # Envoi au serveur Syslog
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(
                    syslog_msg.encode('utf-8'),
                    (self.config["siem"]["syslog_server"], self.config["siem"]["syslog_port"])
                )
            
            logging.info(f"Alerte Syslog envoyée: {message[:50]}...")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'alerte Syslog: {str(e)}")
            return False
    
    def alert_drone_detection(self, drone_data):
        """
        Envoie des alertes pour une détection de drone.
        """
        # Vérifie si l'alerte peut être envoyée (limitations)
        drone_id = drone_data.get("id", "unknown")
        if not self.can_send_alert(drone_id):
            return False
        
        # Prépare les données d'alerte
        timestamp = datetime.now().isoformat()
        alert_data = {
            "type": "drone_detection",
            "timestamp": timestamp,
            "drone": drone_data,
            "location": {
                "lat": drone_data.get("position", {}).get("lat"),
                "lon": drone_data.get("position", {}).get("lon"),
                "alt": drone_data.get("position", {}).get("alt")
            },
            "severity": "info"
        }
        
        # Email
        if self.config["email"]["enabled"]:
            subject = f"[FALCON] Détection de drone - {drone_id}"
            body = f"""
Alerte Falcon-Defender: Détection de drone

ID: {drone_id}
Timestamp: {timestamp}
Type: {drone_data.get('type', 'Unknown')}
Position: {alert_data['location']}

Ceci est une alerte automatique générée par Falcon-Defender.
"""
            self.send_email_alert(subject, body)
        
        # API
        if self.config["api"]["enabled"]:
            self.send_api_alert(alert_data)
        
        # Syslog
        if self.config["siem"]["enabled"]:
            message = f"FALCON-DEFENDER-ALERT: drone={drone_id} type=detection position={alert_data['location']}"
            self.send_syslog_alert(message)
        
        # Enregistre l'alerte
        self.record_alert(drone_id, "detection")
        return True
    
    def alert_geofence_violation(self, drone_data, geofence_data):
        """
        Envoie des alertes pour une violation de zone géographique.
        """
        # Vérifie si l'alerte peut être envoyée (limitations)
        drone_id = drone_data.get("id", "unknown")
        if not self.can_send_alert(f"{drone_id}_geofence"):
            return False
        
        # Prépare les données d'alerte
        timestamp = datetime.now().isoformat()
        alert_data = {
            "type": "geofence_violation",
            "timestamp": timestamp,
            "drone": drone_data,
            "location": {
                "lat": drone_data.get("position", {}).get("lat"),
                "lon": drone_data.get("position", {}).get("lon"),
                "alt": drone_data.get("position", {}).get("alt")
            },
            "geofence": geofence_data,
            "severity": "warning"
        }
        
        # Email
        if self.config["email"]["enabled"]:
            subject = f"[FALCON] ALERTE Violation de zone - {drone_id}"
            body = f"""
ALERTE Falcon-Defender: Violation de zone interdite

ID: {drone_id}
Timestamp: {timestamp}
Type: {drone_data.get('type', 'Unknown')}
Position: {alert_data['location']}
Zone: {geofence_data['zone_name']} ({geofence_data['zone_type']})
Distance: {geofence_data['distance']:.1f}m

Ceci est une alerte automatique générée par Falcon-Defender.
Action requise: Vérifiez la situation et prenez les mesures appropriées.
"""
            self.send_email_alert(subject, body)
        
        # API
        if self.config["api"]["enabled"]:
            self.send_api_alert(alert_data)
        
        # Syslog
        if self.config["siem"]["enabled"]:
            message = f"FALCON-DEFENDER-ALERT: drone={drone_id} type=geofence_violation zone={geofence_data['zone_name']} severity=warning"
            self.send_syslog_alert(message, severity=4)  # Warning
        
        # Enregistre l'alerte
        self.record_alert(f"{drone_id}_geofence", "geofence")
        return True
    
    def alert_countermeasure(self, drone_data, action, result):
        """
        Envoie des alertes pour une action de contre-mesure.
        """
        # Vérifie si l'alerte peut être envoyée (limitations)
        drone_id = drone_data.get("id", "unknown")
        if not self.can_send_alert(f"{drone_id}_action_{action}"):
            return False
        
        # Prépare les données d'alerte
        timestamp = datetime.now().isoformat()
        alert_data = {
            "type": "countermeasure",
            "timestamp": timestamp,
            "drone": drone_data,
            "action": action,
            "result": result,
            "location": {
                "lat": drone_data.get("position", {}).get("lat"),
                "lon": drone_data.get("position", {}).get("lon"),
                "alt": drone_data.get("position", {}).get("alt")
            },
            "severity": "critical"
        }
        
        # Email
        if self.config["email"]["enabled"]:
            subject = f"[FALCON] URGENT Contre-mesure activée - {drone_id}"
            body = f"""
ALERTE URGENTE Falcon-Defender: Contre-mesure activée

ID: {drone_id}
Timestamp: {timestamp}
Type: {drone_data.get('type', 'Unknown')}
Position: {alert_data['location']}
Action: {action}
Résultat: {'Succès' if result else 'Échec'}

Ceci est une alerte automatique générée par Falcon-Defender.
Une contre-mesure a été activée et requiert une attention immédiate.
"""
            self.send_email_alert(subject, body)
        
        # API
        if self.config["api"]["enabled"]:
            self.send_api_alert(alert_data)
        
        # Syslog
        if self.config["siem"]["enabled"]:
            message = f"FALCON-DEFENDER-ALERT: drone={drone_id} type=countermeasure action={action} result={'success' if result else 'failure'} severity=critical"
            self.send_syslog_alert(message, severity=2)  # Critical
        
        # Enregistre l'alerte
        self.record_alert(f"{drone_id}_action_{action}", "countermeasure")
        return True

# Fonction pratique pour utiliser la classe
def send_alert(alert_type, data, config_file=None):
    """
    Fonction d'assistance pour envoyer une alerte rapidement.
    """
    alerter = FalconAlert(config_file)
    
    if alert_type == "detection":
        return alerter.alert_drone_detection(data)
    elif alert_type == "geofence":
        return alerter.alert_geofence_violation(data["drone"], data["geofence"])
    elif alert_type == "countermeasure":
        return alerter.alert_countermeasure(data["drone"], data["action"], data["result"])
    else:
        logging.error(f"Type d'alerte inconnu: {alert_type}")
        return False