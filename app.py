import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    CarouselTemplate,
    CarouselColumn,
    TemplateMessage,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

from db import users_collection
from store import store
from waiting import getShopStatus

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None))
lineHandler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET', None))


@app.route("/")
def index():
    # Return request info
    res = "From Dintaifung Waiting Assistant<br>"
    res += "Request Info:<br>"
    res += "Host: " + request.host + "<br>"
    res += "URL: " + request.url + "<br>"
    res += "Base URL: " + request.base_url + "<br>"
    res += "Remote Addr: " + request.remote_addr + "<br>"
    res += "Method: " + request.method + "<br>"
    res += "Path: " + request.path + "<br>"
    res += "Full Path: " + request.full_path + "<br>"
    res += "Query String: " + request.query_string.decode("utf-8") + "<br>"
    res += "Headers: <br>"
    for key, value in request.headers:
        res += key + ": " + value + "<br>"
    res += "Data: " + request.data.decode("utf-8") + "<br>"

def get_or_create_user(line_user_id):
    user = users_collection.find_one({"line_user_id": line_user_id})
    if not user:
        user = {
            "line_user_id": line_user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "notifies": []
        }
        users_collection.insert_one(user)
    return user

def update_user(line_user_id, update_data):
    update_data["updated_at"] = datetime.now()
    res = users_collection.update_one({"line_user_id": line_user_id}, {"$set": update_data})

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        lineHandler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

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
            QuickReplyItem(
                action=MessageAction(label="刪除通知目標", text="/delete")
            ),
        ]
    )
    return quick_reply

@lineHandler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id
    user = get_or_create_user(user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        if text == "/create":
            # Ask shop position
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        # Change to Carousel
                        TemplateMessage(
                            altText="店家清單",
                            template=CarouselTemplate(
                                columns=[
                                    CarouselColumn(
                                        title=f"{shop['cName']}",
                                        text=f"{shop['cName']}",
                                        actions=[
                                            MessageAction(label="建立此店通知", text=f"/createShop {shop['storeId']}")
                                        ]
                                    ) for shop in store[:10]
                                ] 
                            ),
                        quick_reply=get_quick_reply_menu()
                        )
                    ]
                )
            )
            return
        if text.startswith("/createShop"):
            # Ask seat position
            shop_id = text.split(" ")[1]
            shop = next((shop for shop in store if shop["storeId"] == shop_id), None)
            tableType = shop["tableType"]
            try:
                shopStatus = getShopStatus(shopId=shop_id)
                shopStatus = shopStatus[0]
            except:
                shopStatus = {}
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TemplateMessage(
                            altText="座位清單",
                            template=CarouselTemplate(
                                columns=[
                                    CarouselColumn(
                                        title=f"座位{tableType[i]}人",
                                        text=f"目前等候:號碼{shopStatus['num_'+str(i+1)]}",
                                        actions=[
                                            MessageAction(label="建立通知目標", text=f"/createNotify {shop_id} {tableType[i]}")
                                        ]
                                    ) for i in range(len(tableType))
                                ] 
                            ),
                        quick_reply=get_quick_reply_menu()
                        )
                    ]
                )
            )
            return
        if text.startswith("/createNotify"):
            # Create notification, set user No
            shop_id = text.split(" ")[1]
            seatType = text.split(" ")[2]
            shop = next((shop for shop in store if shop["storeId"] == shop_id), None)
            if not shop:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="找不到此店",
                                quickReply=get_quick_reply_menu()
                            ),
                        ]
                    )
                )
            else:
                user["notifies"].append({
                    "shopId": shop_id,
                    "shopName": shop["cName"],
                    "seatType": seatType
                })
                update_user(user_id, {"notifies": user["notifies"]})
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="輸入號碼以建立通知",
                                quickReply=get_quick_reply_menu()
                            ),
                        ]
                    )
                )
            return
        if text == "/list":
            # Show notification list
            notifies = user["notifies"]
            if not notifies:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="沒有任何通知目標",
                                quickReply=get_quick_reply_menu()
                            ),
                        ]
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            # Change to Carousel
                            TemplateMessage(
                                altText="通知清單",
                                template=CarouselTemplate(
                                    columns=[
                                        CarouselColumn(
                                            title=f"{notify['shopName']}",
                                            text=f"{notify['seatNo']} {getShopStatus(shopId=notify['shopId'])[0]['wait_time']}",
                                            actions=[
                                                MessageAction(label="刪除通知目標", text=f"/delete {notify['shopId']} {notify['seatNo']}")
                                            ]
                                        ) for notify in notifies
                                    ] 
                                ),
                            quick_reply=get_quick_reply_menu()
                            )
                        ]
                    )
                )
            return
        if text.startswith("/delete"):
            # Delete notification
            return
        if any([not notify.get('seatNo', False) for notify in user['notifies']]):
            notify = next((notify for notify in user['notifies'] if not notify.get('seatNo', False)), None)
            print(notify)
            seatNo = text
            if isinstance(seatNo, str):
                try:
                    seatNo = int(seatNo)
                except:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(
                                    text="請輸入數字",
                                    quickReply=get_quick_reply_menu()
                                ),
                            ]
                        )
                    )
            notify['seatNo'] = seatNo
            update_user(user_id, {"notifies": user["notifies"]})
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="建立成功",
                            quickReply=get_quick_reply_menu()
                        ),
                    ]
                )
            )





if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True)