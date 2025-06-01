![falcon_defense](falcon_defense.jpg)

# Falcon-Defender Toolkit 🛡️

Un outil de détection et de défense contre les drones malveillants spécialement conçu pour Kali Linux.

---

## 📑 Table des matières
- [Fonctionnalités](#fonctionnalités)
- [Prérequis système](#prérequis-système)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [Utilisation](#utilisation)
- [Simulation](#simulation)
- [Tests](#tests)
- [Sécurité](#sécurité)
- [Considérations légales](#considérations-légales)
- [Licence](#licence)

---

## 🚀 Fonctionnalités

* 📡 Détection de drones via RF/WiFi/MAVLink
* 🛩️ Analyse des signatures de drones commerciaux
* 🤖 Détection visuelle par IA (YOLOv8)
* 🚨 Réponse défensive passive (alertes, logs)
* 🛠️ Intégration avec des outils Kali Linux existants
* 📊 Visualisation en temps réel des drones détectés
* 🔒 Système de sécurité avancé avec :
  * 🔑 Chiffrement des données sensibles
  * 🔐 Authentification à deux facteurs (2FA)
  * 🗝️ Gestion sécurisée des sessions
  * 🛡️ Protection contre les attaques par force brute
  * ♻️ Rotation automatique des clés
  * 🧹 Nettoyage sécurisé de la mémoire
  * 🧑‍💻 **Nouveau :** Module d'exploitation pour l'analyse et la détection des vulnérabilités drones

---

## 🖥️ Prérequis système

* 🐧 Kali Linux (ou distribution basée sur Debian)
* 🐍 Python 3.10 ou plus récent
* 💾 Minimum 2 GB de RAM
* 💽 **Espace disque disponible : au moins 5 GB**  
   * L'installation des packages, des modèles d'IA et des dépendances requiert un espace disque significatif  
   * Prévoir de l'espace supplémentaire pour les logs, captures et enregistrements vidéo
* 📡 Carte réseau compatible avec le mode moniteur (pour les fonctionnalités RF)
* 🎥 Webcam ou caméra USB (pour les fonctionnalités de détection visuelle)

---

## ⚙️ Installation

### Méthode standard (Linux)

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

---

## 🗂️ Structure du projet

```
falcon-defender-kali/
├── src/                    # Code source principal
│   ├── falcon-defender.py  # Interface principale (CLI)
│   ├── falcon-scan.py      # Module de scan RF/WiFi
│   ├── falcon-vision.py    # Module de détection visuelle
│   ├── falcon-safe.py      # Module de contre-mesures
│   ├── security.py         # Module de sécurité
│   └── exploitation.py     # Module d'exploitation (audit vulnérabilités)
├── simulation/             # 📦 Simulateur de drones et de trafic (voir section Simulation)
├── tests/                  # 🧪 Tests unitaires
├── config/                 # ⚙️ Fichiers de configuration (signatures, vulnérabilités, etc.)
├── models/                 # 🤖 Modèles d'IA (YOLO, etc.)
└── logs/                   # 📝 Journaux système
```

---

## 🕹️ Utilisation

### Interface principale

```bash
falcon-defender
```
Lance l'interface CLI interactive pour piloter tous les modules.

### Modules individuels

1. **Scan RF/WiFi** (`falcon-scan`)
   - Détecte les drones via les signaux RF/WiFi.
   - **Exemple :**
     ```bash
     falcon-scan -i wlan0
     ```
   - **Options principales :**
     - `-i, --interface` : Interface réseau à utiliser (ex: wlan0)
     - `-c, --channel` : Canal WiFi spécifique à scanner
     - `-t, --time` : Durée du scan en secondes
     - `-v, --verbose` : Mode verbeux

2. **Détection visuelle** (`falcon-vision`)
   - Détecte les drones par caméra et IA.
   - **Exemple :**
     ```bash
     falcon-vision --source 0 --display
     ```
   - **Options principales :**
     - `--source` : Source vidéo (0 = webcam, chemin fichier, URL RTSP)
     - `--display` : Affiche la vidéo en direct
     - `--record` : Enregistre la vidéo
     - `--conf` : Seuil de confiance IA

3. **Analyse MAVLink** (`falcon-mavlink`)
   - Analyse le trafic MAVLink (protocole drone)
   - **Exemple :**
     ```bash
     falcon-mavlink --port 14550
     ```
   - **Options principales :**
     - `--port` : Port UDP à écouter (défaut : 14550)
     - `--host` : Adresse IP à écouter
     - `--connect` : Connexion directe à un flux MAVLink
     - `--capture` : Capture les paquets dans un fichier

4. **Contre-mesures sécurisées** (`falcon-safe`)
   - Envoie des commandes sécurisées au drone (RTL, atterrissage, désarmement)
   - **Exemple :**
     ```bash
     falcon-safe --connect udp:192.168.1.10:14550 --action rtl --key auth.key
     ```
   - **Options principales :**
     - `--connect` : Connexion au drone (ex: udp:192.168.1.1:14550)
     - `--action` : Action (`rtl`, `land`, `disarm`)
     - `--key` : Fichier de clé d'autorisation
     - `--sysid`, `--compid` : IDs cibles

5. **Exploitation des vulnérabilités** (`exploitation.py`)
   - Analyse une cible et génère un rapport sur les vulnérabilités connues.
   - **Exemple :**
     ```bash
     python src/exploitation.py
     ```
   - Personnalisez la cible dans le script ou utilisez-le comme module Python.
   - Les vulnérabilités sont définies dans `config/vulnerabilities.json`.

---

## 🛰️ Simulation

Le dossier `simulation/` permet de simuler des drones, du trafic RF/MAVLink et des attaques pour tester Falcon-Defender sans matériel réel.

- **Lancer le simulateur :**
  ```bash
  cd simulation
  python simulator.py
  ```
- **Fonctionnalités :**
  - Génération de faux signaux RF/WiFi
  - Simulation de trafic MAVLink
  - Scénarios d'attaque (DoS, spoofing, etc.)
- **Utilité :**
  - Tester les modules de détection et d'exploitation en environnement contrôlé
  - Démonstrations pédagogiques

---

## 🧪 Tests

Pour exécuter tous les tests unitaires (y compris le module exploitation) :

```bash
python -m pytest tests/
```

---

## 🔒 Sécurité

Le projet implémente plusieurs mesures de sécurité :

* 🔑 Chiffrement AES-256 pour les données sensibles
* 🔐 Authentification à deux facteurs
* 🛡️ Protection contre les attaques par force brute
* ♻️ Rotation automatique des clés
* 🧹 Nettoyage sécurisé de la mémoire
* 📝 Journalisation sécurisée des événements

---

## ⚖️ Considérations légales

L'utilisation de Falcon-Defender doit être conforme aux lois et réglementations locales. Certaines fonctionnalités peuvent être soumises à autorisation selon votre juridiction.

---

## 📄 Licence

GPL-3.0 - Voir le fichier LICENSE pour plus de détails.
