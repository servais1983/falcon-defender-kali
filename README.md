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
git clone https://github.com/servais1983/falcon-defender-kali.git
cd falcon-defender-kali

# Installer les dépendances requises
sudo ./install.sh
```

## Utilisation

```bash
# Lancer la détection RF de base
sudo falcon-scan -i wlan0

# Détecter et analyser les communications MAVLink
sudo falcon-mavlink --port 14550

# Détection visuelle (nécessite une caméra)
falcon-vision --source 0

# Interface complète mode TUI (Terminal User Interface)
falcon-defender
```

## Architecture

Falcon-Defender est organisé en plusieurs modules:

- **falcon-scan**: Détection RF/WiFi des drones
- **falcon-vision**: Détection visuelle des drones avec YOLOv8
- **falcon-mavlink**: Analyse du protocole MAVLink
- **falcon-defender**: Interface utilisateur principale et coordination
- **falcon-safe**: Contre-mesures défensives (nécessite autorisation)

## Considérations légales

L'utilisation de Falcon-Defender doit être conforme aux lois et réglementations locales. Certaines fonctionnalités peuvent être soumises à autorisation selon votre juridiction.

- L'analyse RF passive est généralement légale
- L'interférence active avec les communications drone est souvent **illégale**
- Consultez les régulations locales avant utilisation

## Contribution

Les contributions sont les bienvenues! Veuillez consulter le fichier CONTRIBUTING.md pour plus d'informations.

## Licence

GPL-3.0 - Voir le fichier LICENSE pour plus de détails.