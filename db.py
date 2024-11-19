import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# 獲取環境變數
MONGODB_URI = os.getenv('MONGODB_URI', None)
if MONGODB_URI is None:
    print('Specify MONGODB_URI as environment variables.')
    sys.exit(1)


# 初始化 MongoDB
client = MongoClient(MONGODB_URI)
db = client.dintaifung_waiting
users_collection = db.users