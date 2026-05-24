import os
import logging

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

if os.getenv("RUN_MIGRATIONS_ON_STARTUP", "1") == "1":
    logger = logging.getLogger(__name__)
    try:
        call_command("migrate", interactive=False, verbosity=1)
    except Exception:
        logger.exception("Failed to run startup migrations")
        raise
