import os
import sys
from pathlib import Path

# Füge den Projektpfad zum Python-Pfad hinzu
project_home = str(Path(__file__).parent.parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Setze die Umgebungsvariablen
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'

# Importiere und erstelle die Flask-App
from app import create_app
from app.config.version import get_version
app = create_app()
# Starte mit Versions-Log
try:
    app.logger.info(f"Scandy Version {get_version()} gestartet (WSGI)")
except Exception:
    pass

# Gunicorn erwartet eine 'application' Variable
application = app

if __name__ == '__main__':
    # Für Entwicklung: Flask-Entwicklungsserver
    # Für Produktion: Verwende Gunicorn oder Waitress
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--dev':
        # Entwicklungsserver
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        # Produktionsserver (Waitress als Fallback)
        try:
            from waitress import serve
            print("Starting with Waitress production server...")
            serve(app, host='0.0.0.0', port=5000, threads=4)
        except ImportError:
            print("Waitress not available, falling back to Flask development server...")
            app.run(host='0.0.0.0', port=5000, debug=False) 