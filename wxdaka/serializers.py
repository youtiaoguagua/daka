from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (DetailUser, Room, Reserver)
import json


class LoginValidSerializers(serializers.Serializer):
    code = serializers.CharField(required=True)
    userinfo = serializers.JSONField(required=True)
    # class Meta:
    #     fields = "__all__"


class LoginInfoSerializers(serializers.ModelSerializer):
    userinfo = serializers.JSONField(source='detailuser.userinfo', required=True)
    token = serializers.CharField(source='detailuser.token', required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'userinfo', 'token']

    def create(self, validated_data):
        userdata = validated_data.pop('detailuser')
        user = self.Meta.model.objects.create_user(**validated_data)
        user.detailuser.userinfo = userdata['userinfo']
        user.detailuser.token = userdata['token']
        user.detailuser.save()
        return user


from datetime import datetime


class AllRoomSerializer(serializers.ModelSerializer):
    whether_used = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = '__all__'

    def get_whether_used(self, obj):
        queryset = Reserver.objects.filter(room=obj, date=datetime.now().date(), start_time__lte=datetime.now().time(),
                                           end_time__gte=datetime.now().time())
        if queryset.exists():
            return True
        else:
            return False


class ReserverSerializer(serializers.ModelSerializer):
    roomData = serializers.SerializerMethodField(read_only=True)
    userinfo = serializers.SerializerMethodField(read_only=True)
    start_time = serializers.TimeField(format="%H:%M",required=True)
    end_time = serializers.TimeField(format="%H:%M", required=True)
    user = serializers.IntegerField(source='user.id', required=False)

    class Meta:
        model = Reserver
        fields = "__all__"

    def get_roomData(self, obj):
        return AllRoomSerializer(obj.room).data

    def get_userinfo(self, obj):
        try:
            return json.loads(obj.user.detailuser.userinfo)
        except:
            return None
