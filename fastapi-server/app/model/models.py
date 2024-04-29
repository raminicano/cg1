from pydantic import BaseModel

class DataQueryData(BaseModel):
    상권_코드_명: str = None
    서비스_업종_코드_명: str = None
    기준_년분기_코드: str = None
    자치구_코드_명: str = None
    행정동_코드_명: str = None
    경도: float = None
    위도: float = None

class LocationQuery(BaseModel):
    location: str
    category: str
    gender: str
    age: int
    quarter: int



