"""Self-signed HTTPS certificate.

Phone browsers only give a page microphone access over HTTPS, so the server always runs with TLS.
The certificate is regenerated when the PC's LAN address changes (a different Wi-Fi, a new DHCP lease).
"""

import datetime
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _cert_covers(cert_path: Path, ips: list[str]) -> bool:
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    except (OSError, ValueError):
        return False
    if cert.not_valid_after_utc < datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7):
        return False
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False
    covered = {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
    return set(ips) <= covered


def ensure_cert(cert_dir: Path, ips: list[str]) -> tuple[Path, Path]:
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"
    if key_path.exists() and _cert_covers(cert_path, ips):
        return cert_path, key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "O.R.A.C.L.E.")])
    now = datetime.datetime.now(datetime.timezone.utc)
    san = [x509.DNSName("localhost")] + [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path
