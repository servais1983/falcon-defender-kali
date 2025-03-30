#!/usr/bin/env python3
#
# Falcon-Defender - Module de neutralisation sécurisée (USAGE RESTREINT)
#
# AVERTISSEMENT: L'utilisation de ce module pour interférer avec des drones
# peut être illégale dans de nombreuses juridictions. Il est conçu uniquement
# pour un usage dans un cadre légal et autorisé.
#

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

try:
    from pymavlink import mavutil
except ImportError:
    print("[!] Erreur: Le module pymavlink est requis.")
    print("    Installez-le avec: pip install pymavlink")
    sys.exit(1)

# Configuration du logger
log_dir = os.path.expanduser("~/.falcon-defender/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"falcon-safe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Vérification d'autorisation
def check_authorization(key_file=None):
    """
    Vérifie si l'utilisation des contre-mesures est autorisée.
    Cette fonction devrait idéalement vérifier une clé cryptographique ou
    un autre mécanisme d'autorisation légitime.
    """
    if not key_file:
        logging.warning("Aucun fichier d'autorisation fourni")
        return False
    
    try:
        if not os.path.exists(key_file):
            logging.error(f"Fichier d'autorisation introuvable: {key_file}")
            return False
            
        with open(key_file, 'r') as f:
            key_data = f.read().strip()
            
        # Dans un système réel, vérifiez la signature cryptographique ici
        try:
            from utils.encryption import verify_authorization
            return verify_authorization(key_data)
        except ImportError:
            logging.error("Module de vérification d'autorisation non disponible")
            return False
        
    except Exception as e:
        logging.error(f"Erreur lors de la vérification d'autorisation: {str(e)}")
        return False
    
    # Fonction factice pour les tests - NE PAS UTILISER EN PRODUCTION
    return True

# Fonction pour envoyer une commande RTL (Return to Launch)
def send_rtl_command(connection_string, drone_sysid=1, drone_compid=1, wait_ack=True):
    """
    Envoie une commande RTL (Return to Launch) à un drone.
    """
    logging.info(f"Tentative de connexion à {connection_string}")
    print(f"[*] Tentative de connexion à {connection_string}...")
    
    try:
        # Établit la connexion MAVLink
        mav_conn = mavutil.mavlink_connection(connection_string)
        
        # Attend le heartbeat pour confirmer la connexion
        mav_conn.wait_heartbeat()
        logging.info(f"Connexion établie, heartbeat reçu (système: {mav_conn.target_system}, composant: {mav_conn.target_component})")
        print(f"[+] Connexion établie! Système ID: {mav_conn.target_system}, Composant ID: {mav_conn.target_component}")
        
        # Utilise le système/composant du drone cible si spécifié
        target_system = drone_sysid if drone_sysid != 1 else mav_conn.target_system
        target_component = drone_compid if drone_compid != 1 else mav_conn.target_component
        
        # Envoie la commande RTL
        logging.warning(f"Envoi de la commande RTL au drone {target_system}/{target_component}")
        print(f"[!] Envoi de la commande RTL au drone {target_system}/{target_component}...")
        
        # Utilise MODE_RTL (code mission dépend du firmware du drone)
        mav_conn.set_mode_rtl()
        
        # Si attente d'acknowledgement
        if wait_ack:
            # Attend 3 secondes pour l'accusé de réception
            ack_received = False
            start_time = time.time()
            
            while time.time() - start_time < 3:
                msg = mav_conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=1)
                if msg and msg.command == 20:  # MAV_CMD_NAV_RETURN_TO_LAUNCH
                    ack_received = True
                    if msg.result == 0:  # MAV_RESULT_ACCEPTED
                        logging.info("Commande RTL acceptée")
                        print("[+] Commande RTL acceptée!")
                    else:
                        logging.warning(f"Commande RTL rejetée, code: {msg.result}")
                        print(f"[!] Commande RTL rejetée, code: {msg.result}")
                    break
            
            if not ack_received:
                logging.warning("Pas d'accusé de réception reçu pour la commande RTL")
                print("[!] Pas d'accusé de réception reçu mais la commande a peut-être été exécutée")
        
        # Ferme la connexion
        mav_conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la commande RTL: {str(e)}")
        print(f"[!] Erreur: {str(e)}")
        return False

