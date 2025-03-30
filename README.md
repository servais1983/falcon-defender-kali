![falcon_defense](falcon_defense.jpg)

# Falcon-Defender Toolkit 🛡️

Un outil de détection et de défense contre les drones malveillants spécialement conçu pour Kali Linux.

## Fonctionnalités

- Détection de drones via RF/WiFi/MAVLink
- Analyse des signatures de drones commerciaux
- Détection visuelle par IA (YOLOv8)
- Réponse défensive passive (alertes, logs)
- Intégration avec des outils Kali Linux existants
- Visualisation en temps réel des drones détectés

## Prérequis système

- Kali Linux (ou distribution basée sur Debian)
- Python 3.10 ou plus récent
- Minimum 2 GB de RAM
- **Espace disque disponible : au moins 5 GB**
  - L'installation des packages, des modèles d'IA et des dépendances requiert un espace disque significatif
  - Prévoir de l'espace supplémentaire pour les logs, captures et enregistrements vidéo
- Carte réseau compatible avec le mode moniteur (pour les fonctionnalités RF)
- Webcam ou caméra USB (pour les fonctionnalités de détection visuelle)

## Installation

### Méthode standard

```bash
# Cloner le dépôt
git clone https://github.com/servais1983/falcon-defender-kali.git
cd falcon-defender-kali

# Rendre le script d'installation exécutable (ÉTAPE CRUCIALE)
chmod +x install.sh

# Installer les dépendances requises
sudo ./install.sh
```

> ⚠️ **IMPORTANT** : Ne pas oublier la commande `chmod +x install.sh` avant d'exécuter le script. Sans cette étape, l'installation échouera avec l'erreur "command not found".

### Installation sur un système à espace limité

Si vous disposez de peu d'espace disque, vous pouvez optimiser l'installation :

```bash
# Libérer de l'espace avant l'installation
sudo apt clean
sudo apt autoremove -y
sudo apt update

# Installer uniquement les dépendances minimales
sudo apt install -y python3 python3-pip python3-venv python3-pcapy aircrack-ng wireshark-common tshark libpcap-dev

# Procéder à l'installation
chmod +x install.sh
sudo ./install.sh
```

### Installation avec un environnement virtuel personnalisé

Pour les utilisateurs avancés qui préfèrent gérer leur propre environnement Python :

```bash
# Créer un environnement virtuel
python3 -m venv ~/.venvs/falcon
source ~/.venvs/falcon/bin/activate

# Installer les dépendances manuellement
sudo apt install -y aircrack-ng wireshark tshark tcpdump gnuradio hackrf libhackrf-dev libhackrf0 libpcap-dev libssl-dev
pip install -r requirements.txt

# Exécuter le script d'installation avec des options personnalisées
chmod +x install.sh
sudo VENV_DIR=~/.venvs/falcon ./install.sh --no-venv --no-deps
```

### Vérification de l'installation

Pour vérifier que l'installation a réussi, exécutez :

```bash
falcon-defender
```

Vous devriez voir l'écran d'accueil du toolkit avec la liste des modules disponibles.

## Guide d'utilisation

### Interface principale

Falcon-Defender dispose d'une interface en ligne de commande interactive :

```bash
falcon-defender
```

Cette interface vous permet de lancer tous les modules disponibles, contrôler leur état et visualiser les résultats.

### Modules disponibles

#### 1. Détection RF/WiFi

Ce module analyse le trafic WiFi pour détecter les drones selon leurs signatures RF.

```bash
# Avec l'interface principale
[falcon-defender] > scan -i wlan0

# Ou directement en ligne de commande
sudo falcon-scan -i wlan0

# Options avancées
sudo falcon-scan -i wlan0 -c 6 -t 300 -v
```

Options :
- `-i, --interface` : Interface réseau à utiliser (ex: wlan0)
- `-c, --channel` : Canal WiFi spécifique à scanner
- `-t, --time` : Durée du scan en secondes (0 = indéfini)
- `-v, --verbose` : Mode verbeux avec plus de détails

#### 2. Détection visuelle

Ce module utilise l'IA pour détecter visuellement les drones via une caméra.

