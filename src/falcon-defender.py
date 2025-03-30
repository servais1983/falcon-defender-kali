#!/usr/bin/env python3
#
# Falcon-Defender - Interface utilisateur principale
#

import argparse
import cmd
import json
import logging
import os
import signal
import subprocess
import sys
import time
import threading
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress
    from rich.columns import Columns
    from rich.text import Text
except ImportError:
    print("[!] Erreur: Le module rich est requis.")
    print("    Installez-le avec: pip install rich")
    sys.exit(1)

# Configuration du logger
log_dir = os.path.expanduser("~/.falcon-defender/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"falcon-defender_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Crée la console rich pour l'affichage
console = Console()

class FalconDefenderCLI(cmd.Cmd):
    """Interface en ligne de commande interactive pour Falcon-Defender."""
    
    intro = '''
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║              Falcon-Defender - Détection et défense anti-drone        ║
║                                                                       ║
║  Utilisez les commandes 'help' ou '?' pour afficher l'aide            ║
║  Pour quitter, utilisez 'exit', 'quit' ou Ctrl+D                      ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
'''
    prompt = '[falcon-defender] > '
    file = None
    
    # État des modules
    active_modules = {}
    
    def preloop(self):
        """Initialisation avant la boucle de commande."""
        console.print(Panel(Text("Falcon-Defender v1.0", style="bold"), style="blue"))
        
        # Vérifie les dépendances
        self.check_dependencies()
        
        # Crée les répertoires nécessaires
        self.initialize_directories()
    
    def initialize_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        dirs = [
            "~/.falcon-defender/logs",
            "~/.falcon-defender/results",
            "~/.falcon-defender/detections",
            "~/.falcon-defender/captures",
            "~/.falcon-defender/videos",
            "~/.falcon-defender/audit"
        ]
        
        for d in dirs:
            path = os.path.expanduser(d)
            if not os.path.exists(path):
                try:
                    os.makedirs(path)
                    logging.info(f"Répertoire créé: {path}")
                except Exception as e:
                    logging.error(f"Erreur lors de la création du répertoire {path}: {str(e)}")
    
    def check_dependencies(self):
        """Vérifie que les dépendances requises sont installées."""
        try:
            # Vérifie aircrack-ng
            aircrack = subprocess.run(["which", "aircrack-ng"], capture_output=True, text=True)
            if aircrack.returncode != 0:
                console.print("[bold red]AVERTISSEMENT: aircrack-ng non trouvé, certaines fonctionnalités de scan RF seront limitées[/bold red]")
            
            # Vérifie HackRF
            hackrf = subprocess.run(["which", "hackrf_info"], capture_output=True, text=True)
            if hackrf.returncode != 0:
                console.print("[bold yellow]REMARQUE: HackRF non trouvé, certaines fonctionnalités de scan RF avancées seront désactivées[/bold yellow]")
            
            # Vérifie le modèle YOLOv8
            install_dir = "/opt/falcon-defender"
            if not os.path.exists(os.path.join(install_dir, "models", "yolov8n.pt")) and \
               not os.path.exists(os.path.join(install_dir, "models", "yolov8n-drone.pt")):
                console.print("[bold yellow]REMARQUE: Modèle YOLOv8 non trouvé, la détection visuelle sera limitée[/bold yellow]")
                
        except Exception as e:
            logging.error(f"Erreur lors de la vérification des dépendances: {str(e)}")
    
    def emptyline(self):
        """Ne rien faire quand l'utilisateur entre une ligne vide."""
        pass
    
    def do_exit(self, arg):
        """Quitter le programme."""
        self.stop_all_modules()
        console.print("[bold green]Au revoir ![/bold green]")
        return True
    
    def do_quit(self, arg):
        """Quitter le programme."""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Quitter le programme avec Ctrl+D."""
        print()  # Ajouter une nouvelle ligne
        return self.do_exit(arg)
    
    def stop_all_modules(self):
        """Arrête tous les modules actifs avant de quitter."""
        if not self.active_modules:
            return
            
        console.print("[bold yellow]Arrêt des modules actifs...[/bold yellow]")
        
        for name, process_info in list(self.active_modules.items()):
            process = process_info.get("process")
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                    console.print(f"[green]Module {name} arrêté[/green]")
                except Exception as e:
                    logging.error(f"Erreur lors de l'arrêt du module {name}: {str(e)}")
                    try:
                        process.kill()
                    except:
                        pass
        
        self.active_modules = {}
    
    def do_status(self, arg):
        """Affiche l'état des modules actifs."""
        if not self.active_modules:
            console.print("[yellow]Aucun module actif actuellement[/yellow]")
            return
        
        table = Table(title="Modules actifs")
        table.add_column("Module", style="cyan")
        table.add_column("PID", style="green")
        table.add_column("Démarré", style="yellow")
        table.add_column("Options", style="magenta")
        
        for name, info in self.active_modules.items():
            if "process" in info and info["process"].poll() is None:
                # Le processus est toujours en cours d'exécution
                table.add_row(
                    name,
                    str(info["process"].pid),
                    info["start_time"].strftime("%H:%M:%S"),
                    info.get("options", "")
                )
            else:
                # Le processus s'est terminé
                table.add_row(
                    f"{name} [terminé]",
                    "N/A",
                    info["start_time"].strftime("%H:%M:%S"),
                    info.get("options", "")
                )
        
        console.print(table)
    
    def do_help(self, arg):
        """Affiche l'aide pour les commandes."""
        if arg:
            # Aide pour une commande spécifique
            super().do_help(arg)
        else:
            # Aide générale
            help_text = """
Commandes disponibles:
---------------------
scan        Détection RF/WiFi des drones
vision      Détection visuelle par IA
mavlink     Analyse du protocole MAVLink
safe        Neutralisation sécurisée (usage restreint)
status      Affiche l'état des modules actifs
stop        Arrête un module spécifique
stopall     Arrête tous les modules actifs
results     Affiche les résultats récents
logs        Affiche les journaux récents
help        Affiche cette aide
exit, quit  Quitter le programme

Pour plus d'informations sur une commande spécifique, tapez 'help <commande>'
"""
            console.print(Panel(help_text, title="Aide Falcon-Defender", border_style="blue"))
    
    def do_scan(self, arg):
        """
        Lance la détection RF/WiFi des drones.
        
        Usage: scan -i <interface> [-c <canal>] [-t <durée>] [-v]
            -i, --interface   Interface réseau à utiliser (ex: wlan0)
            -c, --channel     Canal WiFi spécifique à scanner
            -t, --time        Durée du scan en secondes (0 = indéfini)
            -v, --verbose     Mode verbeux
        
        Exemple: scan -i wlan0 -t 300
        """
        if not arg or "-i" not in arg:
            console.print("[bold red]Erreur: L'interface réseau est requise (-i <interface>)[/bold red]")
            self.do_help("scan")
            return
        
        # Exécute falcon-scan avec les arguments fournis
        try:
            cmd = ["falcon-scan"]
            cmd.extend(arg.split())
            
            console.print(f"[bold green]Démarrage de la détection RF/WiFi: {' '.join(cmd)}[/bold green]")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Enregistre le processus
            self.active_modules["scan"] = {
                "process": process,
                "start_time": datetime.now(),
                "options": arg
            }
            
            # Lance un thread pour lire la sortie
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    console.print(f"[cyan][SCAN][/cyan] {line.strip()}")
            
            thread = threading.Thread(target=read_output)
            thread.daemon = True
            thread.start()
            
            console.print("[bold green]Module de scan démarré en arrière-plan.[/bold green]")
            console.print("[bold green]Utilisez 'status' pour voir l'état, 'stop scan' pour arrêter.[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors du démarrage du scan: {str(e)}[/bold red]")
    
    def do_vision(self, arg):
        """
        Lance la détection visuelle des drones par IA.
        
        Usage: vision [--source <source>] [--display] [--record] [--snapshot <secondes>]
            --source    Source vidéo (0 pour webcam, chemin pour fichier, RTSP pour flux)
            --display   Affiche la vidéo en direct
            --record    Enregistre la vidéo avec les détections
            --snapshot  Prend des captures à intervalle régulier (en secondes)
        
        Exemple: vision --source 0 --display
        """
        # Exécute falcon-vision avec les arguments fournis
        try:
            cmd = ["falcon-vision"]
            if arg:
                cmd.extend(arg.split())
            
            console.print(f"[bold green]Démarrage de la détection visuelle: {' '.join(cmd)}[/bold green]")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Enregistre le processus
            self.active_modules["vision"] = {
                "process": process,
                "start_time": datetime.now(),
                "options": arg
            }
            
            # Lance un thread pour lire la sortie
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    console.print(f"[magenta][VISION][/magenta] {line.strip()}")
            
            thread = threading.Thread(target=read_output)
            thread.daemon = True
            thread.start()
            
            console.print("[bold green]Module de vision démarré en arrière-plan.[/bold green]")
            console.print("[bold green]Utilisez 'status' pour voir l'état, 'stop vision' pour arrêter.[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors du démarrage de la détection visuelle: {str(e)}[/bold red]")
    
    def do_mavlink(self, arg):
        """
        Lance la surveillance du protocole MAVLink.
        
        Usage: mavlink [--port <port>] [--host <host>] [--connect <connexion>] [--capture]
            --port      Port UDP à écouter (par défaut: 14550)
            --host      Adresse IP à écouter (par défaut: 0.0.0.0)
            --connect   Connexion directe à un flux MAVLink (ex: udp:192.168.1.1:14550)
            --capture   Capture les paquets MAVLink dans un fichier
        
        Exemple: mavlink --port 14550
        """
        # Exécute falcon-mavlink avec les arguments fournis
        try:
            cmd = ["falcon-mavlink"]
            if arg:
                cmd.extend(arg.split())
            
            console.print(f"[bold green]Démarrage de la surveillance MAVLink: {' '.join(cmd)}[/bold green]")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Enregistre le processus
            self.active_modules["mavlink"] = {
                "process": process,
                "start_time": datetime.now(),
                "options": arg
            }
            
            # Lance un thread pour lire la sortie
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    console.print(f"[blue][MAVLINK][/blue] {line.strip()}")
            
            thread = threading.Thread(target=read_output)
            thread.daemon = True
            thread.start()
            
            console.print("[bold green]Module MAVLink démarré en arrière-plan.[/bold green]")
            console.print("[bold green]Utilisez 'status' pour voir l'état, 'stop mavlink' pour arrêter.[/bold green]")
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors du démarrage de la surveillance MAVLink: {str(e)}[/bold red]")
    
    def do_safe(self, arg):
        """
        Lance les contre-mesures de sécurité (usage restreint).
        
        Usage: safe --connect <connexion> [--action <action>] [--key <fichier_clé>]
            --connect   Connexion au drone (ex: udp:192.168.1.1:14550)
            --action    Action à effectuer: rtl (retour base), land (atterrissage), disarm (désarmement)
            --key       Fichier contenant la clé d'autorisation
        
        Exemple: safe --connect udp:192.168.1.10:14550 --action rtl --key auth.key
        
        AVERTISSEMENT: L'utilisation sans autorisation peut être illégale.
        """
        if not arg or "--connect" not in arg:
            console.print("[bold red]Erreur: La connexion au drone est requise (--connect <connexion>)[/bold red]")
            self.do_help("safe")
            return
        
        # Affiche un avertissement
        warning = """
⚠️  AVERTISSEMENT ⚠️
-------------------
Vous êtes sur le point d'utiliser des contre-mesures actives qui peuvent interférer
avec le fonctionnement d'un drone. Cette action peut être illégale sans autorisation.

Êtes-vous sûr de vouloir continuer? (oui/non): """
        
        console.print(Panel(warning, style="bold red"))
        response = input()
        
        if response.lower() not in ["oui", "o", "yes", "y"]:
            console.print("[yellow]Opération annulée[/yellow]")
            return
        
        # Exécute falcon-safe avec les arguments fournis
        try:
            cmd = ["falcon-safe"]
            cmd.extend(arg.split())
            
            console.print(f"[bold red]Exécution de la contre-mesure: {' '.join(cmd)}[/bold red]")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Pour ce module, on attend la fin plutôt que de le lancer en arrière-plan
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    console.print(f"[red][SAFE][/red] {line.strip()}")
            
            process.wait()
            
            if process.returncode == 0:
                console.print("[bold green]Contre-mesure exécutée avec succès.[/bold green]")
            else:
                console.print("[bold red]Échec de l'exécution de la contre-mesure.[/bold red]")
            
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'exécution de la contre-mesure: {str(e)}[/bold red]")
    
    def do_stop(self, arg):
        """
        Arrête un module spécifique.
        
        Usage: stop <module>
        
        Exemple: stop scan
        """
        if not arg:
            console.print("[bold yellow]Spécifiez le module à arrêter: scan, vision, mavlink[/bold yellow]")
            return
        
        module = arg.strip()
        
        if module not in self.active_modules:
            console.print(f"[bold yellow]Module '{module}' non trouvé ou déjà arrêté[/bold yellow]")
            return
        
        process_info = self.active_modules[module]
        process = process_info.get("process")
        
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
                console.print(f"[bold green]Module {module} arrêté[/bold green]")
                del self.active_modules[module]
            except Exception as e:
                logging.error(f"Erreur lors de l'arrêt du module {module}: {str(e)}")
                console.print(f"[bold red]Erreur lors de l'arrêt du module {module}: {str(e)}[/bold red]")
                try:
                    process.kill()
                    console.print(f"[bold yellow]Module {module} tué de force[/bold yellow]")
                    del self.active_modules[module]
                except:
                    console.print(f"[bold red]Impossible d'arrêter le module {module}[/bold red]")
    
    def do_stopall(self, arg):
        """Arrête tous les modules actifs."""
        self.stop_all_modules()
        console.print("[bold green]Tous les modules ont été arrêtés[/bold green]")
    
    def do_results(self, arg):
        """
        Affiche les résultats récents.
        
        Usage: results [<type>]
            <type> peut être: scan, vision, mavlink (optionnel)
        
        Exemple: results scan
        """
        results_dir = os.path.expanduser("~/.falcon-defender/results")
        
        if not os.path.exists(results_dir):
            console.print("[bold yellow]Aucun résultat trouvé[/bold yellow]")
            return
        
        result_files = []
        for file in os.listdir(results_dir):
            if file.endswith(".json"):
                result_type = None
                if "scan" in file:
                    result_type = "scan"
                elif "vision" in file:
                    result_type = "vision"
                elif "mavlink" in file:
                    result_type = "mavlink"
                
                # Filtre par type si spécifié
                if arg and arg.strip() and result_type != arg.strip():
                    continue
                
                result_files.append({
                    "file": file,
                    "type": result_type,
                    "path": os.path.join(results_dir, file),
                    "time": datetime.fromtimestamp(os.path.getmtime(os.path.join(results_dir, file)))
                })
        
        if not result_files:
            console.print(f"[bold yellow]Aucun résultat {arg if arg else ''} trouvé[/bold yellow]")
            return
        
        # Trie par date (plus récent en premier)
        result_files.sort(key=lambda x: x["time"], reverse=True)
        
        # Affiche les 10 fichiers les plus récents
        table = Table(title="Résultats récents")
        table.add_column("Type", style="cyan")
        table.add_column("Fichier", style="blue")
        table.add_column("Date", style="magenta")
        table.add_column("Détections", style="green")
        
        for result in result_files[:10]:
            # Lit le fichier JSON pour compter les détections
            try:
                with open(result["path"], 'r') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, dict) else 0
            except:
                count = "N/A"
            
            table.add_row(
                result["type"] or "Inconnu",
                result["file"],
                result["time"].strftime("%Y-%m-%d %H:%M:%S"),
                str(count)
            )
        
        console.print(table)
        console.print("[bold green]Pour examiner un fichier en détail: cat ~/.falcon-defender/results/<fichier>[/bold green]")
    
    def do_logs(self, arg):
        """
        Affiche les journaux récents.
        
        Usage: logs [<nombre_lignes>]
            <nombre_lignes> est le nombre de lignes à afficher (par défaut: 20)
        
        Exemple: logs 50
        """
        logs_dir = os.path.expanduser("~/.falcon-defender/logs")
        
        if not os.path.exists(logs_dir):
            console.print("[bold yellow]Aucun journal trouvé[/bold yellow]")
            return
        
        # Nombre de lignes à afficher
        lines = 20
        if arg and arg.strip().isdigit():
            lines = int(arg.strip())
        
        # Trouve le fichier journal le plus récent
        log_files = []
        for file in os.listdir(logs_dir):
            if file.endswith(".log"):
                log_files.append({
                    "file": file,
                    "path": os.path.join(logs_dir, file),
                    "time": datetime.fromtimestamp(os.path.getmtime(os.path.join(logs_dir, file)))
                })
        
        if not log_files:
            console.print("[bold yellow]Aucun journal trouvé[/bold yellow]")
            return
        
        # Trie par date (plus récent en premier)
        log_files.sort(key=lambda x: x["time"], reverse=True)
        latest_log = log_files[0]
        
        # Affiche les dernières lignes du journal
        try:
            with open(latest_log["path"], 'r') as f:
                log_lines = f.readlines()
                
            # Si le fichier a moins de lignes que demandé
            if len(log_lines) < lines:
                lines = len(log_lines)
                
            console.print(Panel(f"Affichage des {lines} dernières lignes du journal: {latest_log['file']}", style="blue"))
            
            # Affiche les dernières lignes avec coloration selon le niveau
            for line in log_lines[-lines:]:
                if "ERROR" in line:
                    console.print(f"[red]{line.strip()}[/red]")
                elif "WARNING" in line:
                    console.print(f"[yellow]{line.strip()}[/yellow]")
                else:
                    console.print(line.strip())
                    
        except Exception as e:
            console.print(f"[bold red]Erreur lors de la lecture du journal: {str(e)}[/bold red]")

