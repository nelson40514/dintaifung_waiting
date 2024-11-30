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
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    JoinEvent,
    FollowEvent,
    TextMessageContent
)

from db import users_collection
from store import store
from utils import getShopStatus, get_quick_reply_menu
from waiting import cronJob

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None))
lineHandler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET', None))


@app.route("/cronjob")
def cron():
    try:
        cronJob()
        return "Success"
    except:
        return "Fail"

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
    return res

def get_or_create_user(line_user_id):
    user = users_collection.find_one({"line_user_id": line_user_id})
    if not user:
        user = {
            "line_user_id": line_user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "notifies": {}
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

def welcomeReplyMessage():
    return ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text="歡迎加入Dintaifung等待機器人\n輸入\\create建立等候清單\n輸入list查看等候清單\n或點選下方快速回復選項",
                        quickReply=get_quick_reply_menu()
                    ),
                ]
            )

@lineHandler.add(JoinEvent)
def handle_join(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            welcomeReplyMessage()
        )

@lineHandler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            welcomeReplyMessage()
        )

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
                                        text=f"{shop['cName']}\n預計等候時間{getShopStatus(shopId=shop['storeId'])[0]['wait_time']}分鐘",
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
            seatTypeId = 1 if seatType == "1~2" else 2 if seatType == "3~4" else 3 if seatType == "5~6" else 4 if seatType == "7" else 0
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
                tempNotify = {
                    "shopId": shop_id,
                    "shopName": shop["cName"],
                    "seatTypeId": seatTypeId,
                    "seatType": seatType
                }
                update_user(user_id, {"tempNotify": tempNotify})
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
            notifies = {}
            for shopNotifies in user["notifies"].values():
                for seatNo, notify in shopNotifies.items():
                    notifies[seatNo] = notify
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
                                            text=f"目前{notify['seatType']}座位\n登記號碼為:{seatNo}\n目前叫號為:{getShopStatus(shopId=notify['shopId'])[0]['num_'+str(notify['seatTypeId'])]}",
                                            actions=[
                                                MessageAction(label="刪除通知目標", text=f"/delete {notify['shopId']} {seatNo}")
                                            ]
                                        ) for seatNo, notify in notifies.items()
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
            notifies = user.get('notifies', {})
            shopId = text.split(" ")[1]
            shop = notifies.get(shopId, {})
            print(f"shop: {shop}")
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
                return
            
            seatNo = text.split(" ")[2]
            seat = shop.get(seatNo, {})
            if not seat:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="找不到此預約",
                                quickReply=get_quick_reply_menu()
                            ),
                        ]
                    )
                )
                return
            
            del shop[seatNo]
            update_user(user_id, {"notifies": notifies})
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="刪除成功",
                            quickReply=get_quick_reply_menu()
                        ),
                    ]
                )
            )
            return

        if user['tempNotify']:
            try:
                seatNo = str(text)
                notify = user['tempNotify']
                for t in ['5', '3', '1', 'passed']:
                    notify[t] = False
                shopId = notify['shopId']                    
                notifies = user.get('notifies', {shop['storeId']:{} for shop in store})
                notifies[shopId][seatNo] = notify
                update_user(user_id, {
                    "notifies" : notifies,
                    "tempNotify": None
                })
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
            except Exception as e:
                print(e)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text=f"建立失敗:{str(e)}",
                                quickReply=get_quick_reply_menu()
                            ),
                        ]
                    )
                )
            return
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text=f"輸入:{text}，可能輸入錯誤",
                        quickReply=get_quick_reply_menu()
                    ),
                ]
            )
        )






if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True)