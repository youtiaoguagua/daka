from __future__ import absolute_import, unicode_literals

from celery import shared_task
from .models import (Reserver, WxInfo)
from datetime import date
from datetime import datetime
import hashlib
import requests
from django.conf import settings
import json


@shared_task()
def DelectExpiredTask():
    Reserver.objects.filter(date__lt=date.today()).delete()


def getAccessToken():
    result = requests.get(
        'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}'.format(corpid=settings.CORPID,corpsecret=settings.CORPSECRET)).json()
    print(result)
    if result['errcode'] == 0:
        frist = WxInfo.objects.first()
        if frist:
            frist.accesstoken = result['access_token']
        else:
            WxInfo.objects.create(accesstoken=result['access_token'])
        return result['access_token']


def sendCard(accesstoken, message):
    contact_method_map = {'phone': "电话", 'wx': "微信", 'qq': 'QQ'}
    data = {
        "touser": "@all",
        "msgtype": "taskcard",
        "agentid": settings.AGENTID,
        "taskcard": {
            "title": "预约审核",
            "description": '''房        间：{room_name}
活动名称：{name}
所        属：{belong} 
活动介绍：{event_intro} 
联系方式：{contact_method}{contact_info}
使用时间：{date} {start_time}-{end_time}
                           '''.format(
                room_name=message['roomData']['room_name'], name=message['name'], belong=message['belong'],
                event_intro=message['event_intro'], contact_method=contact_method_map[message['contact_method']],
                contact_info=message['contact_info'],
                date=message['date'], start_time=message['start_time'], end_time=message['end_time'],
            ),
            "task_id": hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest(),
            "btn": [
                {
                    "key": "accept-" + str(message['id']),
                    "name": "批准",
                    "replace_name": "已批准",
                    "color": "red",
                    "is_bold": True
                },
                {
                    "key": "refuse-" + str(message['id']),
                    "name": "驳回",
                    "replace_name": "已驳回"
                }
            ]
        }
    }
    resCordInfo = requests.post('https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(accesstoken),
                                data=json.dumps(data)).json()
    print(resCordInfo)
    return resCordInfo


@shared_task()
def SendReserverTask(message):
    frist = WxInfo.objects.first()
    if not frist:
        accesstoken = getAccessToken()
    else:
        accesstoken = frist.accesstoken
    resCordInfo = sendCard(accesstoken, message)
    for x in range(2):
        if resCordInfo['errcode'] == 0:
            break
        else:
            accesstoken = getAccessToken()
            resCordInfo = sendCard(accesstoken, message)
            continue
        # elif resCordInfo['errcode'] == 0:
        #     print("发送成功")
        #     break
        # else:
        #     return None


@shared_task()
def SendTemplateMessage(userInfo):
    resultToken = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}".format(
            APPID=settings.WXAPPID, APPSECRET=settings.WXSECRET)).json()
    errcode = resultToken.get('errcode', None)
    if errcode == None:
        data = {
            "touser": userInfo['openid'],
            "template_id": settings.WXTEPLETE,
            "form_id": userInfo['formid'],
            "data": {
                "keyword1": {
                    "value": userInfo['event_status']
                },
                "keyword2": {
                    "value": userInfo['event_name']
                },
                "keyword3": {
                    "value": userInfo['event_date']
                },
                "keyword4": {
                    "value": userInfo['event_room']
                }
            },
            "emphasis_keyword": "keyword1.DATA"
        }
        a = requests.post('https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token={}'.format(
            resultToken['access_token']),data=json.dumps(data))

        print(a.json())


@shared_task()
def test():
    print('dasd')