def main():
    """Fonction principale."""
    try:
        # Affiche une bannière
        banner = """
  ______      _                  _____        __               _           
 |  ____|    | |                |  __ \\      / _|             | |          
 | |__ __ _  | | ___ ___  _ __ | |  | | ___| |_ ___ _ __   __| | ___ _ __ 
 |  __/ _` | | |/ __/ _ \\| '_ \\| |  | |/ _ \\  _/ _ \\ '_ \\ / _` |/ _ \\ '__|
 | | | (_| | | | (_| (_) | | | | |__| |  __/ ||  __/ | | | (_| |  __/ |   
 |_|  \\__,_| |_|\\___\\___/|_| |_|_____/ \\___|_| \\___|_| |_|\\__,_|\\___|_|   
                                                                           
        """
        print(banner)
        
        # Parse les arguments de la ligne de commande
        parser = argparse.ArgumentParser(description='Falcon-Defender - Détection et défense anti-drone')
        parser.add_argument('--no-interactive', action='store_true', help='Désactive le mode interactif')
        args, remaining = parser.parse_known_args()
        
        if args.no_interactive:
            # Mode non interactif - exécute une commande directement
            if not remaining:
                print("Erreur: Aucune commande spécifiée en mode non interactif")
                print("Exemple: falcon-defender --no-interactive scan -i wlan0")
                return 1
                
            # Reconstruit la commande
            command = ' '.join(remaining)
            
            # Crée une instance de la CLI et exécute la commande
            cli = FalconDefenderCLI()
            cli.preloop()
            
            # Détermine quelle méthode appeler
            cmd_name = remaining[0]
            cmd_args = ' '.join(remaining[1:])
            
            # Mappe le nom de la commande à la méthode
            method_name = f"do_{cmd_name}"
            if hasattr(cli, method_name):
                method = getattr(cli, method_name)
                method(cmd_args)
            else:
                print(f"Erreur: Commande inconnue: {cmd_name}")
                return 1
        else:
            # Mode interactif - lance la boucle de commande
            FalconDefenderCLI().cmdloop()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur")
        return 0
    except Exception as e:
        print(f"Erreur: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
