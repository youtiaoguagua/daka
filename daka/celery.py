from __future__ import absolute_import, unicode_literals

import os

from celery import Celery, platforms

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daka.settings')

app = Celery('daka')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(
    enable_utc=True,
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# platforms.C_FORCE_ROOT = True

