"""
Template for the PythonAnywhere WSGI configuration file.

This file is NOT used by the app directly. PythonAnywhere serves the web app
through a file it owns at:

    /var/www/YOURUSER_pythonanywhere_com_wsgi.py

Open that file in the PythonAnywhere editor (Web tab -> "WSGI configuration
file"), delete everything in it, and paste the contents below with YOURUSER
replaced. It is kept in the repo so the deployed configuration is reviewable
rather than living only in a web form.

Note there is no environment-variable juggling here: settings.py reads
`BASE_DIR/.env`, so the deployed configuration lives in
/home/YOURUSER/Jory/backend/.env — which is gitignored and therefore survives
every `git pull`.
"""

import os
import sys

# The directory containing manage.py, so `Jory.settings` and `apps.*` import.
path = "/home/YOURUSER/Jory/backend"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "Jory.settings"

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
