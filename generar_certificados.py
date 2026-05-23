

"""
Script para generar certificados SSL autofirmados para HTTPS usando la librería nativa cryptography.
Este script no depende del ejecutable de OpenSSL del sistema.
"""

import os
import sys
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def generar_certificados():

    app_dir = os.path.join(os.path.dirname(__file__), 'inventario')
    cert_file = os.path.join(app_dir, 'cert.pem')
    key_file = os.path.join(app_dir, 'key.pem')
    
    print("=" * 70)
    print("🔐 GENERADOR DE CERTIFICADOS SSL (INVENTARIO AUTO SOLUTION)")
    print("=" * 70)
    

    if not os.path.exists(app_dir):
        os.makedirs(app_dir)


    if os.path.exists(cert_file) and os.path.exists(key_file):
        respuesta = input(f"\n⚠️  Ya existen certificados en:\n  {cert_file}\n  {key_file}\n\n¿Deseas regenerarlos? (s/n): ").strip().lower()
        if respuesta != 's':
            print("\n[INFO] Se mantienen los certificados existentes.")
            return True
        

        try:
            if os.path.exists(cert_file + ".bak"):
                os.remove(cert_file + ".bak")
            if os.path.exists(key_file + ".bak"):
                os.remove(key_file + ".bak")
            os.rename(cert_file, cert_file + ".bak")
            os.rename(key_file, key_file + ".bak")
            print("\n[OK] Certificados anteriores respaldados (.bak)")
        except Exception as e:
            print(f"\n[⚠️] No se pudo hacer copia de seguridad: {e}")
            
    try:
        print("\n⏳ Generando clave privada RSA de 2048 bits...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        print("⏳ Generando certificado X.509 autofirmado...")
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"CL"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Region"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Santiago"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Inventario Auto Solution"),
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
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.DNSName(u"*.localhost"),
                x509.DNSName(u"127.0.0.1"),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        

        print(f"⏳ Guardando clave privada en: {key_file}")
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            

        print(f"⏳ Guardando certificado en: {cert_file}")
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        print("\n" + "=" * 70)
        print("✅ CERTIFICADOS GENERADOS EXITOSAMENTE!")
        print("=" * 70)
        print(f"📄 Certificado (cert.pem): {cert_file}")
        print(f"🔑 Clave privada (key.pem):  {key_file}")
        print("\n✓ Los certificados serán usados automáticamente al ejecutar la aplicación")
        print("=" * 70 + "\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al generar certificados: {e}")
        return False

if __name__ == '__main__':
    exito = generar_certificados()
    sys.exit(0 if exito else 1)
