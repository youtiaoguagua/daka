from collections import OrderedDict
from datetime import date
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.utils.text import capfirst

from rest_framework import generics, mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from wxdaka.models import Reserver, Room, SettingModel
from wxdaka.serializers import ReserverSerializer as dakaReserverSerializer
from .serializers import Login
from .serializers import (ReserverSerializer, ReviewSerializer,
                          RoomSerializer, CollegeSerializer,
                          RequestDataSerializer, )
from .models import RequestsModel
from rest_framework_extensions.cache.mixins import CacheResponseMixin
from rest_framework_extensions.cache.decorators import cache_response
from Cache.cacheClass import UserKeyConstructor
from datetime import datetime, timedelta, date
from rest_framework_extensions.key_constructor.constructors import DefaultKeyConstructor, DefaultListKeyConstructor
from rest_framework_extensions.cache.mixins import CacheResponseMixin


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 3
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('num_pages', self.page.paginator.num_pages),
            ('results', data)
        ]))


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = Login(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.data)
        if user == None:
            data = {
                'status': 'no such user',
                'code': 1001,
            }
            return Response(data=data)
        else:
            if user.is_active and user.is_staff:
                user_logged_in.send(sender=user.__class__, request=request, user=user)
                refresh = RefreshToken.for_user(user)
                data = {
                    'status': 'success',
                    'code': 0,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'exp': refresh.access_token.payload['exp'],
                }
                return Response(data=data)
            else:
                data = {
                    'status': 'have no permission',
                    'code': 1001,
                }
                return Response(data=data)



class getGloabDataView(APIView):
    permission_classes = [IsAuthenticated]

    @cache_response(60*10,key_func=DefaultKeyConstructor())
    def get(self, request):
        todayReserver = Reserver.objects.filter(date__gte=date.today())
        toReview = todayReserver.filter(is_activate=False)
        allUser = User.objects.count()
        serializer_data = ReserverSerializer(toReview, many=True)
        data = {
            'gloabdata': {
                'toReview': toReview.count(),
                'todayReserver': todayReserver.count(),
                'allUser': allUser
            },
            'reserverData': serializer_data.data
        }
        return Response(data=data, status=status.HTTP_200_OK)


class ReviewReserverView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        type = request.data.get('type', None)
        idList = request.data.getlist('idlist', None)
        data = {
            'type': type,
            'idlist': idList
        }
        seriallizer_data = ReviewSerializer(data=data)
        seriallizer_valid = seriallizer_data.is_valid()
        print(seriallizer_data.data)
        if not seriallizer_valid:
            data = {
                'status': 'fail'
            }
            return Response(data=data, status=status.HTTP_200_OK)

        data = {
            'status': 'success'
        }
        return Response(data=data, status=status.HTTP_200_OK)





class RoomViewSet(CacheResponseMixin,
                  viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()
    pagination_class = LargeResultsSetPagination
    object_cache_key_func = DefaultKeyConstructor()
    list_cache_key_func = DefaultListKeyConstructor()

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def getallrelated(self, request, pk=None):
        collector = NestedObjects(using='default')
        collector.collect(self.queryset.filter(id=pk))

        def format_callback(obj):
            model = obj.__class__
            opts = obj._meta
            no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), obj)
            return no_edit_link

        to_delete = collector.nested(format_callback)

        return Response(data=to_delete)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def deletemany(self, request):
        type = request.data.get('type', None)
        idList = request.data.getlist('idlist', None)
        data = {
            'type': type,
            'idlist': idList
        }
        seriallizer_data = ReviewSerializer(data=data)
        seriallizer_valid = seriallizer_data.is_valid()
        if not seriallizer_valid:
            data = {
                'status': 'fail'
            }
            return Response(data=data, status=status.HTTP_200_OK)
        print(seriallizer_data.validated_data['idlist'])
        self.queryset.filter(id__in=seriallizer_data.validated_data['idlist']).delete()
        data = {
            'status': 'success'
        }
        return Response(data=data, status=status.HTTP_200_OK)


class getCollegeInfoSet(CacheResponseMixin,
                        mixins.UpdateModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CollegeSerializer
    queryset = SettingModel.objects.all()
    object_cache_key_func = DefaultKeyConstructor()
    list_cache_key_func = DefaultKeyConstructor()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if (queryset.count() == 0):
            self.queryset.create(college_name=None, content=None)
        else:
            queryset = queryset[:1]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class getReserverList(CacheResponseMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = dakaReserverSerializer
    queryset = Reserver.objects.all().filter(date__gte=date.today())
    pagination_class = LargeResultsSetPagination
    object_cache_key_func = DefaultKeyConstructor()
    list_cache_key_func = DefaultListKeyConstructor()

    # def get(self, request, *args, **kwargs):
    #     import time
    #     time.sleep(1)
    #     return self.list(request, *args, **kwargs)


class RequestsDataSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RequestsModel.objects.all()

    def __get_serven_data(self, queryset):
        nowDate = date.today()
        countList = []
        allGet, allPost, allDel = [0, 0, 0]
        for x in range(7):
            allNowDate = queryset.filter(date=nowDate)
            getCount = allNowDate.filter(method='GET').count()
            postCount = allNowDate.filter(method='POST').count()
            deleteCount = allNowDate.filter(method='DELETE').count()
            allGet += getCount
            allPost += postCount
            allDel += deleteCount
            countList.append({'date': nowDate,
                              'get': getCount,
                              'post': postCount,
                              'delete': deleteCount})
            nowDate = nowDate - timedelta(days=1)
        countList.reverse()

        def getDict(allGet, allPost, allDel):
            return locals()

        return getDict(allGet, allPost, allDel), countList

    def __get_detail_data(self, queryset):
        dt = datetime.now().replace(minute=0, second=0, microsecond=0)
        resDict = {}
        for index in range(24):
            dtY = dt - timedelta(hours=1)
            res = queryset.filter(datetime__gte=dtY, datetime__lte=dt)
            resDict[dt.strftime('%H:%M')] = res.count()
            dt = dtY
        return resDict

    @cache_response(60 * 60, key_func=DefaultKeyConstructor())
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        resTimeDict = self.__get_detail_data(queryset)
        resultData, countList = self.__get_serven_data(queryset)
        resultData['results'] = {}
        resultData['results']['date'] = countList
        resultData['results']['time'] = resTimeDict
        return Response(resultData)


from rest_framework_extensions.mixins import DetailSerializerMixin
from rest_framework_extensions.mixins import PaginateByMaxMixin, DetailSerializerMixin


class test(DetailSerializerMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    serializer_detail_class = CollegeSerializer
    queryset = Room.objects.all()

    # authentication_classes = [JWTAuthentication]
    # @cache_response(60 * 15,key_func=UserKeyConstructor())
    # def get(self, request):
    #     import time
    #     time.sleep(0.5)
    #     data = {'user':request.user.username}
    #     return Response(data=data, status=status.HTTP_200_OK)
