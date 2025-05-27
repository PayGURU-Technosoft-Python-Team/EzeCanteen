import hashlib
import base64
import os

def encrypt_password(password):
    """
    Encrypts a password using SHA-256 with a random salt
    Returns a base64 encoded string containing the salt and hash
    """
    # Generate a random salt
    salt = os.urandom(16)
    
    # Hash the password with the salt
    hash_obj = hashlib.sha256()
    hash_obj.update(salt + password.encode('utf-8'))
    password_hash = hash_obj.digest()
    
    # Combine salt and hash and encode to base64 for storage
    combined = salt + password_hash
    encoded = base64.b64encode(combined).decode('utf-8')
    
    return encoded

def verify_password(stored_password, input_password):
    """
    Verifies if the input password matches the stored hashed password
    """
    try:
        # Decode the stored password from base64
        decoded = base64.b64decode(stored_password)
        
        # Extract the salt (first 16 bytes)
        salt = decoded[:16]
        stored_hash = decoded[16:]
        
        # Hash the input password with the same salt
        hash_obj = hashlib.sha256()
        hash_obj.update(salt + input_password.encode('utf-8'))
        input_hash = hash_obj.digest()
        
        # Compare the hashes
        return input_hash == stored_hash
    except:
        return False

def cannot_decrypt_password(stored_password):
    """
    This function demonstrates why password hashes cannot be decrypted.
    SHA-256 is a one-way cryptographic hash function - it's mathematically
    designed to be irreversible.
    """
    print("=== Password Decryption Attempt ===")
    print(f"Stored hash: {stored_password}")
    print("\nWhy decryption is impossible:")
    print("1. SHA-256 is a one-way hash function")
    print("2. Multiple different inputs can produce the same hash")
    print("3. The original password information is mathematically lost")
    print("4. This is intentional for security - passwords should never be recoverable")
    print("\nInstead of decryption, use password verification!")
    return None

def demonstrate_password_system():
    """
    Demonstrates the complete password system
    """
    print("=== Password Hashing System Demo ===\n")
    
    # Original password
    original_password = "mySecretPassword123"
    print(f"Original password: {original_password}")
    
    # Hash the password
    hashed_password = encrypt_password(original_password)
    print(f"Hashed password: {hashed_password}")
    
    # Show the components
    decoded = base64.b64decode(hashed_password)
    salt = decoded[:16]
    hash_part = decoded[16:]
    print(f"Salt (hex): {salt.hex()}")
    print(f"Hash (hex): {hash_part.hex()}")
    
    print("\n=== Password Verification ===")
    
    # Test correct password
    correct_test = verify_password(hashed_password, "mySecretPassword123")
    print(f"Correct password verification: {correct_test}")
    
    # Test wrong password
    wrong_test = verify_password(hashed_password, "wrongPassword")
    print(f"Wrong password verification: {wrong_test}")
    
    print("\n")
    # Demonstrate why decryption is impossible
    cannot_decrypt_password(hashed_password)

if __name__ == "__main__":
    demonstrate_password_system()