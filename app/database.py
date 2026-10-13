
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "attendance_db")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=3000,
    tz_aware=True,
)

db = client[MONGO_DB]

employees_collection = db["employees"]
attendance_collection = db["attendance_logs"]
