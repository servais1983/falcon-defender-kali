![falcon_defense](falcon_defense.jpg)

# Falcon-Defender Toolkit 🛡️

Un outil de détection et de défense contre les drones malveillants spécialement conçu pour Kali Linux.

## Fonctionnalités

* Détection de drones via RF/WiFi/MAVLink
* Analyse des signatures de drones commerciaux
* Détection visuelle par IA (YOLOv8)
* Réponse défensive passive (alertes, logs)
* Intégration avec des outils Kali Linux existants
* Visualisation en temps réel des drones détectés
* Système de sécurité avancé avec :
  * Chiffrement des données sensibles
  * Authentification à deux facteurs (2FA)
  * Gestion sécurisée des sessions
  * Protection contre les attaques par force brute
  * Rotation automatique des clés
  * Nettoyage sécurisé de la mémoire

## Prérequis système

* Kali Linux (ou distribution basée sur Debian)
* Python 3.10 ou plus récent
* Minimum 2 GB de RAM
* **Espace disque disponible : au moins 5 GB**  
   * L'installation des packages, des modèles d'IA et des dépendances requiert un espace disque significatif  
   * Prévoir de l'espace supplémentaire pour les logs, captures et enregistrements vidéo
* Carte réseau compatible avec le mode moniteur (pour les fonctionnalités RF)
* Webcam ou caméra USB (pour les fonctionnalités de détection visuelle)

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

### Installation sur Windows

```bash
# Exécuter le script d'installation Windows
install.bat
```

## Structure du projet

```
falcon-defender-kali/
├── src/                    # Code source principal
│   ├── falcon-defender.py  # Interface principale
│   ├── falcon-scan.py      # Module de scan RF/WiFi
│   ├── falcon-vision.py    # Module de détection visuelle
│   ├── falcon-safe.py      # Module de contre-mesures
│   ├── security.py         # Module de sécurité
│   └── exploitation.py     # Module d'exploitation
├── tests/                  # Tests unitaires
├── config/                 # Fichiers de configuration
├── models/                 # Modèles d'IA
└── logs/                   # Journaux système
```

## Utilisation

### Interface principale

```bash
falcon-defender
```

### Modules individuels

1. **Scan RF/WiFi**
```bash
falcon-scan -i wlan0
```

2. **Détection visuelle**
```bash
falcon-vision --source 0 --display
```

3. **Analyse MAVLink**
```bash
falcon-mavlink --port 14550
```

4. **Contre-mesures sécurisées**
```bash
falcon-safe --connect udp:192.168.1.10:14550 --action rtl --key auth.key
```

## Tests

Pour exécuter les tests unitaires :

```bash
python -m pytest tests/
```

## Sécurité

Le projet implémente plusieurs mesures de sécurité :

* Chiffrement AES-256 pour les données sensibles
* Authentification à deux facteurs
* Protection contre les attaques par force brute
* Rotation automatique des clés
* Nettoyage sécurisé de la mémoire
* Journalisation sécurisée des événements

## Considérations légales

L'utilisation de Falcon-Defender doit être conforme aux lois et réglementations locales. Certaines fonctionnalités peuvent être soumises à autorisation selon votre juridiction.

## Licence

GPL-3.0 - Voir le fichier LICENSE pour plus de détails.
