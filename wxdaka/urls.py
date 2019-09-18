from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login/', views.Login.as_view()),
    path('room/', views.GetAllRoom.as_view()),
    path('reserver/', views.ReserverRoomView.as_view()),
    path('reserver/<str:date>/<int:room>/', views.ReserverRoomView.as_view()),
    path('delreserver/<int:pk>/', views.DeleteReserverView.as_view()),
    path('getcollegename/', views.getCollegeName.as_view()),
    path('checklogin/', views.CheckLogin.as_view()),
    path('wxet/', views.WxEnterprise.as_view()),
    # path('about/', views.AboutCollegeView.as_view()),
]
