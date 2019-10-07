import json
from datetime import date as todaydate
from datetime import datetime

import markdown
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import generics
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_extensions.cache.decorators import (
    cache_response
)
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from wechatpy.enterprise import parse_message
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.exceptions import InvalidSignatureException

from .authenticate import AuthenticationCustomer
from .models import (Room, Reserver, SettingModel, )
from .permission import IsOwnerOrReadOnly
from .serializers import (LoginValidSerializers, LoginInfoSerializers, AllRoomSerializer, ReserverSerializer, )
from .tasks import SendReserverTask, SendTemplateMessage
from .utils.timeMap import timemap


class Login(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = LoginValidSerializers

    def create(self, request, *args, **kwargs):
        serializerPost = self.get_serializer(data=request.data)
        serializerPost.is_valid(raise_exception=True)
        payload = {
            'appid': settings.WXAPPID,
            'secret': settings.WXSECRET,
            'js_code': serializerPost.data['code'],
            'grant_type': 'authorization_code',
        }

        jscode2session = requests.get('https://api.weixin.qq.com/sns/jscode2session', params=payload).json()
        if jscode2session.get('errcode',None) != None:
            return Response({'status':"fail"}, status.HTTP_400_BAD_REQUEST)
        openid = jscode2session['openid']
        session_key = jscode2session['session_key']

        authuser = self.queryset.filter(username=openid).first()
        if authuser:
            authuser.detailuser.token = session_key
            authuser.detailuser.save()
            return Response({'token':session_key}, status=status.HTTP_200_OK)


        data = {
            "username":openid,
            "password":"wxuser",
            "userinfo":json.dumps(serializerPost.data['userinfo']),
            "token" : session_key
        }
        print(data)
        serializer = LoginInfoSerializers(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({'token':session_key}, status=status.HTTP_200_OK)

class GetAllRoom(CacheResponseMixin,generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = AllRoomSerializer



class ReserverRoomView(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication,AuthenticationCustomer]
    permission_classes = [IsAuthenticated]
    queryset = Reserver.objects.all()
    serializer_class = ReserverSerializer

    def is_valid_time(self,serializer):
        serdata = serializer.validated_data
        if serdata['start_time'].strftime("%H:%M") not in timemap or serdata['end_time'].strftime("%H:%M") not in timemap:
            return False
        if serdata['start_time'] >= serdata['end_time']:
            return False
        query_set = self.get_queryset().filter(date = serdata['date'],room=serdata['room'])
        query_set_detail = query_set.filter(~Q(start_time=serdata['start_time'],end_time=serdata['end_time']),Q(start_time__gte=serdata['end_time'],end_time__gt=serdata['end_time']) | Q(end_time__lte=serdata['start_time'],start_time__lte=serdata['start_time']))
        if query_set.count()== query_set_detail.count():
            return True
        else:
            return False

    def create(self, request, *args, **kwargs):
        # 设置最多预定的个数
        if self.queryset.filter(date__gte=todaydate.today(),user=request.user).count() >= 7:
            return Response({'status':8,'error':"to many reserver"},status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        timeValid = self.is_valid_time(serializer)
        if timeValid == False:
            return Response({'status':'时间错误'},status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # try:
        #     SendReserverTask.delay(serializer.data)
        # except BaseException as e:
        #     raise e
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        if kwargs =={}:
            queryset = self.filter_queryset(self.get_queryset().filter(user = request.user,date__gte=todaydate.today()))
        else:
            try:
                date = datetime.strptime(kwargs['date'],'%Y-%m-%d')
            except BaseException as e:
                print(e)
                return Response({"status":'参数错误'})
            queryset_filter = self.get_queryset().filter(date = date, room = kwargs['room'] )
            queryset = self.filter_queryset(queryset_filter)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DeleteReserverView(generics.DestroyAPIView):
    authentication_classes = [SessionAuthentication,AuthenticationCustomer]
    permission_classes = [IsOwnerOrReadOnly]
    queryset = Reserver.objects.all()
    serializer_class = ReserverSerializer

    # def perform_destroy(self, instance):
    #     pass
    #     # instance.delete()

class getCollegeName(APIView):

    @cache_response(timeout=60 * 60, cache='default')
    def get(self,request):
        setting = SettingModel.objects.first()
        about = markdown.markdown(setting.content, extensions=['markdown.extensions.nl2br', 'extra'])
        if setting:
            return Response({'college_name':setting.college_name,'about':about},status=status.HTTP_200_OK)
        else:
            return Response({'college_name':"书院","about":None},status=status.HTTP_200_OK)


class CheckLogin(APIView):
    authentication_classes = [AuthenticationCustomer]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        return Response({'status':'success'},status=status.HTTP_200_OK)



class WxEnterprise(APIView):

    def get(self,request):
        signature = self.request.query_params.get('msg_signature')
        timestamp = self.request.query_params.get('timestamp')
        nonce = self.request.query_params.get('nonce')
        echo_str = self.request.query_params.get('echostr')
        CorpId = settings.CORPID
        TOKEN = settings.WXTOKEN
        EncodingAESKey = settings.WXENCODINGAESKEY
        crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
        try:
            echo_str = crypto.check_signature(
                signature,
                timestamp,
                nonce,
                echo_str
            )
        except InvalidSignatureException:
            raise  # 处理异常情况
        return HttpResponse(echo_str)

    def post(self,request):
        raw_message = request.body
        signature = self.request.query_params.get('msg_signature')
        timestamp = self.request.query_params.get('timestamp')
        nonce = self.request.query_params.get('nonce')
        CorpId = settings.CORPID
        TOKEN = settings.WXTOKEN
        EncodingAESKey = settings.WXENCODINGAESKEY

        crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
        try:
            decrypted_xml = crypto.decrypt_message(
                raw_message,
                signature,
                timestamp,
                nonce
            )
        except (InvalidSignatureException, InvalidCorpIdException):
            raise  # 处理异常情况
        else:
            msg = parse_message(decrypted_xml)
            msg_data = msg._data
            if msg_data['Event'] == 'taskcard_click':
                splitMap = msg_data['EventKey'].split('-')
                reserver = Reserver.objects.get(id=splitMap[1])
                userInfo = {
                    "formid": reserver.formid,
                    "openid": reserver.user.username,
                    "event_name": reserver.name,
                    "event_date": "{date} {start_time}-{end_time}".format(date=reserver.date.strftime("%m月%d日"),
                                                                          start_time=reserver.start_time.strftime(
                                                                              "%H:%S"),
                                                                          end_time=reserver.end_time.strftime("%H:%S")),
                    "event_room": reserver.room.room_name,
                }
                if splitMap[0] == 'accept':
                    reserver.is_activate=True
                    reserver.save()
                    userInfo['event_status'] = "通过"
                    SendTemplateMessage.delay(userInfo)
                else:
                   reserver.delete()
                   userInfo['event_status'] = "未通过"
                   SendTemplateMessage.delay(userInfo)
        return HttpResponse(None)




