import pandas as pd
#import numpy as np
#import os
import FinanceDataReader as fdr
import numpy as np

# =====================================
# 1) 합성 데이터 생성 (다변량 t분포 형태로 상관 구조가 있는 수익률을 만든다.)
# =====================================
"""
    def generate_synthetic_returns(T: int = 1500, N: int = 5, seed: int = 42) -> pd.DataFrame:
    #Asset_1부터 Asset_5까지 합성 수익률 시계열 데이터 생성
"""

def generate_real_returns(
         tickers: dict = None,
        start: str = "2020-01-01",
        end: str = "2025-09-19"
) -> pd.DataFrame:

    if tickers is None:
            tickers = {
                "Samsung": "005930",  #삼성전자
                "Hyundai" : "005380",   #현대
                "SKHynix": "000660",   #SK하이닉스
                "KaKao":"035720",       #카카오
               "Naver": "035420"         #네이버
            }

    dfs = {}
    for name, code in tickers.items():
        df = fdr.DataReader(code, start=start, end=end)
        df["Return"]=np.log(df["Close"]).diff()
        dfs[name] = df[["Return"]].dropna()

     # 하나의 DataFrame으로 합치기
    returns = pd.concat(
           [df.rename(columns={"Return": name}) for name, df in dfs.items()],
            axis=1
        ).dropna()
    return returns

start = "2020-01-01"
end = "2025-09-19"

data = pd.DataFrame({
        "Samsung": fdr.DataReader("005930", start, end)["Close"],  # 삼성전자
        "Hyundai": fdr.DataReader("005380", start, end)["Close"],  # 현대
        "SKHynix": fdr.DataReader("000660", start, end)["Close"] , # SK하이닉스
        "KaKao": fdr.DataReader("035720", start, end)["Close"],  # KaKao
        "Naver": fdr.DataReader("035420", start, end)["Close"]  # Naver
      })

# === 2) 수익률 계산 (로그수익률) ===
#returns = np.log(data / data.shift(1)).dropna()

# === 3) CSV로 저장 ===
#returns.to_csv("real_returns.csv", index=True, index_label="Date")
#print("실제 5개의 자산 수익률 CSV 저장 완료:", returns.shape)

""""=== 실행 및 csv로 다운 ===
df = generate_synthetic_returns(T=1500, N=5, seed=42)

 프로젝트 루트 기준 절대 경로 생성
BASE_DIR  os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ile_path = os.path.join(BASE_DIR, "data", "synthetic_returns.csv")

print(os.getcwd())
"""

if __name__ == "__main__":
    returns = generate_real_returns()

    # 결측치 처리 코드
    data = np.array(["1.2", "3.4", "abc", None])  # dtype('O')
    cleaned = np.array([float(x) if x not in [None, "abc"] else np.nan for x in data])

    print("5개 종목 수익률 데이터 샘플")
    print(returns.head())  # 앞부분 5행 출력

    print("\n DataFrame 정보")
    print(returns.info())  # 데이터프레임 구조 확인
    print(" 포함된 종목 목록:", returns.columns.tolist())
