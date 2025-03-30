#!/usr/bin/env python3
#
# Falcon-Defender - Module d'analyse MAVLink
#

import argparse
import json
import logging
import os
import signal
import socket
import struct
import sys
import threading
import time
from datetime import datetime

try:
    from pymavlink import mavutil
    from pymavlink.dialects.v20 import common as mavlink
except ImportError:
    print("[!] Erreur: Le module pymavlink est requis.")
    print("    Installez-le avec: pip install pymavlink")
    sys.exit(1)

# Configuration du logger
log_dir = os.path.expanduser("~/.falcon-defender/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"falcon-mavlink_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

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
messages_stats = {}
stop_monitoring = False

# Chargement des signatures MAVLink depuis le fichier de configuration
def load_mavlink_signatures():
    try:
        # Chemin vers le fichier de configuration
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        config_file = os.path.join(config_dir, "drone_signatures.json")
        
        if not os.path.exists(config_file):
            logging.warning(f"Fichier de signatures introuvable: {config_file}")
            return {
                "mavlink_signatures": [
                    {"type": 0, "name": "HEARTBEAT", "description": "Heartbeat message"},
                    {"type": 33, "name": "GLOBAL_POSITION_INT", "description": "Position and altitude data"},
                    {"type": 32, "name": "LOCAL_POSITION_NED", "description": "Local position data"}
                ]
            }
            
        with open(config_file, 'r') as f:
            data = json.load(f)
            return {"mavlink_signatures": data.get("mavlink_signatures", [])}
            
    except Exception as e:
        logging.error(f"Erreur lors du chargement des signatures MAVLink: {str(e)}")
        return {"mavlink_signatures": []}

# Fonction pour convertir les coordonnées en format lisible
def format_coordinates(lat, lon):
    lat_direction = "N" if lat >= 0 else "S"
    lon_direction = "E" if lon >= 0 else "W"
    
    lat = abs(lat / 10000000.0)
    lon = abs(lon / 10000000.0)
    
    lat_deg = int(lat)
    lat_min = (lat - lat_deg) * 60
    
    lon_deg = int(lon)
    lon_min = (lon - lon_deg) * 60
    
    return f"{lat_deg}°{lat_min:.6f}'{lat_direction}, {lon_deg}°{lon_min:.6f}'{lon_direction}"

# Fonction pour vérifier si un drone est dans une zone d'exclusion
def check_geofence(lat, lon):
    try:
        import yaml
        
        # Chemin vers le fichier de configuration des zones d'exclusion
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        geofence_file = os.path.join(config_dir, "geofence_zones.yml")
        
        if not os.path.exists(geofence_file):
            return None
        
        with open(geofence_file, 'r') as f:
            geofence_data = yaml.safe_load(f)
            
        # Convertit les coordonnées en degrés décimaux
        lat_deg = lat / 10000000.0
        lon_deg = lon / 10000000.0
        
        # Vérifie chaque zone d'exclusion
        for zone_type, zones in geofence_data.items():
            for zone in zones:
                name, zone_lat, zone_lon, radius = zone[:4]
                
                # Calcul approximatif de la distance (formule de Haversine simplifiée)
                from math import radians, sin, cos, sqrt, atan2
                
                R = 6371000  # Rayon de la Terre en mètres
                
                dlat = radians(zone_lat - lat_deg)
                dlon = radians(zone_lon - lon_deg)
                
                a = sin(dlat/2)**2 + cos(radians(lat_deg)) * cos(radians(zone_lat)) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                
                distance = R * c
                
                if distance <= radius:
                    # Ajoute des informations supplémentaires si disponibles
                    response_type = "passive"
                    if len(zone) > 4:
                        response_type = zone[4]
                    
                    return {
                        "zone_name": name,
                        "zone_type": zone_type,
                        "distance": distance,
                        "radius": radius,
                        "response_type": response_type
                    }
                    
        return None
        
    except Exception as e:
        logging.error(f"Erreur lors de la vérification des zones d'exclusion: {str(e)}")
        return None

# Traitement des messages MAVLink reçus
def process_mavlink_message(msg, source_addr=None):
    global detected_drones, messages_stats
    
    if stop_monitoring:
        return
    
    # Incrémente les statistiques pour ce type de message
    msg_type = msg.get_type()
    if msg_type not in messages_stats:
        messages_stats[msg_type] = 1
    else:
        messages_stats[msg_type] += 1
    
    # Génère un ID unique pour ce drone
    system_id = msg.get_srcSystem() if hasattr(msg, 'get_srcSystem') else 0
    component_id = msg.get_srcComponent() if hasattr(msg, 'get_srcComponent') else 0
    
    # Inclut l'adresse source si disponible
    drone_id = f"MAV_{system_id}_{component_id}"
    if source_addr:
        drone_id += f"_{source_addr[0]}_{source_addr[1]}"
    
    # Si c'est la première fois qu'on voit ce drone, l'ajoute à la liste
    current_time = datetime.now()
    if drone_id not in detected_drones:
        detected_drones[drone_id] = {
            "system_id": system_id,
            "component_id": component_id,
            "address": source_addr,
            "first_seen": current_time,
            "last_seen": current_time,
            "message_types": set([msg_type]),
            "position": {},
            "status": {},
            "messages": {}
        }
        
        logging.info(f"Nouveau drone MAVLink détecté - ID: {system_id}, Composant: {component_id}, Addr: {source_addr}")
        print(f"\n[+] DRONE MAVLINK DÉTECTÉ")
        print(f"    ID: {system_id}")
        print(f"    Composant: {component_id}")
        print(f"    Adresse: {source_addr}")
    else:
        # Met à jour les informations du drone
        detected_drones[drone_id]["last_seen"] = current_time
        detected_drones[drone_id]["message_types"].add(msg_type)
    
    # Traite les types de messages spécifiques pour extraire des informations
    
    # Message HEARTBEAT
    if msg_type == "HEARTBEAT":
        detected_drones[drone_id]["status"]["type"] = msg.type
        detected_drones[drone_id]["status"]["autopilot"] = msg.autopilot
        detected_drones[drone_id]["status"]["base_mode"] = msg.base_mode
        detected_drones[drone_id]["status"]["custom_mode"] = msg.custom_mode
        detected_drones[drone_id]["status"]["system_status"] = msg.system_status
        
        # Détermine si le drone est armé
        is_armed = bool(msg.base_mode & mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        detected_drones[drone_id]["status"]["armed"] = is_armed
        
        # Journalise les changements d'état importants
        if "armed" not in detected_drones[drone_id].get("messages", {}) or detected_drones[drone_id]["messages"].get("armed") != is_armed:
            status_str = "ARMÉ" if is_armed else "DÉSARMÉ"
            logging.warning(f"Drone {drone_id} est maintenant {status_str}")
            print(f"[!] Drone {drone_id} est maintenant {status_str}")
        
        detected_drones[drone_id]["messages"]["armed"] = is_armed
    
    # Message GLOBAL_POSITION_INT
    elif msg_type == "GLOBAL_POSITION_INT":
        detected_drones[drone_id]["position"]["lat"] = msg.lat
        detected_drones[drone_id]["position"]["lon"] = msg.lon
        detected_drones[drone_id]["position"]["alt"] = msg.alt
        detected_drones[drone_id]["position"]["relative_alt"] = msg.relative_alt
        detected_drones[drone_id]["position"]["vx"] = msg.vx
        detected_drones[drone_id]["position"]["vy"] = msg.vy
        detected_drones[drone_id]["position"]["vz"] = msg.vz
        detected_drones[drone_id]["position"]["hdg"] = msg.hdg
        detected_drones[drone_id]["position"]["last_update"] = current_time.isoformat()
        
        # Vérifie si le drone est dans une zone d'exclusion
        if "lat" in detected_drones[drone_id]["position"] and "lon" in detected_drones[drone_id]["position"]:
            geofence_result = check_geofence(msg.lat, msg.lon)
            
            if geofence_result:
                detected_drones[drone_id]["geofence"] = geofence_result
                
                # Si c'est la première détection dans une zone ou une nouvelle zone
                if "geofence_alert" not in detected_drones[drone_id] or detected_drones[drone_id]["geofence"]["zone_name"] != detected_drones[drone_id]["geofence_alert"]["zone_name"]:
                    logging.warning(f"Drone {drone_id} détecté dans une zone restreinte: {geofence_result['zone_name']} ({geofence_result['zone_type']})")
                    print(f"\n[!] ALERTE ZONE RESTREINTE")
                    print(f"    Drone: {drone_id}")
                    print(f"    Zone: {geofence_result['zone_name']} ({geofence_result['zone_type']})")
                    print(f"    Distance du centre: {geofence_result['distance']:.1f}m (rayon: {geofence_result['radius']}m)")
                    
                    if geofence_result["response_type"] == "automatic":
                        print(f"    [!] Cette zone autorise une réponse automatique (utiliser falcon-safe.py)")
                    
                    detected_drones[drone_id]["geofence_alert"] = {
                        "zone_name": geofence_result["zone_name"],
                        "time": current_time.isoformat()
                    }
            else:
                # Si le drone était dans une zone et en est sorti
                if "geofence_alert" in detected_drones[drone_id]:
                    logging.info(f"Drone {drone_id} a quitté la zone restreinte: {detected_drones[drone_id]['geofence_alert']['zone_name']}")
                    print(f"[+] Drone {drone_id} a quitté la zone restreinte")
                    
                    detected_drones[drone_id].pop("geofence_alert", None)
                detected_drones[drone_id].pop("geofence", None)
                
    # Message ATTITUDE
    elif msg_type == "ATTITUDE":
        detected_drones[drone_id]["attitude"] = {
            "roll": msg.roll,
            "pitch": msg.pitch,
            "yaw": msg.yaw,
            "rollspeed": msg.rollspeed,
            "pitchspeed": msg.pitchspeed,
            "yawspeed": msg.yawspeed,
            "last_update": current_time.isoformat()
        }
    
    # Message BATTERY_STATUS
    elif msg_type == "BATTERY_STATUS":
        detected_drones[drone_id]["battery"] = {
            "voltage": msg.voltages[0] if len(msg.voltages) > 0 else 0,
            "current": msg.current_battery,
            "remaining": msg.battery_remaining,
            "last_update": current_time.isoformat()
        }
        
        # Alerte batterie faible
        if msg.battery_remaining < 20 and "battery_alert" not in detected_drones[drone_id]:
            logging.warning(f"Drone {drone_id} a une batterie faible: {msg.battery_remaining}%")
            print(f"[!] BATTERIE FAIBLE: Drone {drone_id} - {msg.battery_remaining}%")
            detected_drones[drone_id]["battery_alert"] = True
    
    # Message COMMAND_ACK
    elif msg_type == "COMMAND_ACK":
        detected_drones[drone_id]["command_ack"] = {
            "command": msg.command,
            "result": msg.result,
            "last_update": current_time.isoformat()
        }
        
        # Log des commandes importantes
        logging.info(f"Drone {drone_id} a reçu la commande {msg.command} avec résultat {msg.result}")

# Fonction pour écouter les paquets UDP MAVLink
def listen_udp(host, port):
    global stop_monitoring
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        sock.settimeout(1.0)  # Timeout pour permettre l'arrêt propre
        
        logging.info(f"Écoute MAVLink sur UDP {host}:{port}")
        print(f"[*] Écoute des paquets MAVLink sur UDP {host}:{port}...")
        
        # Crée une connexion MAVLink pour le décodage
        mav = mavutil.mavlink_connection('udpin:0.0.0.0:0', input=False)
        
        while not stop_monitoring:
            try:
                data, addr = sock.recvfrom(1024)
                
                # Décode le message MAVLink
                mav.buf = data
                msg = mav.recv_msg()
                
                if msg:
                    process_mavlink_message(msg, addr)
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Erreur lors de la réception des données: {str(e)}")
                
        sock.close()
        
    except Exception as e:
        logging.error(f"Erreur lors de l'initialisation de l'écoute UDP: {str(e)}")
        print(f"[!] Erreur: {str(e)}")

# Fonction pour se connecter à un flux MAVLink
def connect_mavlink_stream(connection_string):
    global stop_monitoring
    
    try:
        # Initialise la connexion MAVLink
        mav_conn = mavutil.mavlink_connection(connection_string)
        logging.info(f"Connexion MAVLink établie: {connection_string}")
        print(f"[*] Connexion MAVLink établie: {connection_string}")
        
        # Attend un heartbeat pour confirmer la connexion
        mav_conn.wait_heartbeat()
        logging.info("Heartbeat reçu, connexion confirmée")
        print("[+] Heartbeat reçu, connexion confirmée")
        
        # Boucle principale de réception des messages
        while not stop_monitoring:
            msg = mav_conn.recv_match(blocking=False)
            if msg:
                process_mavlink_message(msg)
            else:
                time.sleep(0.01)
                
    except Exception as e:
        logging.error(f"Erreur lors de la connexion MAVLink: {str(e)}")
        print(f"[!] Erreur: {str(e)}")

# Fonction pour afficher périodiquement les statistiques
def display_stats():
    global detected_drones, messages_stats, stop_monitoring
    
    while not stop_monitoring:
        time.sleep(10)
        
        if not detected_drones:
            continue
            
        current_time = datetime.now()
        print("\n*** RÉCAPITULATIF DES DRONES MAVLINK DÉTECTÉS ***")
        print("-" * 80)
        print(f"{'ID':<20} {'SYSTÈME':<10} {'COMPOSANT':<10} {'ÉTAT':<10} {'DERNIÈRE ACTIVITÉ':<15}")
        print("-" * 80)
        
        drones_to_remove = []
        for drone_id, drone in detected_drones.items():
            time_diff = (current_time - drone["last_seen"]).total_seconds()
            
            # Si le drone n'a pas été vu depuis plus de 60 secondes, on le retire de la liste
            if time_diff > 60:
                drones_to_remove.append(drone_id)
                continue
                
            time_since = f"{int(time_diff)}s"
            state = "ARMÉ" if drone.get("status", {}).get("armed", False) else "DÉSARMÉ"
            
            # Affiche des informations de base
            print(f"{drone_id:<20} {drone['system_id']:<10} {drone['component_id']:<10} {state:<10} {time_since:<15}")
            
            # Affiche la position si disponible
            if "position" in drone and "lat" in drone["position"] and "lon" in drone["position"]:
                lat = drone["position"]["lat"]
                lon = drone["position"]["lon"]
                alt = drone["position"]["relative_alt"] / 1000.0  # Conversion en mètres
                
                coords = format_coordinates(lat, lon)
                print(f"    Position: {coords}, Altitude: {alt:.1f}m")
            
            # Affiche l'alerte de zone géographique si applicable
            if "geofence" in drone:
                zone_name = drone["geofence"]["zone_name"]
                zone_type = drone["geofence"]["zone_type"]
                distance = drone["geofence"]["distance"]
                
                print(f"    [!] Dans zone restreinte: {zone_name} ({zone_type}), Distance: {distance:.1f}m")
        
        print("-" * 80)
        print(f"Types de messages: {', '.join(sorted(messages_stats.keys()))}")
        print("-" * 80)
        
        # Supprime les drones qui n'ont pas été vus récemment
        for drone_id in drones_to_remove:
            logging.info(f"Drone perdu de vue: {drone_id}")
            del detected_drones[drone_id]

# Gestion du signal d'interruption
def signal_handler(sig, frame):
    global stop_monitoring
    
    print("\n[*] Arrêt de la surveillance MAVLink...")
    stop_monitoring = True
    
    # Enregistre les résultats dans un fichier
    if detected_drones:
        results_dir = os.path.expanduser("~/.falcon-defender/results")
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, f"mavlink_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Convertit les ensembles en listes pour la sérialisation JSON
        for drone_id in detected_drones:
            if "message_types" in detected_drones[drone_id]:
                detected_drones[drone_id]["message_types"] = list(detected_drones[drone_id]["message_types"])
        
        with open(results_file, 'w') as f:
            json.dump(detected_drones, f, indent=2, default=str)
        
        print(f"[*] Résultats enregistrés dans: {results_file}")
    
    sys.exit(0)

# Fonction principale
def main():
    global mavlink_signatures
    
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description='Falcon-Defender - Module de surveillance MAVLink')
    parser.add_argument('--port', type=int, default=14550, help='Port UDP à écouter (par défaut: 14550)')
    parser.add_argument('--host', default='0.0.0.0', help='Adresse IP à écouter (par défaut: 0.0.0.0)')
    parser.add_argument('--connect', help='Connexion directe à un flux MAVLink (ex: udp:192.168.1.1:14550, tcp:localhost:5760)')
    parser.add_argument('--capture', action='store_true', help='Capturer les paquets MAVLink dans un fichier')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Configuration du niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Charge les signatures MAVLink
    mavlink_signatures = load_mavlink_signatures()
    
    if not mavlink_signatures.get("mavlink_signatures"):
        logging.warning("Aucune signature MAVLink chargée. Les détections seront limitées.")
    else:
        logging.info(f"Chargement de {len(mavlink_signatures['mavlink_signatures'])} signatures MAVLink")
    
    # Configuration du gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrage du thread d'affichage des statistiques
    stats_thread = threading.Thread(target=display_stats)
    stats_thread.daemon = True
    stats_thread.start()
    
    # Capture des paquets MAVLink si demandé
    if args.capture:
        capture_dir = os.path.expanduser("~/.falcon-defender/captures")
        os.makedirs(capture_dir, exist_ok=True)
        
        capture_file = os.path.join(capture_dir, f"mavlink_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tlog")
        
        logging.info(f"Capture MAVLink activée: {capture_file}")
        print(f"[*] Capture MAVLink: {capture_file}")
    
    # Démarrage de la surveillance
    print("[*] Démarrage de la surveillance MAVLink...")
    print("[*] Appuyez sur Ctrl+C pour arrêter")
    
    try:
        if args.connect:
            # Mode connexion directe
            connect_mavlink_stream(args.connect)
        else:
            # Mode écoute UDP
            listen_udp(args.host, args.port)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logging.error(f"Erreur lors de la surveillance: {str(e)}")
        print(f"[!] Erreur: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
