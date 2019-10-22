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
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework_extensions.cache.decorators import (
    cache_response
)
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from wechatpy.enterprise import parse_message
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.exceptions import InvalidSignatureException

from .authenticate import AuthenticationCustomer
from .models import (Room, Reserver, SettingModel, WxAriticle, Notice, College,SignUp)
from .permission import IsOwnerOrReadOnly
from .serializers import (LoginValidSerializers, LoginInfoSerializers, AllRoomSerializer, ReserverSerializer,
                          WxAriticleSerializer, CollegeListSerializer,HandelSignUpDateSerializer,
                          HanderSignUpActivateSerializer)
from .tasks import SendReserverTask, SendTemplateMessage,get_access_token
from .utils.timeMap import timemap
from collections import OrderedDict
from rest_framework.pagination import PageNumberPagination
import hashlib
from django.core.files.base import ContentFile
import traceback
import qrcode
from io import BytesIO
from .utils.crypto import Crypt

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'


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
        if jscode2session.get('errcode', None) != None:
            return Response({'status': "fail"}, status.HTTP_400_BAD_REQUEST)
        openid = jscode2session['openid']
        session_key = jscode2session['session_key']

        authuser = self.queryset.filter(username=openid).first()
        if authuser:
            authuser.detailuser.token = session_key
            authuser.detailuser.save()
            return Response({'token': session_key}, status=status.HTTP_200_OK)

        data = {
            "username": openid,
            "password": "wxuser",
            "userinfo": json.dumps(serializerPost.data['userinfo']),
            "token": session_key
        }
        print(data)
        serializer = LoginInfoSerializers(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({'token': session_key}, status=status.HTTP_200_OK)


class GetAllRoom(CacheResponseMixin, generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = AllRoomSerializer


class ReserverRoomView(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication, AuthenticationCustomer]
    permission_classes = [IsAuthenticated]
    queryset = Reserver.objects.all()
    serializer_class = ReserverSerializer

    def is_valid_time(self, serializer):
        serdata = serializer.validated_data
        if serdata['start_time'].strftime("%H:%M") not in timemap or serdata['end_time'].strftime(
                "%H:%M") not in timemap:
            return False
        if serdata['start_time'] >= serdata['end_time']:
            return False
        query_set = self.get_queryset().filter(date=serdata['date'], room=serdata['room'])
        query_set_detail = query_set.filter(~Q(start_time=serdata['start_time'], end_time=serdata['end_time']),
                                            Q(start_time__gte=serdata['end_time'],
                                              end_time__gt=serdata['end_time']) | Q(end_time__lte=serdata['start_time'],
                                                                                    start_time__lte=serdata[
                                                                                        'start_time']))
        if query_set.count() == query_set_detail.count():
            return True
        else:
            return False

    def create(self, request, *args, **kwargs):
        # 设置最多预定的个数
        if self.queryset.filter(date__gte=todaydate.today(), user=request.user).count() >= 7:
            return Response({'status': 8, 'error': "to many reserver"}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        timeValid = self.is_valid_time(serializer)
        if timeValid == False:
            return Response({'status': '时间错误'}, status=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        try:
            SendReserverTask.delay(serializer.data)
        except BaseException as e:
            raise e
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        if kwargs == {}:
            queryset = self.filter_queryset(self.get_queryset().filter(user=request.user, date__gte=todaydate.today()))
        else:
            try:
                date = datetime.strptime(kwargs['date'], '%Y-%m-%d')
            except BaseException as e:
                print(e)
                return Response({"status": '参数错误'})
            queryset_filter = self.get_queryset().filter(date=date, room=kwargs['room'])
            queryset = self.filter_queryset(queryset_filter)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReserverWxCode(APIView):
    authentication_classes = [SessionAuthentication, AuthenticationCustomer]
    permission_classes = [IsAuthenticated]

    def get(self,request,pk,format=None):
        try:
            reserverObj = Reserver.objects.get(id=pk)
            otherData = {
                "event_name":reserverObj.name,
                "event_room":"{} {}".format(reserverObj.room.college_id.college_name,reserverObj.room.room_name),
                "event_time":"{} {}".format(reserverObj.date.strftime("%Y/%m/%d"),reserverObj.start_time.strftime("%H:%M")),
                "event_content":reserverObj.event_intro
            }
            if reserverObj.WxCodeImage:
                imageUrl = "{}://{}/media/{}".format(self.request.scheme, self.request.META['HTTP_HOST'],
                                                     reserverObj.WxCodeImage)
                otherData['wxcode'] = imageUrl
                otherData['code'] = 0
                return Response(otherData,status=status.HTTP_200_OK)
            accestoken = get_access_token()
            data = {
                'scene': pk
            }
            image = requests.post(
                "https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={}".format(accestoken),
                data=json.dumps(data))
            if image.headers['Content-Type'] == "image/jpeg":
                fmd5 = hashlib.md5(image.content)
                resName = fmd5.hexdigest()
                reserverObj.WxCodeImage.save(
                    resName + '.jpg',
                    ContentFile(image.content)
                )
                imageUrl = "{}://{}/media/{}".format(self.request.scheme, self.request.META['HTTP_HOST'],
                                                     reserverObj.WxCodeImage)
                otherData['wxcode'] = imageUrl
                otherData['code'] = 0
                return Response(otherData,status=status.HTTP_200_OK)
            else:
                return Response({'wxcode': None,"code":1}, status=status.HTTP_200_OK)
        except BaseException as e:
            print(traceback.print_exc())
            return Response({'wxcode':None,"code":1},status=status.HTTP_200_OK)


class HandelSignUpDateSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet
                          ):
    authentication_classes = [AuthenticationCustomer]
    permission_classes = [IsAuthenticated]
    serializer_class = HandelSignUpDateSerializer
    queryset = SignUp.objects.all()

    @action(detail=False, methods=['post'], permission_classes=[])
    def signupactivate(self, request):
        serializer_data = HanderSignUpActivateSerializer(data=request.data)
        serializer_data.is_valid(raise_exception=True)
        code = serializer_data.validated_data["code"]
        id = Crypt().decrypt(code)
        res = SignUp.objects.filter(id=id).update(is_activate=True)
        if res ==0:
            data = {
                "code":1,
                "detail":"没有此数据"
            }
            return Response(data,status=status.HTTP_200_OK)
        else:
            data = {
                "code":0,
                "detail":'success'
            }
            return Response(data,status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[])
    def qrcode(self, request, pk=None):
        CryptData = Crypt().encrypt(pk)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(CryptData)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        output_buffer = BytesIO()
        img.save(output_buffer)
        image_stream = output_buffer.getvalue()
        return HttpResponse(image_stream,content_type="image/jpg")


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



class DeleteReserverView(generics.DestroyAPIView):
    authentication_classes = [SessionAuthentication, AuthenticationCustomer]
    permission_classes = [IsOwnerOrReadOnly]
    queryset = Reserver.objects.all()
    serializer_class = ReserverSerializer

    # def perform_destroy(self, instance):
    #     pass
    #     # instance.delete()


class getCollegeName(APIView):

    @cache_response(timeout=60 * 60, cache='default')
    def get(self, request):
        setting = SettingModel.objects.first()
        about = markdown.markdown(setting.content, extensions=['markdown.extensions.nl2br', 'extra'])
        if setting:
            return Response({'college_name': setting.college_name, 'about': about}, status=status.HTTP_200_OK)
        else:
            return Response({'college_name': "书院", "about": None}, status=status.HTTP_200_OK)


class CheckLogin(APIView):
    authentication_classes = [AuthenticationCustomer]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'status': 'success'}, status=status.HTTP_200_OK)

from .tasks import SendTemplateMessage
class FeiShu(APIView):

    def post(self, request):
        print(request.data)
        methodMap = {'accept':'同意','reject':'拒绝'}
        resTmpData = request.data['action']['value']['data']
        reserverId = request.data['action']['value']['id']
        action = request.data['action']['value']['action']
        resData = json.loads(resTmpData)
        resData['elements'][1] = {
            "tag": "note",
            "elements": [{
                "tag": "lark_md",
                "content": "<at id={}></at> **{}**".format(request.data['open_id'],methodMap[action]),
            }]
        }
        try:
            reserver = Reserver.objects.get(id=reserverId)
            if action=="accept":
                reserver.is_activate = True
                reserver.save()
            userInfo = {
                "openid": reserver.user.username,
                "result":methodMap[action],
                "room":  reserver.room.college_id.college_name+' '+reserver.room.room_name,
                "startDate": "{date} {start_time}".format(date=reserver.date.strftime("%m月%d日"),
                                                                      start_time=reserver.start_time.strftime(
                                                                          "%H:%M")),
                "endDate": "{date} {end_time}".format(date=reserver.date.strftime("%m月%d日"),
                                                                      end_time=reserver.end_time.strftime(
                                                                          "%H:%M")),
                "person":reserver.belong
            }
            SendTemplateMessage.delay(userInfo)
        except:
            pass
        return Response(resData)


# class WxEnterprise(APIView):
#
#     def get(self, request):
#         signature = self.request.query_params.get('msg_signature')
#         timestamp = self.request.query_params.get('timestamp')
#         nonce = self.request.query_params.get('nonce')
#         echo_str = self.request.query_params.get('echostr')
#         CorpId = settings.CORPID
#         TOKEN = settings.WXTOKEN
#         EncodingAESKey = settings.WXENCODINGAESKEY
#         crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
#         try:
#             echo_str = crypto.check_signature(
#                 signature,
#                 timestamp,
#                 nonce,
#                 echo_str
#             )
#         except InvalidSignatureException:
#             raise  # 处理异常情况
#         return HttpResponse(echo_str)
#
#     def post(self, request):
#         raw_message = request.body
#         signature = self.request.query_params.get('msg_signature')
#         timestamp = self.request.query_params.get('timestamp')
#         nonce = self.request.query_params.get('nonce')
#         CorpId = settings.CORPID
#         TOKEN = settings.WXTOKEN
#         EncodingAESKey = settings.WXENCODINGAESKEY
#
#         crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
#         try:
#             decrypted_xml = crypto.decrypt_message(
#                 raw_message,
#                 signature,
#                 timestamp,
#                 nonce
#             )
#         except (InvalidSignatureException, InvalidCorpIdException):
#             raise  # 处理异常情况
#         else:
#             msg = parse_message(decrypted_xml)
#             msg_data = msg._data
#             if msg_data['Event'] == 'taskcard_click':
#                 splitMap = msg_data['EventKey'].split('-')
#                 reserver = Reserver.objects.get(id=splitMap[1])
#                 userInfo = {
#                     "openid": reserver.user.username,
#                     "event_name": reserver.name,
#                     "event_date": "{date} {start_time}-{end_time}".format(date=reserver.date.strftime("%m月%d日"),
#                                                                           start_time=reserver.start_time.strftime(
#                                                                               "%H:%S"),
#                                                                           end_time=reserver.end_time.strftime("%H:%S")),
#                     "event_room": reserver.room.room_name,
#                 }
#                 if splitMap[0] == 'accept':
#                     reserver.is_activate = True
#                     reserver.save()
#                     userInfo['event_status'] = "通过"
#                     SendTemplateMessage.delay(userInfo)
#                 else:
#                     reserver.delete()
#                     userInfo['event_status'] = "未通过"
#                     SendTemplateMessage.delay(userInfo)
#         return HttpResponse(None)


class getAriticleSet(CacheResponseMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []
    serializer_class = WxAriticleSerializer
    queryset = WxAriticle.objects.all()
    pagination_class = LargeResultsSetPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, exclude=('content', 'guid', 'date',))
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, exclude=('content', 'guid', 'date',))
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, fields=('id', 'content'))
        return Response(serializer.data)


