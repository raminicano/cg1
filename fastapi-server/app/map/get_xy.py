from dotenv import load_dotenv
import os
import requests

# .env 파일에서 환경변수 로드
load_dotenv()

# 환경변수에서 API 키 가져오기
REST_API_KEY = os.getenv('REST_API_KEY')


def get_location(address):
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    headers = {
    "Authorization": f"KakaoAK {REST_API_KEY}"
    }
    response = requests.get(url, headers=headers, params={'query': address}).json()

    long = response['documents'][0]['x'] 
    lati = response['documents'][0]['y']
    return float(lati), float(long)
