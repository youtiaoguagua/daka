from .models import RequestsModel
from datetime import datetime

class CustomerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
         # 配置和初始化

    def __call__(self, request):
        try:
            if(request.META['REQUEST_METHOD'] in ['DELETE','GET',"POST"]):
                data = {
                    'method':request.META['REQUEST_METHOD'],
                    'ip':request.META['REMOTE_ADDR'],
                }
                RequestsModel.objects.create(**data)
        except BaseException as e:
            raise e
        response = self.get_response(request)
        return response