from .models import RequestsModel
from datetime import datetime
from django_redis import get_redis_connection
import json
from datetime import datetime,date

class CustomerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.re = get_redis_connection("redis")

    def __call__(self, request):
        try:
            if(request.META['REQUEST_METHOD'] in ['DELETE','GET',"POST"]):
                data = {
                    'method':request.META['REQUEST_METHOD'],
                    'ip':request.META['REMOTE_ADDR'],
                    'datetime':datetime.now(),
                    'date':date.today(),
                }
                try:
                    self.re.ping()
                    self.re.lpush('request',json.dumps(data,default=str))
                    # self.re.hset('request',datetime.now().timestamp(),json.dumps(data,default=str))
                except:
                    pass
        except BaseException as e:
            raise e
        response = self.get_response(request)
        return response