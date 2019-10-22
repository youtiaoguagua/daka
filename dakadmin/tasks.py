from daka.celery import app as celery_app
from celery import shared_task
from django_redis import get_redis_connection
from .models import RequestsModel
import json
from celery.schedules import crontab

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(minute='*/30'), cleanCache.s())

@celery_app.task
def cleanCache():
    re = get_redis_connection("redis")
    try:
        re.ping()
        def list_iter(name):
            list_count = re.llen(name)
            for index in range(list_count):
                yield re.lpop(name)
        reqList = [RequestsModel(**json.loads(x)) for x in list_iter('request')]
        RequestsModel.objects.bulk_create(reqList)
    except:
        pass

