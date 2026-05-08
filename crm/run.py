"""crm.run — entry point. Lance le serveur Flask local.

Usage :
    python -X utf8 -m crm.run
"""
import argparse
from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="Mad Makers CRM — local server")
    parser.add_argument("--host", default="127.0.0.1", help="Host bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--debug", action="store_true", default=True, help="Debug mode (auto-reload)")
    args = parser.parse_args()

    print(f"\n  Mad Makers CRM — http://{args.host}:{args.port}\n")
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
