import FinanceDataReader as fdr
import pandas as pd

if __name__ == "__main__":
    tickers = {
    "Samsung": "005930",
    "Hyundai": "005380",
    "SKHynix": "000660",
    "KaKao": "035720",
    "Naver": "035420",
}

# 기간
start = "2025-06-04"
end = "2025-08-21"

# 여러 종목 데이터 합치기
adjclose_data = pd.DataFrame()

for name, code in tickers.items():
    df = fdr.DataReader(code, start, end)[["Close"]]
    df.rename(columns={"Close": name}, inplace=True)
    if adjclose_data.empty:
        adjclose_data = df
    else:
        adjclose_data = adjclose_data.join(df, how="outer")

# CSV 저장
adjclose_data.to_csv(r"C:\Users\dbjin\DATA\Close.csv", encoding="utf-8-sig")

print(adjclose_data.head())
