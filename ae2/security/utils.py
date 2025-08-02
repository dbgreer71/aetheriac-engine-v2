"""
Security utilities for AE v2.

This module provides utility functions for security operations.
"""

import hashlib
import secrets
import string
import re
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization


class SecurityUtils:
    """Security utility functions."""
    
    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate a secure random password."""
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")
        
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]
        
        # Fill the rest with random characters
        all_chars = lowercase + uppercase + digits + symbols
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))
        
        # Shuffle the password
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        
        return ''.join(password_list)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """Validate password strength and return issues."""
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not re.search(r"[a-z]", password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"[A-Z]", password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"\d", password):
            issues.append("Password must contain at least one digit")
        
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
            issues.append("Password must contain at least one special character")
        
        # Check for common patterns
        common_patterns = [
            "password", "123456", "qwerty", "admin", "user",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                issues.append(f"Password contains common pattern: {pattern}")
                break
        
        # Check for repeated characters
        if re.search(r"(.)\1{2,}", password):
            issues.append("Password contains too many repeated characters")
        
        # Check for sequential characters
        if re.search(r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)", password_lower):
            issues.append("Password contains sequential characters")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash a password with a salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        return base64.b64encode(key).decode(), salt
    
    @staticmethod
    def verify_password_hash(password: str, hash_value: str, salt: str) -> bool:
        """Verify a password against its hash."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            
            kdf.verify(password.encode(), base64.b64decode(hash_value))
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_jwt_token(payload: dict, secret_key: str, algorithm: str = "HS256", expires_in: int = 3600) -> str:
        """Generate a JWT token."""
        payload_copy = payload.copy()
        payload_copy.update({
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in)
        })
        
        return jwt.encode(payload_copy, secret_key, algorithm=algorithm)
    
    @staticmethod
    def verify_jwt_token(token: str, secret_key: str, algorithms: List[str] = None) -> Optional[dict]:
        """Verify and decode a JWT token."""
        if algorithms is None:
            algorithms = ["HS256"]
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=algorithms)
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a Fernet encryption key."""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def encrypt_data(data: str, key: str) -> str:
        """Encrypt data using Fernet."""
        f = Fernet(key.encode())
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str, key: str) -> str:
        """Decrypt data using Fernet."""
        f = Fernet(key.encode())
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(decoded_data)
        return decrypted_data.decode()
    
    @staticmethod
    def generate_rsa_key_pair() -> Tuple[str, str]:
        """Generate RSA key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        public_key = private_key.public_key()
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    @staticmethod
    def encrypt_with_rsa(data: str, public_key_pem: str) -> str:
        """Encrypt data using RSA public key."""
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        
        encrypted_data = public_key.encrypt(
            data.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted_data).decode()
    
    @staticmethod
    def decrypt_with_rsa(encrypted_data: str, private_key_pem: str) -> str:
        """Decrypt data using RSA private key."""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = private_key.decrypt(
            decoded_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted_data.decode()
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return f"ae_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format."""
        pattern = r"^ae_[A-Za-z0-9_-]{43}$"
        return bool(re.match(pattern, api_key))
    
    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        # Remove null bytes
        sanitized = input_string.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\t')
        
        # Limit length
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))
    
    @staticmethod
    def calculate_password_entropy(password: str) -> float:
        """Calculate password entropy (bits of randomness)."""
        # Count unique character sets used
        char_sets = 0
        if re.search(r"[a-z]", password):
            char_sets += 26
        if re.search(r"[A-Z]", password):
            char_sets += 26
        if re.search(r"\d", password):
            char_sets += 10
        if re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
            char_sets += 32
        
        # Calculate entropy
        entropy = len(password) * (char_sets ** 0.5)
        return entropy
    
    @staticmethod
    def get_password_strength(password: str) -> str:
        """Get password strength rating."""
        entropy = SecurityUtils.calculate_password_entropy(password)
        
        if entropy < 30:
            return "weak"
        elif entropy < 50:
            return "medium"
        elif entropy < 70:
            return "strong"
        else:
            return "very_strong"
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a one-time password."""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def hash_file(file_path: str, algorithm: str = "sha256") -> str:
        """Calculate hash of a file."""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def verify_file_hash(file_path: str, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify file hash against expected value."""
        actual_hash = SecurityUtils.hash_file(file_path, algorithm)
        return secrets.compare_digest(actual_hash, expected_hash)


# Import base64 at module level
import base64 