
from fastapi import FastAPI, Query, HTTPException
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
import requests
import json
import os
from database import mydb, create_item
import pydantic
from datetime import datetime
from services.location_service import fetch_congestion_data


pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str


app = FastAPI()

message = {
    "약간 붐빔" : "사람들이 몰려있을 가능성이 크고 붐빈다고 느낄 수 있어요. 인구밀도가 높은 구간에서는 도보 이동시 부딪힘이 발생할 수 있어요.",
    "여유" : "사람이 몰려있을 가능성이 낮고 붐빔은 거의 느껴지지 않아요. 도보 이동이 자유로워요.",
    "보통" : "사람이 몰려있을 수 있지만 크게 붐비지는 않아요. 도보 이동에 큰 제약이 없어요.",
    "붐빔" : "사람들이 몰려있을 가능성이 매우 크고 많이 붐빈다고 느낄 수 있어요. 인구밀도가 높은 구간에서는 도보 이동시 부딪힘이 발생할 수 있어요."
}

# MongoDB 접속 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.relpath(__file__)))
secret_file = os.path.join(BASE_DIR, 'secret.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        raise Exception(f"Set the {setting} environment variable.")




# 서울 공공 API 데이터 가져오기 및 MongoDB에 저장
@app.get("/fetch_and_save_congestion")
async def fetch_and_save_congestion(location: str = Query(...)):
    SEOUL_API_KEY = get_secret("SEOUL_API_KEY")
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/citydata/1/2/{location}"
    response = requests.get(url)
    data = response.json()
    city_data = data['CITYDATA']

    # MongoDB에 데이터 저장 시도
    try:
        result = await create_item('congestion', city_data)
        return {"status_code": 200, "result": result}
    except HTTPException as e:
        return {"status_code": e.status_code, "result": e.detail}




@app.get("/location/congestion")
async def get_congestion_info(location: str, input_time: datetime = Query(None)):
    closest_location = fetch_congestion_data(location)

    print(closest_location)
    # 입력 시간이 제공되지 않았다면 현재 시간을 사용
    if input_time is None:
        input_time = datetime.now()
        query = {
            "AREA_NM": closest_location,
            "LIVE_PPLTN_STTS.PPLTN_TIME": input_time.strftime("%Y-%m-%d %H:%M")
        }
    else:
        query = {
            "AREA_NM": closest_location
        }
    
    current_time = datetime.now()

    result_data = {}

    try:
        data = mydb['congestion'].find_one(query, sort=[('_id', -1)]) # sort로 가장 최근에 들어간 데이터를 가져와서 제일 정확도가 높은 데이터를 가져옴
        # data = mydb['congestion'].find(query, {"_id" : 0}, sort=[('_id', -1)])
        # return data
        if not data:
            raise HTTPException(status_code=404, detail="Data not found")
        
        # 현재시간은 입력을 안할것임 그래서 현재시간이지만 과거에 호출한 경우는 없다.
        if input_time.date() == current_time.date() and input_time.hour == current_time.hour:
            # 현재 시간 데이터를 반환
            result_data = { 
                "area_nm" : closest_location,
                "area_congest_lvl": data["LIVE_PPLTN_STTS"][0]["AREA_CONGEST_LVL"],
                "area_congest_msg": data["LIVE_PPLTN_STTS"][0]["AREA_CONGEST_MSG"],
                # "inquiry_time": input_time.strftime("%Y.%m.%d %H:%M")
                "inquiry_time": current_time
            }
        else:
            # 입력 시간에 해당하는 예측 데이터를 찾기
            forecast_data = next((item for item in data["LIVE_PPLTN_STTS"][0]["FCST_PPLTN"]
                                  if datetime.strptime(item["FCST_TIME"], "%Y-%m-%d %H:%M") == input_time), None)
            if forecast_data is None:
                raise HTTPException(status_code=404, detail="Forecast data not found for the given time")
            result_data = {
                "area_nm" : closest_location,
                "area_congest_lvl": forecast_data["FCST_CONGEST_LVL"],
                "area_congest_msg" : message[forecast_data["FCST_CONGEST_LVL"]],
                "inquiry_time": forecast_data['FCST_TIME']
            }

        return {"code": 200, "message": "혼잡도 데이터 조회에 성공하였습니다.", "data": result_data}
    except Exception as e:
        return {"code": 500, "message": str(e), "data": {}}


