from django.db import models

# Create your models here.

class RequestsModel(models.Model):
    method = models.CharField(max_length=20,blank=True,null=True,verbose_name="请求方法")
    ip  = models.GenericIPAddressField(blank=True,null=True,verbose_name="请求地址")
    datetime = models.DateTimeField(auto_now_add=True)
    date = models.DateField(auto_now_add=True)