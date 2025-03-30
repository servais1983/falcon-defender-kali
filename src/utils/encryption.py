#!/usr/bin/env python3
#
# Falcon-Defender - Module de chiffrement et sécurité
#

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
except ImportError:
    logging.error("Le module cryptography est requis.")
    logging.error("Installez-le avec: pip install cryptography")
    raise

class AESEncryptor:
    """
    Classe pour le chiffrement et déchiffrement AES-GCM.
    """
    def __init__(self, key=None):
        """
        Initialise un chiffreur AES-GCM avec une clé donnée ou générée aléatoirement.
        """
        self.key = key or os.urandom(32)  # AES-256 (32 octets)
        self.backend = default_backend()
    
    def encrypt(self, plaintext):
        """
        Chiffre les données avec AES-GCM.
        Retourne un tuple (iv, ciphertext, tag).
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
            
        # Génère un vecteur d'initialisation aléatoire
        iv = os.urandom(12)  # 96 bits recommandé pour GCM
        
        # Crée le chiffreur
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        
        # Chiffre les données
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Retourne IV, texte chiffré et tag d'authentification
        return (iv, ciphertext, encryptor.tag)
    
    def decrypt(self, iv, ciphertext, tag):
        """
        Déchiffre les données avec AES-GCM.
        """
        # Crée le déchiffreur
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=self.backend
        )
        decryptor = cipher.decryptor()
        
        # Déchiffre les données
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext
    
    def encrypt_to_base64(self, plaintext):
        """
        Chiffre et encode en Base64 pour faciliter le stockage/transmission.
        """
        iv, ciphertext, tag = self.encrypt(plaintext)
        
        # Concatène les éléments et encode en Base64
        combined = iv + tag + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_from_base64(self, encoded_data):
        """
        Décode de Base64 et déchiffre.
        """
        # Décode de Base64
        combined = base64.b64decode(encoded_data)
        
        # Extrait les composants
        iv = combined[:12]
        tag = combined[12:28]  # 16 octets pour le tag GCM
        ciphertext = combined[28:]
        
        # Déchiffre
        plaintext = self.decrypt(iv, ciphertext, tag)
        
        # Retourne en texte si c'était du texte à l'origine
        try:
            return plaintext.decode('utf-8')
        except UnicodeDecodeError:
            return plaintext

class TokenManager:
    """
    Gère la création et validation de jetons d'authentification.
    """
    def __init__(self, secret_key=None):
        """
        Initialise avec une clé secrète donnée ou générée.
        """
        self.secret_key = secret_key or os.urandom(32)
    
    def generate_token(self, user_id, expiry_hours=24):
        """
        Génère un jeton d'authentification avec une date d'expiration.
        """
        # Crée les données du jeton
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
        payload = {
            "user_id": user_id,
            "exp": expiry.timestamp(),
            "iat": datetime.utcnow().timestamp()
        }
        
        # Sérialise en JSON
        payload_json = json.dumps(payload)
        
        # Chiffre avec AES
        encryptor = AESEncryptor(self.secret_key)
        encrypted_token = encryptor.encrypt_to_base64(payload_json)
        
        # Ajoute une signature HMAC
        signature = hmac.new(
            self.secret_key,
            encrypted_token.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Combine le jeton et la signature
        return f"{encrypted_token}.{signature}"
    
    def validate_token(self, token):
        """
        Vérifie si un jeton est valide et non expiré.
        Retourne les données du jeton si valide, None sinon.
        """
        try:
            # Sépare le jeton et la signature
            encrypted_token, signature = token.split('.')
            
            # Vérifie la signature
            expected_sig = hmac.new(
                self.secret_key,
                encrypted_token.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_sig, signature):
                logging.warning("Signature de jeton invalide")
                return None
            
            # Déchiffre le jeton
            encryptor = AESEncryptor(self.secret_key)
            payload_json = encryptor.decrypt_from_base64(encrypted_token)
            
            # Désérialise le JSON
            payload = json.loads(payload_json)
            
            # Vérifie l'expiration
            if payload["exp"] < time.time():
                logging.warning("Jeton expiré")
                return None
            
            return payload
            
        except Exception as e:
            logging.error(f"Erreur lors de la validation du jeton: {str(e)}")
            return None

# Fonction pour vérifier l'autorisation pour falcon-safe.py
def verify_authorization(key_data):
    """
    Vérifie si une clé d'autorisation est valide pour les contre-mesures.
    Fonction factice pour l'exemple - À remplacer par une implémentation sécurisée.
    """
    try:
        # Format attendu: JSON contenant une autorisation signée
        data = json.loads(key_data)
        
        if not all(k in data for k in ["token", "authority", "expiry"]):
            logging.error("Format de clé d'autorisation invalide")
            return False
        
        # Vérifie l'expiration
        expiry = datetime.fromisoformat(data["expiry"])
        if expiry < datetime.utcnow():
            logging.error(f"Autorisation expirée depuis {expiry}")
            return False
            
        # Dans une implémentation réelle, vérifiez la signature cryptographique ici
        
        logging.info(f"Autorisation validée, émise par {data['authority']}")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la vérification d'autorisation: {str(e)}")
        return False

# Fonction pour chiffrer les logs sensibles
def encrypt_log_entry(log_entry, key=None):
    """
    Chiffre une entrée de log pour la stocker de manière sécurisée.
    """
    encryptor = AESEncryptor(key)
    return encryptor.encrypt_to_base64(json.dumps(log_entry))

# Fonction pour déchiffrer les logs
def decrypt_log_entry(encrypted_entry, key):
    """
    Déchiffre une entrée de log stockée.
    """
    encryptor = AESEncryptor(key)
    try:
        decrypted = encryptor.decrypt_from_base64(encrypted_entry)
        return json.loads(decrypted)
    except Exception as e:
        logging.error(f"Erreur lors du déchiffrement du log: {str(e)}")
        return None