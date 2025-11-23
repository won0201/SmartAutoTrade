#Server.asset.py
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import FinanceDataReader as fdr
import logging

assets_router = APIRouter()

# CSV에서 자산 가져오기
@assets_router.get("/assets")
def get_assets():
    try:
        df = pd.read_csv(r"C:/Users/dbjin/DATA/assets_data.csv", encoding="utf-8-sig")
        return df[['Code', 'Name']].to_dict(orient="records")
    except Exception as e:
        logging.exception("Error in /assets API")
        return {"error": str(e)}

# 최초 실행 시 CSV 생성
def save_assets_csv():
    df = fdr.StockListing('KRX')
    df[['Code', 'Name']].to_csv(r"C:/Users/dbjin/DATA/assets_data.csv", index=False, encoding="utf-8-sig")
    print(f"저장 완료: {df.shape}")

save_assets_csv()

# uvicorn 실행용 main
#if __name__ == "__main__":

#    df = fdr.StockListing('KRX')
#    df[['Code', 'Name']].to_csv(r"C:\Users\dbjin\DATA\assets_data.csv", index=False, encoding="utf-8-sig")
#    df = pd.read_csv("assets_data.csv", encoding="utf-8-sig")

#    print(f"저장 완료: {df.shape}")

   #uvicorn.run(app, host="127.0.0.1", port=8083)


