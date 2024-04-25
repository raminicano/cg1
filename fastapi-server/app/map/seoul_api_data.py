from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

SEOUL_API_KEY = os.getenv('SEOUL_API_KEY')

def get_congestion(location):
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_API_KEY}/json/citydata/1/2/{location}"
    response = requests.get(url)
    data = json.loads(response.text)
    return data