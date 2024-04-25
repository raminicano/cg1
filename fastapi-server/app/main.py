from fastapi import FastAPI
import httpx
import os


app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello" : "World"}


@app.get("/get-specific-record")
async def get_specific_record():
    # json-server의 주소
    url = "http://0.0.0.0:5000/data"
    
    # 비동기 HTTP 클라이언트 생성
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
        
        # 특정 상권 코드를 가진 레코드 찾기
        for record in data:
            if record.get("상권_코드") == 3120068:
                return record
        return {"message": "Record not found"}


if __name__ == '__main__' :
    uvicorn.run(app, host="0.0.0.0", port=3000)
    