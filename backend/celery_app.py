# backend/celery_app.py
import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('CELERY_CONFIG_MODULE', 'backend.celery_config')

# Create the Celery app instance
celery_app = Celery('chama_wallet')

# Load configuration from celery_config.py
celery_app.config_from_object('backend.celery_config')

# Auto-discover tasks from all registered Django app configs.
celery_app.autodiscover_tasks(['backend.tasks'])

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
celery_app.set_default()
