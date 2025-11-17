# backend/celery_config.py
import os

# Broker settings
broker_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
result_backend = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Task default settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Task routing
task_routes = {
    'backend.tasks.notifications.*': {'queue': 'notifications'},
    'backend.tasks.analytics.*': {'queue': 'analytics'},
    'backend.tasks.processing.*': {'queue': 'processing'},
}

# Worker settings
worker_prefetch_multiplier = 1
worker_disable_rate_limits = False
worker_send_task_events = True

# Result settings
result_expires = 3600  # 1 hour

# Beat scheduler settings (for future scheduled tasks)
beat_scheduler = 'celery.beat.PersistentScheduler'
beat_schedule_filename = '/tmp/celerybeat-schedule'