```bash
# Avec l'interface principale
[falcon-defender] > vision --source 0 --display

# Ou directement en ligne de commande
falcon-vision --source 0 --display
```

Options :
- `--source` : Source vidéo (0 pour webcam, chemin pour fichier, URL RTSP pour flux réseau)
- `--display` : Affiche la vidéo en direct
- `--record` : Enregistre la vidéo avec les détections
- `--snapshot` : Prend des captures à intervalle régulier (en secondes)
- `--conf` : Seuil de confiance pour la détection (0-1)

#### 3. Analyse MAVLink

Ce module intercepte et analyse les communications MAVLink des drones.

```bash
# Avec l'interface principale
[falcon-defender] > mavlink --port 14550

# Ou directement en ligne de commande
falcon-mavlink --port 14550
```

Options :
- `--port` : Port UDP à écouter (par défaut: 14550)
- `--host` : Adresse IP à écouter (par défaut: 0.0.0.0)
- `--connect` : Connexion directe à un flux MAVLink (ex: udp:192.168.1.1:14550)
- `--capture` : Capture les paquets MAVLink dans un fichier

#### 4. Contre-mesures sécurisées (usage restreint)

⚠️ **AVERTISSEMENT** : Ce module permet d'interagir avec des drones et ne doit être utilisé que dans un cadre légal et autorisé.

```bash
# Avec l'interface principale
[falcon-defender] > safe --connect udp:192.168.1.10:14550 --action rtl --key auth.key

# Ou directement en ligne de commande
falcon-safe --connect udp:192.168.1.10:14550 --action rtl --key auth.key
```

Options :
- `--connect` : Connexion au drone (ex: udp:192.168.1.1:14550)
- `--action` : Action à effectuer:
  - `rtl` : Return to Launch (retour à la base)
  - `land` : Atterrissage
  - `disarm` : Désarmement (attention: dangereux si le drone est en vol)
- `--key` : Fichier contenant la clé d'autorisation
- `--sysid` : ID du système cible (par défaut: 1)
- `--compid` : ID du composant cible (par défaut: 1)

### Visualisation des résultats

Pour voir les résultats récents des détections :

```bash
# Avec l'interface principale
[falcon-defender] > results
[falcon-defender] > results scan  # Pour un type spécifique

# Ou directement via le système de fichiers
cat ~/.falcon-defender/results/scan_results_*.json
```

### Journaux (logs)

Pour consulter les journaux :

```bash
# Avec l'interface principale
[falcon-defender] > logs
[falcon-defender] > logs 50  # Affiche les 50 dernières lignes

# Ou directement via le système de fichiers
cat ~/.falcon-defender/logs/*.log
```

## Exemples d'utilisation pratiques

### Scénario 1 : Surveillance d'un périmètre

Pour surveiller un périmètre à la recherche de drones non autorisés :

```bash
# Lancez les deux modules principaux de détection
sudo falcon-scan -i wlan0
falcon-vision --source 0 --display --record
```

### Scénario 2 : Analyse de trafic MAVLink existant

Pour analyser une communication MAVLink existante :

```bash
# Surveillez le port MAVLink standard
falcon-mavlink --port 14550 --capture
```

### Scénario 3 : Configuration complète de surveillance

Pour une surveillance complète avec tous les modules :

```bash
# Utilisez l'interface principale
falcon-defender

# Puis lancez les modules
[falcon-defender] > scan -i wlan0
[falcon-defender] > vision --source rtsp://surveillance_camera_url --record
[falcon-defender] > mavlink --port 14550

# Vérifiez l'état des modules
[falcon-defender] > status
```

## Structure des fichiers et données

- Les résultats sont stockés dans `~/.falcon-defender/results/`
- Les journaux sont stockés dans `~/.falcon-defender/logs/`
- Les captures d'écran sont stockées dans `~/.falcon-defender/detections/`
- Les vidéos enregistrées sont stockées dans `~/.falcon-defender/videos/`
- Les captures réseau sont stockées dans `~/.falcon-defender/captures/`

## Considérations légales

L'utilisation de Falcon-Defender doit être conforme aux lois et réglementations locales. Certaines fonctionnalités peuvent être soumises à autorisation selon votre juridiction.

