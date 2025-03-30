#!/bin/bash
#
# Script d'installation Falcon-Defender pour Kali Linux
#

set -e  # Exit on error

# Couleurs pour une meilleure lisibilité
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   Falcon-Defender - Script d'installation   ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo ""

# Vérifie si le script est exécuté avec sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] Ce script doit être exécuté avec sudo${NC}"
  exit 1
fi

# Vérifie que nous sommes bien sur Kali Linux ou une distribution compatible
if ! command -v apt-get &> /dev/null; then
    echo -e "${YELLOW}[!] Ce script est conçu pour Kali Linux ou une distribution basée sur Debian${NC}"
    echo -e "${YELLOW}[!] Vous pouvez continuer, mais certaines fonctionnalités pourraient ne pas fonctionner correctement${NC}"
    read -p "Continuer? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[*] Mise à jour des dépôts...${NC}"
apt-get update

echo -e "${GREEN}[*] Installation des dépendances système...${NC}"
apt-get install -y python3 python3-pip python3-dev python3-venv \
                   aircrack-ng wireshark tshark tcpdump \
                   gnuradio hackrf libhackrf-dev libhackrf0 \
                   libpcap-dev libssl-dev

# Vérifie si hackrf est disponible
if ! command -v hackrf_info &> /dev/null; then
    echo -e "${YELLOW}[!] HackRF n'a pas pu être installé correctement${NC}"
    echo -e "${YELLOW}[!] Certaines fonctionnalités de détection RF seront limitées${NC}"
else
    echo -e "${GREEN}[+] HackRF installé correctement${NC}"
fi

# Crée un environnement virtuel Python
echo -e "${GREEN}[*] Création d'un environnement virtuel Python...${NC}"
VENV_DIR="/opt/falcon-defender/venv"
mkdir -p /opt/falcon-defender
python3 -m venv $VENV_DIR

# Installe les dépendances Python
echo -e "${GREEN}[*] Installation des dépendances Python...${NC}"
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r requirements.txt

# Copie les fichiers dans le répertoire d'installation
echo -e "${GREEN}[*] Copie des fichiers...${NC}"
INSTALL_DIR="/opt/falcon-defender"
mkdir -p $INSTALL_DIR/config $INSTALL_DIR/logs $INSTALL_DIR/results $INSTALL_DIR/models

# Copie des scripts Python
cp -r src/* $INSTALL_DIR/
chmod +x $INSTALL_DIR/*.py

# Crée les liens symboliques dans /usr/local/bin
echo -e "${GREEN}[*] Création des liens symboliques...${NC}"
for script in falcon-scan falcon-vision falcon-mavlink falcon-safe; do
    cat > /usr/local/bin/$script << EOF
#!/bin/bash
source $VENV_DIR/bin/activate
exec python3 $INSTALL_DIR/$script.py "\$@"
EOF
    chmod +x /usr/local/bin/$script
done

# Crée un script principal falcon-defender
cat > /usr/local/bin/falcon-defender << EOF
#!/bin/bash
echo "Falcon-Defender Toolkit pour Kali Linux"
echo "======================================="
echo ""
echo "Modules disponibles:"
echo "  falcon-scan    - Détection RF/WiFi des drones"
echo "  falcon-vision  - Détection visuelle par IA"
echo "  falcon-mavlink - Analyse du protocole MAVLink"
echo "  falcon-safe    - Neutralisation sécurisée (usage restreint)"
echo ""
echo "Exemple d'utilisation:"
echo "  falcon-scan -i wlan0         # Détection sur interface wlan0"
echo "  falcon-vision --source 0     # Détection visuelle avec webcam"
echo "  falcon-mavlink --port 14550  # Écoute MAVLink sur UDP port 14550"
echo ""
EOF
chmod +x /usr/local/bin/falcon-defender

# Copie les fichiers de configuration par défaut
echo -e "${GREEN}[*] Création des fichiers de configuration...${NC}"
if [ ! -f $INSTALL_DIR/config/drone_signatures.json ]; then
    cp config/drone_signatures.json $INSTALL_DIR/config/
fi

if [ ! -f $INSTALL_DIR/config/geofence_zones.yml ]; then
    cp config/geofence_zones.yml $INSTALL_DIR/config/
fi

# Télécharge le modèle YOLOv8 si nécessaire
echo -e "${GREEN}[*] Vérification du modèle YOLOv8...${NC}"
if [ ! -f $INSTALL_DIR/models/yolov8n-drone.pt ]; then
    echo -e "${YELLOW}[!] Modèle YOLOv8 spécifique pour drones non trouvé${NC}"
    echo -e "${GREEN}[*] Téléchargement du modèle YOLOv8 générique...${NC}"
    
    # Télécharge le modèle YOLOv8 nanoscale
    $VENV_DIR/bin/pip install --upgrade ultralytics
    $VENV_DIR/bin/python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').save('$INSTALL_DIR/models/yolov8n.pt')"
    
    echo -e "${YELLOW}[!] Remarque: Pour de meilleures performances, entraînez un modèle spécifique pour drones${NC}"
else
    echo -e "${GREEN}[+] Modèle YOLOv8 pour drones trouvé${NC}"
fi

# Crée les répertoires pour les logs et résultats
echo -e "${GREEN}[*] Création des répertoires de données...${NC}"
mkdir -p ~/.falcon-defender/{logs,results,detections,videos,captures,audit}
chmod -R 755 ~/.falcon-defender

echo -e "${GREEN}[+] Installation terminée avec succès!${NC}"
echo ""
echo -e "${BLUE}Vous pouvez maintenant utiliser Falcon-Defender:${NC}"
echo -e "${BLUE}  - Tapez 'falcon-defender' pour voir les options disponibles${NC}"
echo -e "${BLUE}  - Exemple: 'falcon-scan -i wlan0' pour scanner avec l'interface wlan0${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Assurez-vous d'utiliser cet outil conformément aux lois et réglementations locales${NC}"
echo -e "${YELLOW}           L'interférence avec des drones peut être illégale dans votre juridiction${NC}"
echo ""
