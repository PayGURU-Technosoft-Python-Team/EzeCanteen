import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Secret key used for deriving the encryption key
SECRET_KEY = b'EzeeCanteen_PayGURU_SECRET_KEY_2023'

def get_encryption_key():
    """Generate a consistent encryption key from the SECRET_KEY"""
    salt = b'static_salt_value_for_consistency'  # Using static salt for key derivation
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY))
    return key

def encrypt_password(password):
    """
    Encrypts a password using Fernet symmetric encryption
    Returns a base64 encoded encrypted string
    """
    if not password:
        return ""
    
    key = get_encryption_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(password.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')

def decrypt_password(encrypted_password):
    """
    Decrypts a password that was encrypted with encrypt_password
    Returns the original password as a string
    """
    if not encrypted_password:
        return ""
    
    try:
        key = get_encryption_key()
        f = Fernet(key)
        decrypted_data = f.decrypt(base64.urlsafe_b64decode(encrypted_password.encode('utf-8')))
        return decrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""

def verify_password(stored_password, input_password):
    """
    Verifies if the input password matches the stored encrypted password
    """
    decrypted = decrypt_password(stored_password)
    return decrypted == input_password

