# main2.py
# 이상탐지 API 서버 포트 다르게 실행 해야 함
from fastapi import FastAPI
import uvicorn

from Fraud_Detection_Model.FIGARCH_Estimation.API_RISK_SCORE import riskscore_router
from Fraud_Detection_Model.FIGARCH_Estimation.API_RISK_STATS import riskstats_router

from fastapi.middleware.cors import CORSMiddleware

from Fraud_Detection_Model.SVM_Classification.SVM_ISOFOREST import svm_plot_router
from Fraud_Detection_Model.ANN_Classification.ANN_ISOFOREST import ann_plot_router
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "FastAPI 서버가 정상적으로 작동 중입니다."}


origins = ["http://localhost:5173","http://localhost:8080"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],     # GET, POST 등 모든 메소드 허용
    allow_headers=["*"],     # 모든 헤더 허용
)


app.include_router(riskscore_router)

app.include_router(riskstats_router)

app.include_router(svm_plot_router, prefix="/svm")

app.include_router(ann_plot_router, prefix="/ann")


if __name__ == "__main__":
    uvicorn.run("main2:app", host="0.0.0.0", port=8085, reload=False)
