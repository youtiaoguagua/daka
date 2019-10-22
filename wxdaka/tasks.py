from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import (Reserver, WxInfo, WxAriticle,College)
from datetime import date
from datetime import datetime
import hashlib
import requests
from django.conf import settings
import json
from daka.celery import app as celery_app
from celery.schedules import crontab
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime,timedelta
from dateutil.parser import parse as timeparser
import pytz
from dateutil import tz
from django.utils.timezone import make_naive
from django_redis import get_redis_connection
from django_celery_beat.models import CrontabSchedule, PeriodicTask


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # sender.add_periodic_task(10, getHomeAriticle.s())
    pass




# 得到微信的Rss
@celery_app.task
def getHomeAriticle():
    guid = None
    firstAriticle = WxAriticle.objects.first()
    if firstAriticle != None:
        guid = firstAriticle.guid
    d = feedparser.parse('https://rsshub.app/kzfeed/topic/baLARAjQD4WNK')
    for item in d.entries:
        if guid == item.id:
            break
        soup = BeautifulSoup(item.summary, 'html.parser')
        img_tag = soup.select_one('img[src]')
        to_zone = tz.gettz('CST')
        pubDate = make_naive(timeparser(item.published.strip('"')))
        req = requests.get(item.id)
        soup = BeautifulSoup(req.text, 'html.parser')
        content = str(soup.find('div', class_='rich_media_area_primary_inner'))
        # content = req.text
        if img_tag:
            data = {
                'guid': item.id,
                'title': item.title,
                'image': img_tag['src'],
                'content': content,
                'pubDate': pubDate,
            }
            print(data)
            WxAriticle.objects.create(**data)


# 定期删除过期的预定
@shared_task()
def DelectExpiredTask():
    Reserver.objects.filter(date__lt=date.today()).delete()

# 维护微信access token
def get_access_token(getNew=False):
    red = get_redis_connection("redis")
    accesstoken = None
    def get_access_token():
        resultToken = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}".format(
                APPID=settings.WXAPPID, APPSECRET=settings.WXSECRET)).json()
        errcode = resultToken.get('errcode', None)
        if errcode == None:
            accesstoken = resultToken['access_token']
            print('task',accesstoken)
            expires_in = resultToken['expires_in']
            red.set('wxdakaAccessToken', accesstoken, ex=1200)
            return accesstoken
    if getNew:
        return get_access_token()
    try:
        red.ping()
        accesstoken = red.get('wxdakaAccessToken')
        if not accesstoken:
            accesstoken = get_access_token()
        else:
            accesstoken = accesstoken.decode('utf8')
        return accesstoken
    except BaseException as e:
        raise e


# def getAccessToken():
#     result = requests.get(
#         'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}'.format(
#             corpid=settings.CORPID, corpsecret=settings.CORPSECRET)).json()
#     print(result)
#     if result['errcode'] == 0:
#         frist = WxInfo.objects.first()
#         if frist:
#             frist.accesstoken = result['access_token']
#         else:
#             WxInfo.objects.create(accesstoken=result['access_token'])
#         return result['access_token']
#
#
# def sendCard(accesstoken, message):
#     contact_method_map = {'phone': "电话", 'wx': "微信", 'qq': 'QQ'}
#     data = {
#         "touser": "@all",
#         "msgtype": "taskcard",
#         "agentid": settings.AGENTID,
#         "taskcard": {
#             "title": "预约审核",
#             "description": '''房        间：{room_name}
# 活动名称：{name}
# 所        属：{belong}
# 活动介绍：{event_intro}
# 联系方式：{contact_method}{contact_info}
# 使用时间：{date} {start_time}-{end_time}
#                            '''.format(
#                 room_name=message['roomData']['room_name'], name=message['name'], belong=message['belong'],
#                 event_intro=message['event_intro'], contact_method=contact_method_map[message['contact_method']],
#                 contact_info=message['contact_info'],
#                 date=message['date'], start_time=message['start_time'], end_time=message['end_time'],
#             ),
#             "task_id": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest(),
#             "btn": [
#                 {
#                     "key": "accept-" + str(message['id']),
#                     "name": "批准",
#                     "replace_name": "已批准",
#                     "color": "red",
#                     "is_bold": True
#                 },
#                 {
#                     "key": "refuse-" + str(message['id']),
#                     "name": "驳回",
#                     "replace_name": "已驳回"
#                 }
#             ]
#         }
#     }
#     resCordInfo = requests.post('https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(accesstoken),
#                                 data=json.dumps(data)).json()
#     print(resCordInfo)
#     return resCordInfo
#
# @shared_task()
# def SendReserverTask(message):
#     frist = WxInfo.objects.first()
#     if not frist:
#         accesstoken = getAccessToken()
#     else:
#         accesstoken = frist.accesstoken
#     resCordInfo = sendCard(accesstoken, message)
#     for x in range(2):
#         if resCordInfo['errcode'] == 0:
#             break
#         else:
#             accesstoken = getAccessToken()
#             resCordInfo = sendCard(accesstoken, message)
#             continue

