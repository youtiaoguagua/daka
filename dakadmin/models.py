from django.db import models

# Create your models here.

class RequestsModel(models.Model):
    method = models.CharField(max_length=20,blank=True,null=True,verbose_name="请求方法")
    ip  = models.GenericIPAddressField(blank=True,null=True,verbose_name="请求地址")
    datetime = models.DateTimeField()
    date = models.DateField()

    class Meta:
        ordering = ['-datetime']
        verbose_name = '请求统计'
        verbose_name_plural = '请求统计'