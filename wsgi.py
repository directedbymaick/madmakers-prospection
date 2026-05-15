"""WSGI entry point pour gunicorn (déploiement Render).

Usage local (équivalent au dev server) :
    gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app

Usage prod (Render auto) :
    gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app
"""
from crm.app import create_app

app = create_app()

if __name__ == "__main__":
    # Permet de lancer python wsgi.py pour test sans gunicorn
    app.run(host="0.0.0.0", port=8000)
