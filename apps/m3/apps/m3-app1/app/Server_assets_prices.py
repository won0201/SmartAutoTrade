#Server_assets_prices.py
from fastapi import APIRouter
import FinanceDataReader as fdr
import pandas as pd
import os

# 라우터 정의
assets_prices_router = APIRouter(prefix="/assets", tags=["Assets"])

# -----------------------------
# 자산 리스트 (한국 주요 종목)
# -----------------------------
START_DATE = "2020-01-01"
CSV_PATH = r"C:\Users\dbjin\DATA\assets_prices.csv"

ASSETS = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "네이버": "035420",
    "카카오": "035720",
    "현대차": "005380"
}

def fetch_assets_to_csv(path: str) -> pd.DataFrame | None:
    all_data = []
    print("\n[데이터 수집 시작] -----------------------------")
    for name, code in ASSETS.items():
        try:
            print(f" {name} ({code}) 데이터 수집 중...")
            df = fdr.DataReader(code, start=START_DATE)
            if df is None or df.empty:
                print(f" {name} 데이터 없음")
                continue
            df = df.reset_index()
            df["Name"] = name
            df["Code"] = code
            df = df[["Date", "Name", "Code", "Open", "High", "Low", "Close", "Volume"]]
            all_data.append(df)
        except Exception as e:
            print(f" {name} ({code}) 수집 실패: {e}")

    if not all_data:
        print("수집된 데이터가 없습니다.")
        return None

    df_all = pd.concat(all_data, ignore_index=True)
    df_all.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[완료] {len(df_all)}건 저장됨 → {os.path.abspath(path)}\n")
    return df_all

# -----------------------------
# API: /asset/prices
# -----------------------------
# API: 최근 30일 자산 가격 조회
@assets_prices_router.get("/prices")
def get_asset_prices():
    try:
        if not os.path.exists(CSV_PATH):
            print("[CSV 없음] 새로 생성 중...")
            df = fetch_assets_to_csv(CSV_PATH)
        else:
            print("[CSV 있음] 파일 읽는 중...")
            df = pd.read_csv(CSV_PATH)

        df["Date"] = pd.to_datetime(df["Date"])
        recent = df[df["Date"] >= pd.Timestamp.today() - pd.DateOffset(days=30)]

        if not isinstance(recent, pd.DataFrame):
            return {"error": "데이터 형식 오류: recent는 DataFrame이 아닙니다."}

        print(f"[응답 준비 완료] {len(recent)}건 반환")
        return recent.to_dict(orient="records")

    except Exception as e:
        print("[에러 발생]", e)
        return {"error": str(e)}

# -----------------------------
# 실행
# -----------------------------
#if __name__ == "__main__":
    df = fetch_assets_to_csv(CSV_PATH)
    csv_path = r"C:\Users\dbjin\DATA\assets_prices.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