class GetNotice(APIView):

    def get(self, request):
        res = Notice.objects.first()
        if res:
            data = {
                'date': res.date,
                'notice': res.notice
            }
        else:
            data = {
                'date': None,
                'notice': None
            }
        return Response(data, status=status.HTTP_200_OK)


class CollegeListView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet):
    authentication_classes = []
    permission_classes = []
    serializer_class = CollegeListSerializer
    queryset = College.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, exclude=['college_intro'])
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, exclude=['college_intro'])
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, exclude=['room'])
        return Response(serializer.data)


from rest_framework.parsers import MultiPartParser,FileUploadParser

from datetime import timedelta
class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)

    def post(self,request):
        file_obj = request.data["image"]
        # print(request.data)
        # from .serializers import TestImageSerializer
        # file_serializer = TestImageSerializer(data=request.data)
        # file_serializer.is_valid(raise_exception=True)
        # file_serializer.save()
        # data = file_serializer.data
        # return Response({})

    def test(self):
        print(self.request.META['HTTP_HOST'])

    def get(self, request, format=None):
        # print(type(request.data['laji']))
        # print(request.data)
        # SendReserverTask.delay('dsad')
        # tomorrow = datetime.utcnow() + timedelta(minutes=2)
        # testArgs.apply_async(eta=tomorrow ,expires=datetime.utcnow()+timedelta(minutes=1))
        from .models import TestImage
        import hashlib
        from io import BytesIO
        # from django.core.files import File
        from django.core.files.base import ContentFile
        from .serializers import TestImageSerializer
        # from django.core.files.uploadedfile import InMemoryUploadedFile

        from django.core.files import uploadedfile
        a = requests.get("https://ws1.sinaimg.cn/large/007icE8gly1g6z52pzft8j318x0gowqx.jpg")
        from io import StringIO
        from django.core.files import File
        # img_temp = StringIO()
        # inImage.save(img_temp, 'PNG')
        # img_temp.seek(0)
        fp = BytesIO()
        fp.write(a.content)
        fp.flush()
        c = File(fp,'dsadsad.jpg')
        d = ContentFile(a.content,"caonidasdma.jpg")
        data = {
            "image":d
        }
        print(data)
        file_serializer = TestImageSerializer(data=data)
        file_serializer.is_valid(raise_exception=True)
        print(file_serializer.data)
        return Response({})

        # data = {
        #     'scene': 'id=3'
        # }
        # accestoken = get_access_token()
        # print(accestoken)
        # imagefun = lambda : requests.post(
        #     "https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={}".format(accestoken),
        #     data=json.dumps(data),stream=True)
        # image = imagefun()
        # if image.headers['Content-Type']=="image/jpeg":
        #     pass
        # else:
        #     image = image.json()
        #     print(image)
        #     if image['errcode'] == 40001:
        #         print('jinru')
        #         accestoken = get_access_token(True)
        #         print(accestoken)
        #
        #         image = imagefun()
        #
        # return HttpResponse(image,content_type="image/png")

        # fmd5 = hashlib.md5(image.content)
        # resName = fmd5.hexdigest()
        # f = InMemoryUploadedFile(image.content, 'media_file', resName+'.jpg', 'image/jpg',
        #                          len(image.content), None)
        # fp = BytesIO()
        # fp.write(image.content)
        # print(f.__dict__)
        # request.data['image'] = "dsadsad"
        # resq = request.data.copy()
        # resq['image'] = f
        # print(request.data)
        # a = TestImage.objects.get(id=1)
        # print(a)
        # file_serializer = TestImageSerializer(data=resq)
        # file_serializer.is_valid(raise_exception=True)
        # data = file_serializer.data
        # a = request.build_absolute_uri(data['image'])
        # print(a)

        # if file_serializer.is_valid(raise_exception=True):
        #     file_serializer.save()
        #     return Response(file_serializer.data)
        # return Response({})

        # fmd5 = hashlib.md5(image.content)
        # resName = fmd5.hexdigest()
        # imageobj= TestImage()
        # imageobj.image.save(
        #     resName+".jpg",
        #     ContentFile(image.content)
        # )
        #
        # print(request.build_absolute_uri(str(imageobj.image)))
        # print(request.META['HTTP_HOST'])
        pass
        # return HttpResponse(image,content_type="image/png")