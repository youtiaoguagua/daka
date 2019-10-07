from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from annoying.fields import AutoOneToOneField, JSONField
from ckeditor.fields import RichTextField

class DetailUser(models.Model):
    user = AutoOneToOneField(User,primary_key=True,on_delete=models.CASCADE,related_name ="detailuser")
    userinfo = models.CharField(max_length=1000,blank=True, null=True)
    token = models.CharField(max_length=255,blank=True, null=True)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'


class Room(models.Model):
    room_name = models.CharField(max_length=255, verbose_name='房间名字')
    room_introduction = models.CharField(max_length=255, verbose_name="房间介绍（粗略）")
    room_count = models.CharField(max_length=255, verbose_name="房间可容纳人数")
    room_use = models.CharField(max_length=255, verbose_name="房间用途")
    room_image = models.URLField(max_length=255, verbose_name="房间图片")

    def __str__(self):
        return self.room_name

    class Meta:
        verbose_name = '房间'
        verbose_name_plural = '房间'



class Reserver(models.Model):
    GENDER_CHOICES = (
        ('phone', '手机'),
        ('wx', '微信'),
        ('qq', 'QQ'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='预约的用户')
    room= models.ForeignKey(Room,related_name='roomDetail', on_delete=models.CASCADE, verbose_name="预约的房间")
    start_time = models.TimeField(verbose_name="预约的开始时间")
    end_time = models.TimeField(verbose_name="预约的结束时间")
    date = models.DateField(verbose_name="预约日期")
    name = models.CharField(max_length=255,verbose_name='活动名称')
    belong = models.CharField(max_length=255, blank=True, null=True, verbose_name='活动所属组织或个人')
    event_intro = models.CharField(max_length=500, blank=True, null=True, verbose_name='活动描述')
    contact_method = models.CharField(choices=GENDER_CHOICES, max_length=255, verbose_name="用什么联系")
    contact_info = models.CharField(max_length=255, verbose_name="联系方式")
    datecreat = models.DateTimeField(auto_now=True,verbose_name="创建时间")
    is_activate = models.BooleanField(default=False, verbose_name="预约是否有效")
    formid = models.CharField(max_length=255,null=True,blank=True,verbose_name="表单ID")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-datecreat']
        verbose_name = '预约'
        verbose_name_plural = '预约'


class SettingModel(models.Model):
    college_name = models.CharField(max_length=255,verbose_name="书院名字",blank=True,null=True)
    content = RichTextField(verbose_name="书院介绍",blank=True,null=True)

    def __str__(self):
        return self.college_name

    class Meta:
        verbose_name = '书院'
        verbose_name_plural = '书院'

class WxInfo(models.Model):
    accesstoken = models.CharField(max_length=500,verbose_name="企业微信私匙")



