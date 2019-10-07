from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('getalldata/', views.getGloabDataView.as_view()),
    path('review/', views.ReviewReserverView.as_view()),
    path('test/', views.test.as_view())
]

from dakadmin.views import RoomViewSet,getCollegeInfoSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'room', RoomViewSet, basename='user')
router.register(r'college', getCollegeInfoSet, basename='user')
urlpatterns += router.urls
