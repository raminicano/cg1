from fastapi import APIRouter, HTTPException
from typing import Any
import requests
import pandas as pd
from map.get_xy import get_location

router = APIRouter()

@router.get("/congestion/")
async def fetch_congestion_data(address: str) -> Any:
    try:
        latitude, longitude = get_location(address)
        df = pd.read_csv('./data/landmark_final.csv')
        df['distance'] = df.apply(lambda row: haversine(latitude, longitude, row['위도'], row['경도']), axis=1)
        closest_location = df.loc[df['distance'].idxmin()]['랜드마크']
        api_key = os.getenv('SEOUL_API_KEY')
        url = f"http://openapi.seoul.go.kr:8088/{api_key}/json/citydata/1/2/{closest_location}"
        response = requests.get(url)
        data = response.json()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