# 发送小程序通知
@shared_task()
def SendTemplateMessage(userInfo):
    # red = get_redis_connection("redis")
    # try:
    #     red.ping()
    #     accesstoken = red.get('wxdakaAccessToken')
    #     if not accesstoken:
    #         resultToken = requests.get(
    #             "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}".format(
    #                 APPID=settings.WXAPPID, APPSECRET=settings.WXSECRET)).json()
    #         errcode = resultToken.get('errcode', None)
    #         if errcode == None:
    #             accesstoken = resultToken['access_token']
    #             red.set('wxdakaAccessToken', accesstoken, ex=5400)
    #     else:
    #         accesstoken = accesstoken.decode('utf8')
    # except:
    #     return
    accesstoken = get_access_token()
    data = {
        "touser": userInfo['openid'],
        "template_id": "anuMnlIXj9Bod4b908Tsv2_Y-ycBBCMNIRuitNBFV_Q",
        "page": "index",
        "data": {
            "phrase1": {
                "value": userInfo['result']
            },
            "thing2": {
                "value": userInfo['room']
            },
            "date3": {
                "value": userInfo["startDate"]
            },
            "date4": {
                "value": userInfo['endDate']
            },
            "name5": {
                "value": userInfo['person']
            }
        }
    }
    b = requests.post('https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'.format(
        access_token=accesstoken), data=json.dumps(data))
    print(b.text)


@shared_task()
def SendCroServerMessageTask(**kwargs):
    print(kwargs)
    reserver = Reserver.objects.get(id=kwargs['id'])
    accesstoken = get_access_token()
    def get_event_intro():
        if 0<len(reserver.event_intro)<20:
            return reserver.event_intro
        elif len(reserver.event_intro)>=20:
            return reserver.event_intro[0:19]
        else:
            return "什么也没填"
    data = {
        "touser":reserver.user.username,
        "template_id": "T10iPYCCqLNS2ve41HP5Z3t0UthVW9rhQktLrkl1Vv0",
        "page": "index",
        "data": {
            "thing4": {
                "value": reserver.name
            },
            "date5": {
                "value": "{} {}".format(reserver.date.strftime("%Y-%m-%d"),reserver.start_time.strftime("%H:%M"))
            },
            "thing6": {
                "value": "{} {}".format(reserver.room.college_id.college_name,reserver.room.room_name)
            },
            "thing2": {
                "value": get_event_intro()
            }
        }
    }
    b = requests.post('https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'.format(
        access_token=accesstoken), data=json.dumps(data))
    print(b.text)
    pass



from wxdaka.utils.feishuData import FeishuMessage
# 发送审核通知到飞信
@shared_task()
def SendReserverTask(message):
    # 设置定时任务，在前30分钟提醒活动开始
    serverDate = timeparser(message['date'])
    serverTime= timeparser(message['start_time'])
    serverDatetime = serverDate+timedelta(hours=serverTime.hour,minutes=serverTime.minute)
    if serverDatetime > datetime.now()+timedelta(minutes=30):
        # 提前三十分钟提醒
        expiresDatetime = serverDatetime.astimezone(tz.UTC)
        runDatetime = expiresDatetime-timedelta(minutes=30)
        SendCroServerMessageTask.apply_async(kwargs={'id':message['id']}, eta=runDatetime ,expires=expiresDatetime)
    else:
        SendCroServerMessageTask.apply_async(kwargs={'id':message['id']})
    try:
        collegeData = College.objects.get(college_name=message['roomData']['college_name'])
        collegeChatId = collegeData.college.college_chat_id
        message['chat_id'] = collegeChatId
    except:
        return
    # 得到飞书的accessid并存入redis
    red = get_redis_connection("redis")
    try:
        red.ping()
        accesstoken = red.get('feishudakaAccessToken')
        if not accesstoken:
            data = {
                "app_id": settings.FEISHUAPPID,
                "app_secret": settings.FEISHUAPPSECRET
            }
            resultToken = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/",
                                        data=json.dumps(data)).json()
            errcode = resultToken.get('code')
            if errcode == 0:
                accesstoken = resultToken['tenant_access_token']
                red.set('feishudakaAccessToken', accesstoken, ex=5400)
        else:
            accesstoken = accesstoken.decode('utf8')
    except:
        return
    headers = {
        "Authorization": "Bearer {}".format(accesstoken),
        "Content-Type": "application/json"
    }
    data = FeishuMessage(message)
    requests.post("https://open.feishu.cn/open-apis/message/v3/send/", data=json.dumps(data), headers=headers)


@shared_task()
def testArgs():
    print("草泥马")