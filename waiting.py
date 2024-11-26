import json


from db import users_collection
from app import get_quick_reply_menu
from store import store
from utils import sendNotify, getShopStatus

def cronJob():
    store_time_data = {shop["storeId"]:getShopStatus(shopId=shop["storeId"])[0] for shop in store}

    print(json.dumps(store_time_data, indent=2 , ensure_ascii=False))

    for user in users_collection.find():
        print(user)
        notifies = user.get('notifies', {})
        for notifyShop in notifies:
            for seatNo, notify in notifies[notifyShop].items():
                try:
                    shopId = notify["shopId"]
                    seatTypeId = notify["seatTypeId"]
                    storeSeatNo = store_time_data[shopId]["num_"+str(seatTypeId)]
                    seatWaiting = int(seatNo) - int(storeSeatNo)
                    print(seatWaiting, seatNo, storeSeatNo)
                    if seatWaiting < -3:
                        print("passed")
                        users_collection.update_one({"line_user_id": user['line_user_id']}, {"$set": {f"notifies.{notifyShop}.{seatNo}.passed": True}})
                        continue
                    if seatWaiting <= 5 and not notify['5']:
                        print("notify5")
                        sendNotify(user_id=user['line_user_id'],text=f"目前{notify['shopName']}店{notify['seatType']}人叫號:{storeSeatNo}\n您的號碼為{seatNo}\n請準備前往")
                        users_collection.update_one({"line_user_id": user['line_user_id']}, {"$set": {f"notifies.{notifyShop}.{seatNo}.5": True}})
                        continue
                    if seatWaiting <= 3 and not notify['3']:
                        print("notify3")
                        sendNotify(user_id=user['line_user_id'],text=f"目前{notify['shopName']}店{notify['seatType']}人叫號:{storeSeatNo}\n您的號碼為{seatNo}\n請準備前往")
                        users_collection.update_one({"line_user_id": user['line_user_id']}, {"$set": {f"notifies.{notifyShop}.{seatNo}.3": True}})
                        continue
                    if seatWaiting <= 1 and not notify['1']:
                        print("notify1")
                        sendNotify(user_id=user['line_user_id'],text=f"目前{notify['shopName']}店{notify['seatType']}人叫號:{storeSeatNo}\n您的號碼為{seatNo}\n請準備前往")
                        users_collection.update_one({"line_user_id": user['line_user_id']}, {"$set": {f"notifies.{notifyShop}.{seatNo}.1": True}})

                except Exception as e:
                    print(e)

def main():
    cronJob()

if __name__ == '__main__':
    main()