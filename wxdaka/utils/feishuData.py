from dateutil.parser import parse as timeparser
import json


def FeishuMessage(message):
    contactMap = {'phone': "电话", 'wx': "微信", 'qq': 'QQ'}
    ShenHeiMessage = {
        "chat_id": message['chat_id'],
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "预约审核"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "预约房间：{}".format(message['roomData']['room_name'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "活动名称：{}".format(message['name'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "活动描述：{}".format(message['event_intro'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "负责人：{}".format(message['belong'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "工号学号：{}".format(message['school_id'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "{}：{}".format(contactMap[message['contact_method']],message['contact_info'])
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "时间：{}".format(timeparser(message['date']).strftime("%Y年%m月%d日"))
                             }
                         },
                         {
                             "is_short": False,
                             "text": {
                                 "tag": "lark_md",
                                 "content": "证件图片：[证件图片]({})".format(message['prove_image'])
                             }
                         }
                     ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "不同意"
                            },
                            "type": "primary",
                            "value": {
                                "action": "reject",
                                "id":message['id']
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "同意"
                            },
                            "type": "primary",
                            "value": {
                                "action": "accept",
                                "id": message['id']
                            }
                        }
                    ]
                }
            ]
        }
    }
    ShenHeiMessage['card']['elements'][1]['actions'][0]['value']['data'] = json.dumps(ShenHeiMessage['card'])
    ShenHeiMessage['card']['elements'][1]['actions'][1]['value']['data'] = json.dumps(ShenHeiMessage['card'])
    return ShenHeiMessage