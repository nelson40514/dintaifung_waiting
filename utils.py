import os

from dotenv import load_dotenv
from requests import post

from store import store

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)

load_dotenv()
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None))


def get_quick_reply_menu():
    quick_reply = QuickReply(
        items=[
            # QuickReplyItem(
            #     action=MessageAction(label="查看狀態", text="/status")
            # ),
            QuickReplyItem(
                action=MessageAction(label="建立通知目標", text="/create")
            ),
            QuickReplyItem(
                action=MessageAction(label="顯示通知清單", text="/list")
            ),
            # QuickReplyItem(
            #     action=MessageAction(label="刪除通知目標", text="/delete")
            # ),
        ]
    )
    return quick_reply

def sendNotify(user_id, text="Notify"):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[
                    TextMessage(
                        text=text,
                        quickReply=get_quick_reply_menu()
                    )
                ]
            )
        )


def getShopStatus(shopId="0001"):
    url = 'https://www.dintaifung.tw/Queue/Home/WebApiTest'
    parameter = {"storeid":shopId}

    res = post(url, data=parameter)

    # print(res.json())
    return res.json()