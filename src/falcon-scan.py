#!/usr/bin/env python3
#
# Falcon-Defender - Module de détection RF/WiFi
#

import argparse
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime
import json

try:
    from scapy.all import *
    from scapy.layers.dot11 import Dot11, Dot11Beacon, Dot11Elt
except ImportError:
    print("[!] Erreur: Le module scapy est requis.")
    print("    Installez-le avec: pip install scapy")
    sys.exit(1)

# Configuration du logger
log_dir = os.path.expanduser("~/.falcon-defender/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"falcon-scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Variables globales
detected_drones = {}
stop_scanning = False

# Chargement des signatures de drones depuis le fichier de configuration
def load_drone_signatures():
    try:
        # Chemin vers le fichier de configuration
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        config_file = os.path.join(config_dir, "drone_signatures.json")
        
        if not os.path.exists(config_file):
            logging.warning(f"Fichier de signatures introuvable: {config_file}")
            return {
                "wifi_signatures": [
                    {"name": "DJI Phantom", "ssid_patterns": ["DJI-", "Phantom"], "oui": ["60:60:1F", "34:D2:62"]},
                    {"name": "Parrot AR", "ssid_patterns": ["ardrone", "Parrot"], "oui": ["90:03:B7", "00:26:7E"]},
                    {"name": "Skydio", "ssid_patterns": ["skydio", "Skydio-"], "oui": ["F0:F0:02"]}
                ]
            }
            
        with open(config_file, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        logging.error(f"Erreur lors du chargement des signatures: {str(e)}")
        return {"wifi_signatures": []}

# Fonction de détection des drones via WiFi
def detect_drone_wifi(pkt):
    global detected_drones
    
    if stop_scanning:
        return
        
    # Vérifie si le paquet est un beacon frame ou un probe response
    if not (pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp)):
        return
        
    # Récupère les informations du paquet
    try:
        if pkt.haslayer(Dot11Elt) and pkt.type == 0:
            ssid = pkt[Dot11Elt].info.decode('utf-8', errors='ignore')
            bssid = pkt[Dot11].addr2
            signal_strength = -(256-ord(pkt[RadioTap].notdecoded[-4:-3])) if pkt.haslayer(RadioTap) else 0
            channel = int(ord(pkt[Dot11Elt:3].info))
            
            # Vérifie si le SSID ou le BSSID correspond à une signature de drone
            for drone in drone_signatures["wifi_signatures"]:
                if any(pattern.lower() in ssid.lower() for pattern in drone["ssid_patterns"]) or \
                   any(oui.lower() in bssid.lower() for oui in drone["oui"]):
                    
                    drone_id = f"{bssid}_{ssid}"
                    if drone_id not in detected_drones:
                        detected_drones[drone_id] = {
                            "type": drone["name"],
                            "ssid": ssid,
                            "bssid": bssid,
                            "channel": channel,
                            "signal": signal_strength,
                            "first_seen": datetime.now(),
                            "last_seen": datetime.now()
                        }
                        
                        logging.warning(f"Drone détecté - Type: {drone['name']}, SSID: {ssid}, BSSID: {bssid}, Canal: {channel}, Signal: {signal_strength} dBm")
                        print(f"\n[!] DRONE DÉTECTÉ\n    Type: {drone['name']}\n    SSID: {ssid}\n    BSSID: {bssid}\n    Canal: {channel}\n    Signal: {signal_strength} dBm\n")
                    else:
                        detected_drones[drone_id]["last_seen"] = datetime.now()
                        detected_drones[drone_id]["signal"] = signal_strength
                    
                    break
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse du paquet: {str(e)}")

# Fonction pour afficher périodiquement la liste des drones détectés
def display_detected_drones():
    global detected_drones
    
    while not stop_scanning:
        time.sleep(10)
        
        if not detected_drones:
            continue
            
        current_time = datetime.now()
        print("\n*** RÉCAPITULATIF DES DRONES DÉTECTÉS ***")
        print("-" * 80)
        print(f"{'TYPE':<15} {'SSID':<20} {'BSSID':<18} {'SIGNAL':<8} {'DEPUIS':<10}")
        print("-" * 80)
        
        drones_to_remove = []
        for drone_id, drone in detected_drones.items():
            time_diff = (current_time - drone["last_seen"]).total_seconds()
            
            # Si le drone n'a pas été vu depuis plus de 60 secondes, on le retire de la liste
            if time_diff > 60:
                drones_to_remove.append(drone_id)
                continue
                
            time_since = f"{int(time_diff)}s"
            print(f"{drone['type']:<15} {drone['ssid']:<20} {drone['bssid']:<18} {drone['signal']:<8} {time_since:<10}")
        
        print("-" * 80)
        
        # Supprime les drones qui n'ont pas été vus récemment
        for drone_id in drones_to_remove:
            logging.info(f"Drone perdu de vue: {detected_drones[drone_id]['type']} ({detected_drones[drone_id]['bssid']})")
            del detected_drones[drone_id]

# Gestion du signal d'interruption
def signal_handler(sig, frame):
    global stop_scanning
    
    print("\n[*] Arrêt du scan...")
    stop_scanning = True
    
    # Enregistre les résultats dans un fichier
    if detected_drones:
        results_dir = os.path.expanduser("~/.falcon-defender/results")
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(results_file, 'w') as f:
            json.dump(detected_drones, f, indent=2, default=str)
        
        print(f"[*] Résultats enregistrés dans: {results_file}")
    
    sys.exit(0)

# Fonction principale
def main():
    global drone_signatures, stop_scanning
    
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description='Falcon-Defender - Module de détection RF/WiFi')
    parser.add_argument('-i', '--interface', required=True, help='Interface réseau à utiliser pour le scan')
    parser.add_argument('-c', '--channel', type=int, help='Canal WiFi à scanner (par défaut: tous les canaux)')
    parser.add_argument('-t', '--time', type=int, default=0, help='Durée du scan en secondes (par défaut: indéfini)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Configuration du niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Charge les signatures de drones
    drone_signatures = load_drone_signatures()
    
    if not drone_signatures.get("wifi_signatures"):
        logging.error("Aucune signature de drone chargée. Vérifiez le fichier de configuration.")
        sys.exit(1)
    
    logging.info(f"Chargement de {len(drone_signatures['wifi_signatures'])} signatures de drone")
    
    # Vérification de l'interface
    try:
        if not os.path.exists(f"/sys/class/net/{args.interface}"):
            logging.error(f"Interface {args.interface} non trouvée")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Erreur lors de la vérification de l'interface: {str(e)}")
        sys.exit(1)
    
    # Mise en mode moniteur si nécessaire
    if "mon" not in args.interface:
        logging.info(f"Mise en mode moniteur de l'interface {args.interface}...")
        os.system(f"sudo airmon-ng start {args.interface} > /dev/null 2>&1")
        args.interface = f"{args.interface}mon"
        
        # Vérification que l'interface monitor existe
        if not os.path.exists(f"/sys/class/net/{args.interface}"):
            logging.error(f"Impossible de mettre l'interface {args.interface} en mode moniteur")
            sys.exit(1)
    
    # Configuration du canal si spécifié
    if args.channel:
        logging.info(f"Réglage du canal WiFi sur {args.channel}...")
        os.system(f"sudo iwconfig {args.interface} channel {args.channel} > /dev/null 2>&1")
    
    # Configuration du gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrage du thread d'affichage
    display_thread = threading.Thread(target=display_detected_drones)
    display_thread.daemon = True
    display_thread.start()
    
    # Démarrage du scan
    logging.info(f"Démarrage du scan RF/WiFi sur l'interface {args.interface}...")
    print(f"[*] Démarrage du scan sur {args.interface}...")
    print("[*] Appuyez sur Ctrl+C pour arrêter le scan")
    
    if args.time > 0:
        print(f"[*] Scan programmé pour {args.time} secondes")
        # Arrêt automatique après la durée spécifiée
        threading.Timer(args.time, lambda: signal_handler(signal.SIGINT, None)).start()
    
    try:
        sniff(iface=args.interface, prn=detect_drone_wifi, store=0)
    except Exception as e:
        logging.error(f"Erreur lors du scan: {str(e)}")
        print(f"[!] Erreur: {str(e)}")
        
        # Restauration de l'interface si nécessaire
        if "mon" in args.interface and not args.interface.startswith("mon"):
            original_interface = args.interface.replace("mon", "")
            os.system(f"sudo airmon-ng stop {args.interface} > /dev/null 2>&1")
        
        sys.exit(1)

if __name__ == "__main__":
    main()
