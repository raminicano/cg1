from sqlalchemy import Column, String, DateTime, Integer, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Congestion(Base):
    __tablename__ = 'congestion'
    area_nm = Column(String(255), primary_key=True)
    inquiry_time = Column(DateTime, primary_key=True)
    area_congest_lvl = Column(String(255))
    area_congest_msg = Column(String(255))


class Event(Base):
    __tablename__ = 'event'
    area_nm = Column(String(255), primary_key=True)
    event_period = Column(String(255))
    event_place = Column(String(255))
    thumbnail = Column(String(511))
    url = Column(String(511), primary_key=True)


class Location(Base):
    __tablename__ = 'location'
    district_code = Column(String(255), primary_key=True)
    service_code = Column(String(255), primary_key=True)
    quarter = Column(Integer, primary_key=True)
    gu_code = Column(String(255))
    dong_code = Column(String(255))
    male = Column(Float)
    female = Column(Float)
    age_10 = Column(Float)
    age_20 = Column(Float)
    age_30 = Column(Float)
    age_40 = Column(Float)
    age_50 = Column(Float)
    age_60 = Column(Float)
    

class Store(Base):
    __tablename__ = 'store'
    상권_구분_코드 = Column(String(255))
    상권_구분_코드_명 = Column(String(255))
    상권_코드 = Column(String(255), primary_key=True)
    상권_코드_명 = Column(String(255))
    엑스좌표_값 = Column(Integer)
    와이좌표_값 = Column(Integer)
    자치구_코드 = Column(String(255))
    자치구_코드_명 = Column(String(255))
    행정동_코드 = Column(String(255))
    행정동_코드_명 = Column(String(255))
    영역_면적 = Column(Float)
    경도 = Column(Float)
    위도 = Column(Float)


class Landmark(Base):
    __tablename__ = 'landmark'
    구 = Column(String(255))
    동 = Column(String(255))
    랜드마크 = Column(String(255), primary_key=True)
    위도 = Column(Float)
    경도 = Column(Float)