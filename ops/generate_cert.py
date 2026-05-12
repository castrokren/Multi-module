#!/usr/bin/env python3
"""
Generate self-signed HTTPS certificate for dashboard
"""

from pathlib import Path
import subprocess
import sys

def generate_cert():
    """Generate self-signed certificate using openssl"""
    cert_file = Path(__file__).parent / "cert.pem"
    key_file = Path(__file__).parent / "key.pem"

    if cert_file.exists() and key_file.exists():
        print("Certificate already exists")
        return True

    try:
        # Try to use openssl if available
        result = subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_file), "-out", str(cert_file),
            "-days", "365", "-nodes",
            "-subj", "/C=US/ST=State/L=City/O=Org/CN=localhost"
        ], capture_output=True)

        if result.returncode == 0:
            print("Certificate generated successfully")
            return True
        else:
            print("OpenSSL failed, trying Python fallback...")
            return generate_cert_python()
    except FileNotFoundError:
        print("OpenSSL not found, trying Python fallback...")
        return generate_cert_python()

def generate_cert_python():
    """Generate certificate using Python's cryptography library"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from datetime import datetime, timedelta

        cert_file = Path(__file__).parent / "cert.pem"
        key_file = Path(__file__).parent / "key.pem"

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"City"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Org"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).sign(private_key, hashes.SHA256())

        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write private key
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        print("Certificate generated successfully")
        return True
    except Exception as e:
        print(f"Failed to generate certificate: {e}")
        return False

if __name__ == "__main__":
    if generate_cert():
        sys.exit(0)
    else:
        sys.exit(1)