- L'analyse RF passive est généralement légale
- L'interférence active avec les communications drone est souvent **illégale**
- Consultez les régulations locales avant utilisation

## Personnalisation

- Les signatures de drones peuvent être modifiées dans `config/drone_signatures.json`
- Les zones d'exclusion géographiques peuvent être définies dans `config/geofence_zones.yml`
- Les paramètres d'alerte peuvent être configurés dans un fichier JSON séparé

## Résolution de problèmes

### Problèmes d'installation courants

```bash
# Si vous obtenez l'erreur "command not found" lors de l'exécution du script d'installation
chmod +x install.sh
sudo ./install.sh

# Si vous rencontrez des erreurs de dépendances
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev
```

### Erreurs de dépendances Python spécifiques

Si vous rencontrez des erreurs avec certaines dépendances Python comme pcapy :

```bash
# Installer pcapy via apt plutôt que pip
sudo apt install python3-pcapy

# Modifier le fichier requirements.txt pour ignorer cette dépendance
sed -i 's/pcapy>=0.11.5/# pcapy>=0.11.5 # Installé via apt/g' requirements.txt

# Installer une alternative
sudo apt install -y libpcap-dev
sudo /opt/falcon-defender/venv/bin/pip install pcapy-ng
```

De même pour gnuradio :
```bash
sudo apt install -y gnuradio
sed -i 's/gnuradio-companion>=3.10.0/# gnuradio-companion>=3.10.0 # Installé via apt/g' requirements.txt
```

### Problèmes d'espace disque

Si vous rencontrez l'erreur "No space left on device" pendant l'installation :

```bash
# Libérer de l'espace
sudo apt clean
sudo apt autoremove -y
sudo journalctl --vacuum-time=1d

# Vérifier l'espace disponible
df -h
```

Vous pouvez également installer Falcon-Defender sur un disque externe :

```bash
# Monter un disque externe
sudo mkdir -p /mnt/external
sudo mount /dev/sdX1 /mnt/external  # Remplacez X1 par votre partition

# Créer un lien symbolique pour l'installation
sudo mkdir -p /mnt/external/falcon-defender
sudo ln -s /mnt/external/falcon-defender /opt/falcon-defender

# Continuer l'installation
sudo ./install.sh
```

### Problèmes de versions Python

Si vous rencontrez des problèmes avec Python 3.13 ou versions ultérieures :

```bash
# Créer un environnement virtuel avec une version spécifique de Python
sudo apt install python3.11 python3.11-venv python3.11-dev
python3.11 -m venv /opt/falcon-defender/venv
sudo /opt/falcon-defender/venv/bin/pip install --upgrade pip
sudo /opt/falcon-defender/venv/bin/pip install -r requirements.txt
```

### L'interface réseau n'est pas en mode moniteur

```bash
# Mettre manuellement l'interface en mode moniteur
sudo airmon-ng start wlan0
```

### Erreurs de permission

```bash
# Assurez-vous d'exécuter avec sudo pour les fonctionnalités réseau
sudo falcon-scan -i wlan0

# Si vous obtenez des erreurs de permission sur les fichiers de log ou résultats
sudo chown -R $USER:$USER ~/.falcon-defender
```

### Modèle YOLOv8 non trouvé

```bash
# Téléchargez manuellement le modèle
mkdir -p ~/.falcon-defender/models
wget https://github.com/ultralytics/assets/releases/download/v8.0/yolov8n.pt -O ~/.falcon-defender/models/yolov8n.pt
```

### Problèmes avec Docker

Si vous utilisez Docker sur Kali Linux et rencontrez des erreurs de dépôt :

```bash
# Supprimer le dépôt Docker problématique
sudo rm /etc/apt/sources.list.d/docker.list

# Ajouter le dépôt Docker pour Debian Bullseye (compatible avec Kali)
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian bullseye stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

## Contribution

Les contributions sont les bienvenues! Veuillez consulter le fichier CONTRIBUTING.md pour plus d'informations.

## Licence

GPL-3.0 - Voir le fichier LICENSE pour plus de détails.