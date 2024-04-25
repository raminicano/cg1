import numpy as np
import pandas as pd

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
