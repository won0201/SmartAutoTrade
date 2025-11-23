from fastapi import FastAPI,APIRouter
import pandas as pd

riskstats_router = APIRouter()

@riskstats_router.get("/risk/stats")
async def get_risk_table():
    df = pd.read_csv(r"C:\Users\dbjin\DATA\Zscore_summary_stats.csv")
    return df.to_dict(orient="records")