# Fonction pour forcer l'atterrissage
def send_land_command(connection_string, drone_sysid=1, drone_compid=1, wait_ack=True):
    """
    Envoie une commande d'atterrissage à un drone.
    """
    logging.info(f"Tentative de connexion à {connection_string}")
    print(f"[*] Tentative de connexion à {connection_string}...")
    
    try:
        # Établit la connexion MAVLink
        mav_conn = mavutil.mavlink_connection(connection_string)
        
        # Attend le heartbeat pour confirmer la connexion
        mav_conn.wait_heartbeat()
        logging.info(f"Connexion établie, heartbeat reçu (système: {mav_conn.target_system}, composant: {mav_conn.target_component})")
        print(f"[+] Connexion établie! Système ID: {mav_conn.target_system}, Composant ID: {mav_conn.target_component}")
        
        # Utilise le système/composant du drone cible si spécifié
        target_system = drone_sysid if drone_sysid != 1 else mav_conn.target_system
        target_component = drone_compid if drone_compid != 1 else mav_conn.target_component
        
        # Envoie la commande LAND
        logging.warning(f"Envoi de la commande d'atterrissage au drone {target_system}/{target_component}")
        print(f"[!] Envoi de la commande d'atterrissage au drone {target_system}/{target_component}...")
        
        # Commande LAND
        mav_conn.mav.command_long_send(
            target_system,
            target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,  # Confirmation
            0, 0, 0, 0, 0, 0, 0  # Paramètres non utilisés
        )
        
        # Si attente d'acknowledgement
        if wait_ack:
            # Attend 3 secondes pour l'accusé de réception
            ack_received = False
            start_time = time.time()
            
            while time.time() - start_time < 3:
                msg = mav_conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=1)
                if msg and msg.command == mavutil.mavlink.MAV_CMD_NAV_LAND:
                    ack_received = True
                    if msg.result == 0:  # MAV_RESULT_ACCEPTED
                        logging.info("Commande d'atterrissage acceptée")
                        print("[+] Commande d'atterrissage acceptée!")
                    else:
                        logging.warning(f"Commande d'atterrissage rejetée, code: {msg.result}")
                        print(f"[!] Commande d'atterrissage rejetée, code: {msg.result}")
                    break
            
            if not ack_received:
                logging.warning("Pas d'accusé de réception reçu pour la commande d'atterrissage")
                print("[!] Pas d'accusé de réception reçu mais la commande a peut-être été exécutée")
        
        # Ferme la connexion
        mav_conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la commande d'atterrissage: {str(e)}")
        print(f"[!] Erreur: {str(e)}")
        return False

# Fonction pour désarmer le drone
def send_disarm_command(connection_string, drone_sysid=1, drone_compid=1, wait_ack=True):
    """
    Envoie une commande de désarmement à un drone.
    ATTENTION: Cela peut être dangereux si le drone est en vol!
    """
    logging.info(f"Tentative de connexion à {connection_string}")
    print(f"[*] Tentative de connexion à {connection_string}...")
    
    try:
        # Établit la connexion MAVLink
        mav_conn = mavutil.mavlink_connection(connection_string)
        
        # Attend le heartbeat pour confirmer la connexion
        mav_conn.wait_heartbeat()
        logging.info(f"Connexion établie, heartbeat reçu (système: {mav_conn.target_system}, composant: {mav_conn.target_component})")
        print(f"[+] Connexion établie! Système ID: {mav_conn.target_system}, Composant ID: {mav_conn.target_component}")
        
        # Utilise le système/composant du drone cible si spécifié
        target_system = drone_sysid if drone_sysid != 1 else mav_conn.target_system
        target_component = drone_compid if drone_compid != 1 else mav_conn.target_component
        
        # Envoie la commande DISARM
        logging.warning(f"Envoi de la commande de désarmement au drone {target_system}/{target_component}")
        print(f"[!] ATTENTION: Envoi de la commande de désarmement au drone {target_system}/{target_component}...")
        print(f"[!] Cette commande peut être dangereuse si le drone est en vol!")
        
        # Petite pause pour laisser le temps à l'opérateur d'annuler
        for i in range(5, 0, -1):
            print(f"[*] Désarmement dans {i} secondes... (Ctrl+C pour annuler)")
            time.sleep(1)
        
        # Commande DISARM
        mav_conn.mav.command_long_send(
            target_system,
            target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # Confirmation
            0,  # 0 = désarmer
            0, 0, 0, 0, 0, 0  # Paramètres non utilisés
        )
        
        # Si attente d'acknowledgement
        if wait_ack:
            # Attend 3 secondes pour l'accusé de réception
            ack_received = False
            start_time = time.time()
            
            while time.time() - start_time < 3:
                msg = mav_conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=1)
                if msg and msg.command == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
                    ack_received = True
                    if msg.result == 0:  # MAV_RESULT_ACCEPTED
                        logging.info("Commande de désarmement acceptée")
                        print("[+] Commande de désarmement acceptée!")
                    else:
                        logging.warning(f"Commande de désarmement rejetée, code: {msg.result}")
                        print(f"[!] Commande de désarmement rejetée, code: {msg.result}")
                    break
            
            if not ack_received:
                logging.warning("Pas d'accusé de réception reçu pour la commande de désarmement")
                print("[!] Pas d'accusé de réception reçu mais la commande a peut-être été exécutée")
        
        # Ferme la connexion
        mav_conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi de la commande de désarmement: {str(e)}")
        print(f"[!] Erreur: {str(e)}")
        return False

