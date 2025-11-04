#main.py
#메인 API 서버 실행
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from API_optimize_plot import optimize_router
from Fraud_Detection_Model.SVM_Classification.API_plot_es import es_cutoff_router
from app.Server_assets import assets_router
from app.Server_assets_prices import fetch_assets_to_csv, assets_prices_router
from contextlib import asynccontextmanager

CSV_PATH = r"C:\Users\dbjin\DATA\assets_prices.csv"

# Lifespan 이벤트 정의
@asynccontextmanager
async def lifespan(app: FastAPI):
    fetch_assets_to_csv(CSV_PATH)
    print("[데이터 수집 완료]")
    yield
    print("서버 종료")

# FastAPI 앱 생성 시 lifespan 지정
app = FastAPI(lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(assets_router)

app.include_router(assets_prices_router)

app.include_router(optimize_router)

app.include_router(es_cutoff_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=False)