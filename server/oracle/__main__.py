import uvicorn

from .app import create_app
from .certs import ensure_cert
from .config import load_settings
from .netinfo import lan_ip
from .session import SessionManager


def main() -> None:
    settings = load_settings()
    ip = lan_ip()
    cert, key = ensure_cert(settings.cert_dir, sorted({ip, "127.0.0.1"}))
    join_url = f"https://{ip}:{settings.port}/join"

    manager = SessionManager(settings.data_dir)
    app = create_app(settings, manager, join_url=join_url)

    print()
    print("  O.R.A.C.L.E. is running")
    print(f"  Dashboard (this PC):  https://localhost:{settings.port}/dm")
    print(f"  Players (phones):     {join_url}")
    print("  Your browser warns about the certificate the first time: choose Advanced -> Proceed.")
    print()
    uvicorn.run(app, host=settings.host, port=settings.port, ssl_certfile=str(cert), ssl_keyfile=str(key), log_level="warning")


if __name__ == "__main__":
    main()
