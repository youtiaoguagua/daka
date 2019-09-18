from django.contrib import admin
from . import models
from django.contrib.auth.admin import UserAdmin


@admin.register(models.Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_name', 'room_introduction']


@admin.register(models.DetailUser)
class DetailUserAdmin(admin.ModelAdmin):
    list_display = ['user_username','userinfo',]

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'OpenId'


@admin.register(models.Reserver)
class ReserverAdmin(admin.ModelAdmin):
    list_display = ['name','date','start_time', 'end_time','room']
    list_filter = ('room',)

# @admin.register(models.AboutCollege)
# class AboutCollegeAdmin(admin.ModelAdmin):
#     list_display = ['name']
#
#     def has_add_permission(self, request):
#         num_objects = self.model.objects.count()
#         if num_objects >= 1:
#             return False
#         else:
#             return True

@admin.register(models.SettingModel)
class SettingModelAdmin(admin.ModelAdmin):
    list_display = ['college_name']

    def has_add_permission(self, request):
        num_objects = self.model.objects.count()
        if num_objects >= 1:
            return False
        else:
            return True


admin.site.site_header = '书院预约'
admin.site.site_title = '书院预约'