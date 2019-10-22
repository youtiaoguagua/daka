from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('getalldata/', views.getGloabDataView.as_view()),
    path('review/', views.ReviewReserverView.as_view()),
    path('reserver/', views.getReserverList.as_view()),
    # path('test/', views.test.as_view())
]

from dakadmin.views import RoomViewSet,getCollegeInfoSet,RequestsDataSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'room', RoomViewSet, basename='user')
router.register(r'college', getCollegeInfoSet, basename='user')
router.register(r'request', RequestsDataSet, basename='user')
router.register(r'test', views.test, basename='user')
urlpatterns += router.urls
