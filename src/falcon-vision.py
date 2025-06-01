#!/usr/bin/env python3
#
# Falcon-Defender - Module de détection visuelle par IA
#

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime

try:
    import cv2
    from ultralytics import YOLO
except ImportError:
    print("[!] Erreur: Les modules OpenCV et Ultralytics sont requis.")
    print("    Installez-les avec: pip install opencv-python ultralytics")
    sys.exit(1)

# Configuration du logger
log_dir = os.path.expanduser("~/.falcon-defender/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"falcon-vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

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
stop_processing = False
model = None

# Couleurs pour la visualisation
COLORS = {
    "detection": (0, 0, 255),  # Rouge pour les détections
    "tracking": (0, 255, 0),   # Vert pour le tracking
    "text_bg": (0, 0, 0),      # Noir pour le fond du texte
    "text": (255, 255, 255)    # Blanc pour le texte
}

# Vérification et chargement du modèle YOLOv8
def load_model():
    # Vérifie si un modèle spécifique pour les drones existe
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    drone_model_path = os.path.join(models_dir, "yolov8n-drone.pt")
    
    # Si le modèle spécifique n'existe pas, utilise le modèle générique
    if not os.path.exists(drone_model_path):
        logging.warning(f"Modèle spécifique pour drones introuvable: {drone_model_path}")
        logging.info("Utilisation du modèle YOLOv8n générique")
        return YOLO("yolov8n.pt")
    
    logging.info(f"Chargement du modèle spécifique pour drones: {drone_model_path}")
    return YOLO(drone_model_path)

# Traitement de la détection visuelle
def process_frame(frame, confidence=0.4):
    global detected_drones, model
    
    if frame is None or model is None:
        return frame
    
    # Infos sur le frame pour l'affichage
    height, width = frame.shape[:2]
    
    # Exécute la détection et le tracking
    try:
        results = model.track(frame, persist=True, conf=confidence, verbose=False)
    except Exception as e:
        logging.error(f"Erreur lors du tracking: {str(e)}")
        return frame
    
    # Traite les résultats
    if results is not None:
        for result in results:
            if result is not None and hasattr(result, 'track'):
                track = result.track
                if track is not None:
                    # Traitement du tracking
                    process_tracking(track)
    
    # Traite les résultats
    if results is not None and len(results) > 0:
        # Récupère les boîtes de détection
        boxes = results[0].boxes
        
        current_time = datetime.now()
        
        # Pour chaque détection
        for box in boxes:
            # Récupère la classe et la confiance
            cls = int(box.cls.item())
            conf = float(box.conf.item())
            
            # Récupère le nom de la classe
            class_name = results[0].names[cls]
            
            # Pour les drones et les objets volants (avion, hélicoptère, oiseau)
            if class_name in ["drone", "airplane", "bird", "helicopter", "kite"]:
                # Récupère les coordonnées de la boîte
                x1, y1, x2, y2 = [int(val) for val in box.xyxy[0].tolist()]
                
                # Calcule le centre et la taille
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                size = (x2 - x1) * (y2 - y1)
                
                # Calcule la position relative (pour l'estimation de la distance)
                rel_x = center_x / width - 0.5  # -0.5 à 0.5, 0 = centre
                rel_y = center_y / height - 0.5  # -0.5 à 0.5, 0 = centre
                
                # Récupère l'ID de tracking si disponible
                track_id = int(box.id.item()) if box.id is not None else None
                
                # Crée un ID unique pour cette détection
                detection_id = f"{class_name}_{track_id if track_id is not None else str(center_x)+'_'+str(center_y)}"
                
                # Détermine la couleur en fonction du tracking
                color = COLORS["tracking"] if track_id is not None else COLORS["detection"]
                
                # Dessine la boîte de détection
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Ajoute l'étiquette avec la classe et la confiance
                label = f"{class_name.upper()}: {conf:.2f}"
                if track_id is not None:
                    label += f" ID:{track_id}"
                
                # Calcule la taille et la position du texte
                (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + text_width, y1), COLORS["text_bg"], -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS["text"], 2)
                
                # Ajoute ou met à jour la détection dans le dictionnaire
                if detection_id not in detected_drones:
                    detected_drones[detection_id] = {
                        "type": class_name,
                        "track_id": track_id,
                        "first_seen": current_time,
                        "last_seen": current_time,
                        "confidence": conf,
                        "position": {
                            "center_x": center_x,
                            "center_y": center_y,
                            "relative_x": rel_x,
                            "relative_y": rel_y,
                            "size": size
                        }
                    }
                    
                    # Log et affichage de la nouvelle détection
                    logging.warning(f"Drone/objet volant détecté - Type: {class_name}, Conf: {conf:.2f}, ID: {track_id}")
                    direction = ""
                    if rel_x < -0.3:
                        direction += "gauche"
                    elif rel_x > 0.3:
                        direction += "droite"
                    else:
                        direction += "centre"
                    
                    if rel_y < -0.3:
                        direction += " haut"
                    elif rel_y > 0.3:
                        direction += " bas"
                    else:
                        direction += " milieu"
                    
                    print(f"\n[!] DÉTECTION - {class_name.upper()}")
                    print(f"    Confiance: {conf:.2f}")
                    print(f"    Position: {direction}")
                    print(f"    ID Tracking: {track_id if track_id is not None else 'Non suivi'}")
                else:
                    # Mise à jour des informations
                    detected_drones[detection_id]["last_seen"] = current_time
                    detected_drones[detection_id]["confidence"] = conf
                    detected_drones[detection_id]["position"] = {
                        "center_x": center_x,
                        "center_y": center_y,
                        "relative_x": rel_x,
                        "relative_y": rel_y,
                        "size": size
                    }
    
    # Ajoute un titre et les infos en haut du frame
    cv2.putText(frame, "FALCON-DEFENDER", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 120, 255), 2)
    cv2.putText(frame, f"Détections: {len(detected_drones)}", (width - 150, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Nettoie les détections périmées (plus de 5 secondes sans mise à jour)
    current_time = datetime.now()
    detections_to_remove = []
    for detection_id, detection in detected_drones.items():
        time_diff = (current_time - detection["last_seen"]).total_seconds()
        if time_diff > 5:
            detections_to_remove.append(detection_id)
    
    for detection_id in detections_to_remove:
        del detected_drones[detection_id]
    
    return frame

# Fonction pour enregistrer une capture en cas de détection
def save_detection_image(frame):
    if frame is None:
        return
        
    results_dir = os.path.expanduser("~/.falcon-defender/detections")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_file = os.path.join(results_dir, f"detection_{timestamp}.jpg")
    
    cv2.imwrite(image_file, frame)
    logging.info(f"Capture sauvegardée: {image_file}")
    print(f"[*] Capture sauvegardée: {image_file}")

# Fonction principale de capture vidéo
def capture_video(source, confidence, display, record, snapshot):
    global stop_processing, model
    
    try:
        # Initialise la capture vidéo
        if source.isdigit():
            source = int(source)
            
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            logging.error(f"Impossible d'ouvrir la source vidéo: {source}")
            print(f"[!] Erreur: Impossible d'ouvrir la source vidéo: {source}")
            return
        
        logging.info(f"Capture vidéo initialisée depuis: {source}")
        
        # Récupère la largeur et la hauteur de la vidéo
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        logging.info(f"Résolution: {width}x{height}, FPS: {fps}")
        
        # Configuration de l'enregistrement vidéo si demandé
        video_writer = None
        if record:
            results_dir = os.path.expanduser("~/.falcon-defender/videos")
            os.makedirs(results_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_file = os.path.join(results_dir, f"record_{timestamp}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(video_file, fourcc, fps, (width, height))
            
            logging.info(f"Enregistrement vidéo activé: {video_file}")
            print(f"[*] Enregistrement vidéo: {video_file}")
        
        # Boucle principale de traitement vidéo
        last_snapshot_time = datetime.now()
        
        while not stop_processing:
            ret, frame = cap.read()
            
            if not ret:
                logging.warning("Fin du flux vidéo ou erreur de lecture")
                break
            
            # Traite le frame avec la détection
            processed_frame = process_frame(frame, confidence)
            
            # Enregistre le frame si l'enregistrement est activé
            if video_writer is not None:
                video_writer.write(processed_frame)
            
            # Prend des captures périodiques si demandé
            if snapshot > 0 and detected_drones:
                current_time = datetime.now()
                time_diff = (current_time - last_snapshot_time).total_seconds()
                
                if time_diff >= snapshot:
                    save_detection_image(processed_frame)
                    last_snapshot_time = current_time
            
            # Affiche le frame si demandé
            if display:
                cv2.imshow("Falcon-Defender Vision", processed_frame)
                
                # Vérifie les touches
                key = cv2.waitKey(1) & 0xFF
                
                # 'q' pour quitter
                if key == ord('q'):
                    break
                
                # 's' pour capture manuelle
                elif key == ord('s'):
                    save_detection_image(processed_frame)
                
                # 'h' pour afficher l'aide
                elif key == ord('h'):
                    print("\n*** COMMANDES CLAVIER ***")
                    print("q - Quitter le programme")
                    print("s - Prendre une capture d'écran")
                    print("h - Afficher cette aide")
        
        # Nettoyage
        cap.release()
        if video_writer is not None:
            video_writer.release()
        cv2.destroyAllWindows()
        
    except Exception as e:
        logging.error(f"Erreur lors de la capture vidéo: {str(e)}")
        print(f"[!] Erreur: {str(e)}")

# Gestion du signal d'interruption
def signal_handler(sig, frame):
    global stop_processing
    
    print("\n[*] Arrêt de la détection visuelle...")
    stop_processing = True
    
    # Enregistre les résultats dans un fichier
    if detected_drones:
        results_dir = os.path.expanduser("~/.falcon-defender/results")
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, f"vision_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(results_file, 'w') as f:
            json.dump(detected_drones, f, indent=2, default=str)
        
        print(f"[*] Résultats enregistrés dans: {results_file}")
    
    # Attend un peu pour laisser le temps au thread de se terminer
    time.sleep(1)
    sys.exit(0)

# Fonction principale
def main():
    global model
    
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description='Falcon-Defender - Module de détection visuelle par IA')
    parser.add_argument('--source', default='0', help='Source vidéo (0 pour webcam, chemin pour fichier, RTSP pour flux)')
    parser.add_argument('--conf', type=float, default=0.4, help='Seuil de confiance pour la détection (0-1)')
    parser.add_argument('--display', action='store_true', help='Afficher la vidéo en direct')
    parser.add_argument('--record', action='store_true', help='Enregistrer la vidéo avec les détections')
    parser.add_argument('--snapshot', type=int, default=0, help='Prendre des captures à intervalle régulier (en secondes, 0 pour désactiver)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mode verbeux')
    
    args = parser.parse_args()
    
    # Configuration du niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Vérification de la présence de GPU pour l'accélération
    try:
        gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if gpu_available:
            logging.info("GPU CUDA détecté, accélération disponible")
        else:
            logging.info("Pas de GPU CUDA détecté, utilisation du CPU")
    except:
        logging.info("OpenCV compilé sans support CUDA, utilisation du CPU")
    
    # Charge le modèle YOLOv8
    try:
        model = load_model()
    except Exception as e:
        logging.error(f"Erreur lors du chargement du modèle: {str(e)}")
        print(f"[!] Erreur lors du chargement du modèle YOLO: {str(e)}")
        sys.exit(1)
    
    # Configuration du gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    
    # Démarrage de la détection visuelle
    logging.info("Démarrage de la détection visuelle...")
    print(f"[*] Démarrage de la détection visuelle depuis {args.source}...")
    print("[*] Appuyez sur Ctrl+C pour arrêter")
    
    if args.display:
        print("[*] Fenêtre d'affichage activée (appuyez sur 'q' pour quitter, 's' pour capture, 'h' pour aide)")
    
    # Lance la capture vidéo
    capture_video(args.source, args.conf, args.display, args.record, args.snapshot)

def process_tracking(track):
    """Traite les informations de tracking d'un objet détecté."""
    if track is None:
        return
    # Ici vous pouvez ajouter du code spécifique pour le traitement du tracking
    pass

if __name__ == "__main__":
    main()
