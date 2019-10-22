from rest_framework import serializers
from django.contrib.auth.models import User
import json
from wxdaka.models import Reserver, Room, SettingModel
from wxdaka.serializers import AllRoomSerializer
from .models import RequestsModel




class Login(serializers.ModelSerializer):
    username = serializers.CharField()

    class Meta:
        model = User
        fields = ['username', 'password']

class ReserverSerializer(serializers.ModelSerializer):
    roomData = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Reserver
        fields = "__all__"

    def get_roomData(self, obj):
        return AllRoomSerializer(obj.room).data

class ReviewSerializer(serializers.Serializer):
    idlist = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    type = serializers.ChoiceField(required=True,choices=['allow','reject','delete'])

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class CollegeSerializer(serializers.ModelSerializer):

    class Meta:
        model = SettingModel
        fields = "__all__"



class RequestDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = RequestsModel
        fields = "__all__"
