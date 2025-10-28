#!/usr/bin/env python3
"""
Generate RSA key pair for JWT signing
Run this once to generate JWT_PRIVATE_KEY_PEM and JWT_PUBLIC_KEY_PEM
"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_rsa_keypair():
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode(), public_pem.decode()


if __name__ == "__main__":
    private_key, public_key = generate_rsa_keypair()
    
    print("=== PRIVATE KEY (JWT_PRIVATE_KEY_PEM) ===")
    print(private_key)
    print("\n=== PUBLIC KEY (JWT_PUBLIC_KEY_PEM) ===")
    print(public_key)
    print("\n⚠️  Save these keys securely in your .env file!")
    print("Keep the private key secret!")
