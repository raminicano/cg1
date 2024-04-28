from fastapi import FastAPI, HTTPException
from bson.objectid import ObjectId
from pymongo import mongo_client
from pymongo.errors import PyMongoError

import pydantic
import os.path
import json


pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

BASE_DIR = os.path.dirname(os.path.dirname(os.path.relpath("./")))
secret_file = os.path.join(BASE_DIR, 'secret.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        errorMsg = "Set the {} environment variable.".format(setting)
        return errorMsg

HOSTNAME = get_secret("ATLAS_Hostname")
USERNAME = get_secret("ATLAS_Username")
PASSWORD = get_secret("ATLAS_Password")

client = mongo_client.MongoClient(f'mongodb://{USERNAME}:{PASSWORD}@{HOSTNAME}')
print('Connected to Mongodb...')

mydb = client['cg']
mycol = mydb['congestion']

# MongoDB에 데이터를 추가하는 함수
async def create_item(collection_name: str, item):
    collection = mydb[collection_name]
    try:
        result = collection.insert_one(item)
        return {"_id": str(result.inserted_id), "message": "Item successfully added"}
    except PyMongoError as e:
        return {"status_code" : 400, "result" : f"Error saving item: {str(e)}"}

