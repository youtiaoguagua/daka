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
    path('getwxcode/<int:pk>/', views.ReserverWxCode.as_view()),
    path('delreserver/<int:pk>/', views.DeleteReserverView.as_view()),
    path('getcollegename/', views.getCollegeName.as_view()),
    path('checklogin/', views.CheckLogin.as_view()),
    # path('wxet/', views.WxEnterprise.as_view()),
    path('feishu/', views.FeiShu.as_view()),
    path('notice/', views.GetNotice.as_view()),
    path('upload/', views.FileUploadView.as_view()),

    # path('about/', views.AboutCollegeView.as_view()),
]

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'ariticle', views.getAriticleSet,basename='user') #得到首页文章
router.register(r'college', views.CollegeListView,basename='user') #得到首页文章
router.register(r'signup', views.HandelSignUpDateSet,basename='user') #得到首页文章
urlpatterns += router.urls


