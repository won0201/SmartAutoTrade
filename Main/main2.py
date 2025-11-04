# main2.py
# 이상탐지 API 서버 포트 다르게 실행 해야 함
from fastapi import FastAPI
import uvicorn
from Fraud_Detection_Model.FIGARCH_Estimation.API_RISK_SCORE import riskscore_router
from fastapi.middleware.cors import CORSMiddleware
from Fraud_Detection_Model.FIGARCH_Estimation.API_RISK_STATS import riskstats_router

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "FastAPI 서버가 정상적으로 작동 중입니다."}


origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(riskscore_router)

app.include_router(riskstats_router)
if __name__ == "__main__":
    uvicorn.run("main2:app", host="127.0.0.1", port=8085, reload=False)