# Fonction pour sauvegarder les actions dans un journal d'audit
def save_audit_log(action, connection_string, result, key_file=None):
    """
    Enregistre une entrée dans le journal d'audit pour des raisons légales.
    """
    try:
        audit_dir = os.path.expanduser("~/.falcon-defender/audit")
        os.makedirs(audit_dir, exist_ok=True)
        
        audit_file = os.path.join(audit_dir, f"audit_{datetime.now().strftime('%Y%m')}.log")
        
        timestamp = datetime.now().isoformat()
        username = os.getlogin()
        hostname = os.uname().nodename
        ip = connection_string.split(':')[1] if ':' in connection_string else connection_string
        
        entry = {
            "timestamp": timestamp,
            "action": action,
            "target": ip,
            "user": username,
            "hostname": hostname,
            "key_file": key_file,
            "result": result
        }
        
        with open(audit_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
            
        logging.info(f"Action enregistrée dans le journal d'audit: {audit_file}")
        
    except Exception as e:
        logging.error(f"Erreur lors de l'enregistrement dans le journal d'audit: {str(e)}")

# Fonction principale
def main():
    # Affiche l'avertissement
    print("\n" + "!" * 80)
    print("AVERTISSEMENT: Ce module est conçu pour être utilisé uniquement dans un cadre légal")
    print("et autorisé. L'interférence avec des drones peut être illégale dans votre juridiction.")
    print("Utilisez ce module uniquement si vous avez l'autorisation légale de le faire.")
    print("!" * 80 + "\n")
    
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description='Falcon-Defender - Module de neutralisation sécurisée (USAGE RESTREINT)')
    parser.add_argument('--connect', required=True, help='Connexion au drone (ex: udp:192.168.1.1:14550)')
    parser.add_argument('--sysid', type=int, default=1, help='ID du système cible (par défaut: 1)')
    parser.add_argument('--compid', type=int, default=1, help='ID du composant cible (par défaut: 1)')
    parser.add_argument('--action', choices=['rtl', 'land', 'disarm'], default='rtl',
                        help='Action à effectuer (rtl=retour à la base, land=atterrissage, disarm=désarmement)')
    parser.add_argument('--key', help='Fichier contenant la clé d\'autorisation')
    parser.add_argument('--no-ack', action='store_true', help='Ne pas attendre d\'accusé de réception')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Configuration du niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Vérifie l'autorisation
    if not check_authorization(args.key):
        logging.error("Autorisation refusée. Vous devez fournir une clé d'autorisation valide.")
        print("[!] AUTORISATION REFUSÉE")
        print("    Pour des raisons de sécurité et légales, ce module nécessite une autorisation valide.")
        print("    Contactez votre administrateur système ou les autorités compétentes pour obtenir une clé.")
        return False
    
    # Exécute l'action demandée
    result = False
    
    if args.action == 'rtl':
        print("\n[*] Tentative d'envoi d'une commande de retour à la base (RTL)...")
        result = send_rtl_command(args.connect, args.sysid, args.compid, not args.no_ack)
    
    elif args.action == 'land':
        print("\n[*] Tentative d'envoi d'une commande d'atterrissage...")
        result = send_land_command(args.connect, args.sysid, args.compid, not args.no_ack)
    
    elif args.action == 'disarm':
        print("\n[*] Tentative d'envoi d'une commande de désarmement...")
        result = send_disarm_command(args.connect, args.sysid, args.compid, not args.no_ack)
    
    # Enregistre l'action dans le journal d'audit
    save_audit_log(args.action, args.connect, result, args.key)
    
    if result:
        print("\n[+] Action complétée avec succès.")
    else:
        print("\n[!] Échec de l'action.")
    
    return result

# Point d'entrée
if __name__ == "__main__":
    try:
        # Intercepte Ctrl+C pour une sortie propre
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
        
        # Exécute la fonction principale
        sys.exit(0 if main() else 1)
        
    except KeyboardInterrupt:
        print("\n[*] Opération annulée par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Erreur non gérée: {str(e)}")
        print(f"\n[!] Erreur: {str(e)}")
        sys.exit(1)
