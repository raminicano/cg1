
from fastapi import FastAPI, Query, HTTPException
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
import requests
import json
import os
from database import mydb, create_item
import pydantic
from datetime import datetime, timedelta
from services.location_service import fetch_congestion_data, haversine, get_location
import pandas as pd
from model.models import *



pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str


app = FastAPI()

message = {
    "여유" : "사람이 몰려있을 가능성이 낮고 붐빔은 거의 느껴지지 않아요. 도보 이동이 자유로워요.",
    "보통" : "사람이 몰려있을 수 있지만 크게 붐비지는 않아요. 도보 이동에 큰 제약이 없어요.",
    "약간 붐빔" : "사람들이 몰려있을 가능성이 크고 붐빈다고 느낄 수 있어요. 인구밀도가 높은 구간에서는 도보 이동시 부딪힘이 발생할 수 있어요.",
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
async def fetch_and_save_congestion(place: str = Query(...)):
    SEOUL_API_KEY = get_secret("SEOUL_API_KEY")
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/citydata/1/2/{place}"
    response = requests.get(url)
    data = response.json()
    city_data = data['CITYDATA']
    print('일단 호출까지는 했음')

    # MongoDB에 데이터 저장 시도
    try:
        result = await create_item('congestion', city_data)
        return {"status_code": 200, "result": result}
    except HTTPException as e:
        return {"status_code": e.status_code, "result": e.detail}


# 위치 기준 혼잡도 찾기
@app.get("/location/test")
async def test(location: str, input_time: datetime = Query(None)):
    closest_location = fetch_congestion_data(location)
    print(closest_location)
    query = {
            "AREA_NM": closest_location
        }
    data = mydb['congestion'].find_one(query)
    return {'code' : 200, 'data' : data}

# 위치 기준 혼잡도 찾기
@app.get("/location/congestion")
async def get_congestion_info(location: str, input_time: datetime = Query(None)):
    closest_location = fetch_congestion_data(location)

    print(closest_location)
    # 입력 시간이 제공되지 않았다면 현재 시간을 사용
    if input_time is None:
        input_time = datetime.now()
        one_hour_ago = datetime.now() - timedelta(hours=1)
        hour = one_hour_ago.hour  # 시간 부분 추출
        date_str = input_time.strftime("%Y-%m-%d")

        # 쿼리에서 시간 비교
        query = {
            "AREA_NM": closest_location,
            "$expr": {
                "$and": [
                    {"$eq": [{"$substr": [{"$arrayElemAt": ["$LIVE_PPLTN_STTS.PPLTN_TIME", 0]}, 0, 10]}, date_str]}, # 첫 번째 요소의 날짜가 일치하는지 확인
                    {"$eq": [{"$hour": {"$dateFromString": {"dateString": {"$arrayElemAt": ["$LIVE_PPLTN_STTS.PPLTN_TIME", 0]}}}}, hour]}  # 계산된 1시간 전의 시간
                ]
            }
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
            # 데이터를 저장하고
            result = await fetch_and_save_congestion(place=closest_location)
            print(result)
            # 다시 쿼리 호출
            data = mydb['congestion'].find_one({"AREA_NM": closest_location}, sort=[('_id', -1)])
            # raise HTTPException(status_code=404, detail="Data not found")
        
        # 현재시간은 입력을 안할것임 그래서 현재시간이지만 과거에 호출한 경우는 없다.
        if input_time.date() == current_time.date() and input_time.hour == current_time.hour:
            print('현재시간 동일함')
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
            print('예측시간 찾는중')
            forecast_data = next((item for item in data["LIVE_PPLTN_STTS"][0]["FCST_PPLTN"]
                                  if datetime.strptime(item["FCST_TIME"], "%Y-%m-%d %H:%M") == input_time), None)
            if forecast_data is None:
                raise HTTPException(status_code=404, detail="Forecast data not found for the given time")
            result_data = {
                "area_nm" : closest_location,
                "area_congest_lvl": forecast_data["FCST_CONGEST_LVL"],
                "area_congest_msg" : message[forecast_data["FCST_CONGEST_LVL"]],
                "pre_inquiry_time": forecast_data['FCST_TIME']
            }

        return {"code": 200, "message": "혼잡도 데이터 조회에 성공하였습니다.", "data": result_data}
    except Exception as e:
        return {"code": 500, "message": str(e), "data": {}}


# 근처 혼잡하지 않은 핫스팟 조회
@app.get("/location/search/hot")
async def hot_search(place: str, congestion: str, input_time: datetime = Query(None)):
    df = pd.read_csv('../../data/landmark_final.csv')
    congestion_levels = list(message.keys())
    current_lat = df[df['랜드마크'] == place]['위도'].values[0]
    current_lon = df[df['랜드마크'] == place]['경도'].values[0]

    # 각 랜드마크까지의 거리 계산
    df['distance'] = df.apply(lambda row: haversine(current_lat, current_lon, row['위도'], row['경도']), axis=1)
    
    # 거리에 따라 데이터프레임 정렬 후 현재 위치 랜드마크 제외
    df_sorted = df[df['랜드마크'] != place].sort_values(by='distance')

    current_index = congestion_levels.index(congestion)
    if (current_index == 0) or (current_index == 1):
        return {"code": 201, "message": "혼잡 데이터를 찾지 않아도 됩니다."}
    # 혼잡하지 않은 랜드마크 찾기
    for index, row in df_sorted.iterrows():
        congestion_info = await get_congestion_info(row['랜드마크'], input_time)
        level = congestion_info['data']['area_congest_lvl']
        if congestion_levels.index(level) < current_index:
            result_date = {"area_nm": row['랜드마크'], "area_congest_lvl": level}
            return {"code": 200, "message" : "근처 혼잡하지 않은 지역 찾기에 성공했습니다." , "data" : result_date}
    
    return {"code": 400, "message": "혼잡하지 않은 지역 찾기에 실패했습니다."}


# 위치기반 이벤트 검색
@app.get("/location/search/event")
async def get_events(area_nm: str = Query(..., description="The area name to filter events")):
    query = {"AREA_NM": area_nm}
    projection = {"AREA_NM" : 1,"EVENT_STTS.EVENT_PERIOD": 1, "EVENT_STTS.EVENT_PLACE": 1, "EVENT_STTS.THUMBNAIL": 1, "EVENT_STTS.URL": 1, "_id": 0}
    try:
        data = mydb['congestion'].find_one(query, projection, sort=[('_id', -1)])
        if not data or len(data["EVENT_STTS"]) == 0:
            return {'code' : 404, 'message' : '이벤트 데이터가 없습니다.'}
        else : 
            return {'code' : 200, 'message' : '이벤트 데이터를 조회하는데 성공했습니다.', 'data' : data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    

@app.post("/get_data")
async def query_data(request: DataQueryData):
    base_url = "http://0.0.0.0:5001/data"
    params = request.dict(exclude_none=True)  # None 값 제외하고 딕셔너리 생성
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # 오류가 발생하면 예외를 발생
        data = response.json()
        if len(data) == 0:
            return {"code": 201, "message" : "상권 추정 매출 데이터가 없습니다.", "data": data}
        return {"code": 200, "message" : "상권 추정 매출 데이터 조회에 성공했습니다.", "data": data}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@app.post("/location/recommend/store")
async def location_recommend(request: LocationQuery):
    base_url = "http://0.0.0.0:5001/data"
    # 위치 정보를 먼저 조회
    lati, long = get_location(request.location)

    # 성별 정제
    gender_sales = f'{request.gender}_매출_금액'
    # 연령대 정제
    age_sales = f'연령대_{request.age}_매출_금액'

    # API에 전송할 파라미터 준비
    params = {
        "서비스_업종_코드_명": request.category,
        "기준_년분기_코드": request.quarter
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # 오류가 발생하면 예외를 발생
        all_data = response.json()
        if len(all_data) == 0:
            return {"code": 201, "message" : "상권 추정 매출 데이터가 없습니다.", "data": data}
        # 거리 계산
        
        for data in all_data:
            data['distance'] = haversine(lati, long, data['위도'], data['경도'])

        # 가장 가까운 10개 데이터 필터링
        closest_data = sorted(all_data, key=lambda x: x['distance'])[:10]
        
        # 성별 및 연령대별로 매출 금액이 높은 순으로 정렬
        highest_gender_sales = [{
                "상권_코드_명": data["상권_코드_명"],
                "서비스_업종_코드_명": data["서비스_업종_코드_명"],
                "기준_년분기_코드": data["기준_년분기_코드"],
                "자치구_코드_명": data["자치구_코드_명"],
                "행정동_코드_명": data["행정동_코드_명"],
                "sales": data['매출액'][gender_sales]
            } for data in closest_data]

        highest_age_sales = [{
                "상권_코드_명": data["상권_코드_명"],
                "서비스_업종_코드_명": data["서비스_업종_코드_명"],
                "기준_년분기_코드": data["기준_년분기_코드"],
                "자치구_코드_명": data["자치구_코드_명"],
                "행정동_코드_명": data["행정동_코드_명"],
                "sales": data['매출액'][age_sales]
            } for data in closest_data]
        
        return {"code": 200, "message" : "상권 추정 매출 데이터 조회에 성공했습니다.", "data": {"gender" : highest_gender_sales, "age" : highest_age_sales}}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@app.post("/location/recommend/category")
async def category_recommend(request: CateogoryQuery):
    base_url = "http://0.0.0.0:5001/data"
    # 위치 정보를 먼저 조회
    lati, long = get_location(request.location)

    df = pd.read_csv('../../data/only_store.csv', index_col=0)
    df['distance'] = df.apply(lambda row: haversine(lati, long, row['위도'], row['경도']), axis=1)
    df_sorted = df.sort_values(by='distance').head(100)

    all_data = [] 
    for store_code in df_sorted['상권_코드_명'].unique():
        params = {
            "상권_코드_명": store_code,
            "기준_년분기_코드": request.quarter
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            all_data.extend(data)  # 각 요청의 결과를 모아 리스트에 추가
        except requests.RequestException as e:
            continue  # 오류 발생 시 해당 상권 코드명에 대한 요청을 건너뛰고 계속 진행

   # 성별 정제
    gender_sales = f'{request.gender}_매출_금액'
    # 연령대 정제
    age_sales = f'연령대_{request.age}_매출_금액'

    sales_gender_summary = {}
    sales_age_summary = {}
    for item in all_data:
        service_type = item['서비스_업종_코드_명']
        if service_type in sales_gender_summary:
            sales_gender_summary[service_type] += item['매출액'][gender_sales]
            sales_age_summary[service_type] += item['매출액'][age_sales]
        else:
            sales_gender_summary[service_type] = item['매출액'][gender_sales]
            sales_age_summary[service_type] = item['매출액'][age_sales]

    sorted_sales_gender_summary = dict(sorted(sales_gender_summary.items(), key=lambda x: x[1], reverse=True))
    sorted_sales_age_summary = dict(sorted(sales_age_summary.items(), key=lambda x: x[1], reverse=True))

    return {"code": 200, "message" : "상권 추정 매출 데이터 조회에 성공했습니다.", "data": {"gender" : sorted_sales_gender_summary, "age" : sorted_sales_age_summary}}

