from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework import generics, mixins

from .serializers import Login
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.signals import user_logged_in
from django.contrib.admin.utils import NestedObjects
from django.utils.text import capfirst

from wxdaka.models import Reserver, Room, SettingModel
from datetime import date
from .serializers import ReserverSerializer, ReviewSerializer, RoomSerializer, CollegeSerializer
from rest_framework.pagination import PageNumberPagination, CursorPagination
from collections import OrderedDict


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 10
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


class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()
    pagination_class = LargeResultsSetPagination

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


class getCollegeInfoSet(mixins.UpdateModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CollegeSerializer
    queryset = SettingModel.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if (queryset.count() == 0):
            self.queryset.create(college_name=None, content=None)
        else:
            queryset = queryset[:1]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class getReserverList(generics.ListAPIView):



from rest_framework_simplejwt.authentication import JWTAuthentication


class test(APIView):
    permission_classes = [IsAuthenticated]

    # authentication_classes = [JWTAuthentication]

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
