![Logo_falcon_defense](images/falcon_defense.jpg)

# Falcon-Defender Toolkit 🛡️

Un outil de détection et de défense contre les drones malveillants spécialement conçu pour Kali Linux.

## Fonctionnalités

- Détection de drones via RF/WiFi/MAVLink
- Analyse des signatures de drones commerciaux
- Détection visuelle par IA (YOLOv8)
- Réponse défensive passive (alertes, logs)
- Intégration avec des outils Kali Linux existants
- Visualisation en temps réel des drones détectés

## Installation

```bash
# Cloner le dépôt
git clone 
https://github.com/servais1983/falcon-defender-kali.git
cd falcon-defender-kali

# Installer les dépendances requises
sudo ./
install.sh
```

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

### L'interface réseau n'est pas en mode moniteur

```bash
# Mettre manuellement l'interface en mode moniteur
sudo airmon-ng start wlan0
```

### Erreurs de permission

```bash
# Assurez-vous d'exécuter avec sudo pour les fonctionnalités réseau
sudo falcon-scan -i wlan0
```

### Modèle YOLOv8 non trouvé

```bash
# Téléchargez manuellement le modèle
mkdir -p ~/.falcon-defender/models
wget https://github.com/ultralytics/assets/releases/download/v8.0/yolov8n.pt -O ~/.falcon-defender/models/yolov8n.pt
```

## Contribution

Les contributions sont les bienvenues! Veuillez consulter le fichier CONTRIBUTING.md pour plus d'informations.

## Licence

GPL-3.0 - Voir le fichier LICENSE pour plus de détails.
