import os
import requests
import json
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
secret_file = os.path.join(BASE_DIR, '../secret.json')

with open(secret_file) as f:
    secrets = json.loads(f.read())

def get_secret(setting, secrets=secrets):
    try:
        return secrets[setting]
    except KeyError:
        errorMsg = "Set the {} environment variable.".format(setting)
        return errorMsg

REST_API_KEY = get_secret("REST_API_KEY")


def get_location(address):
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    headers = {
    "Authorization": f"KakaoAK {REST_API_KEY}"
    }
    response = requests.get(url, headers=headers, params={'query': address}).json()

    long = response['documents'][0]['x'] 
    lati = response['documents'][0]['y']
    return float(lati), float(long)



def haversine(lat1, lon1, lat2, lon2):
    # 모든 위도 경도는 라디안 단위로 변환
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # 위도와 경도 차이
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # 허버사인 공식 사용
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    # 6,371km는 지구의 반지름
    km = 6371 * c
    return km


def fetch_congestion_data(address: str):
    latitude, longitude = get_location(address)
    df = pd.read_csv('../../data/landmark_final.csv')
    df['distance'] = df.apply(lambda row: haversine(latitude, longitude, row['위도'], row['경도']), axis=1)
    closest_location = df.loc[df['distance'].idxmin()]['랜드마크']
    
    return closest_location
