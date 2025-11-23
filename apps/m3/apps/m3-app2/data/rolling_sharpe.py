import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import os

def Sharpratio(tickers, start, end, cd_csv_path, output_file, window=60):
    """
    1. 종목 종가 데이터 불러오기
    2. 일간 수익률 계산
    3. 무위험 금리(CD91) 불러오기
    4. 60일 롤링 샤프비율 계산
    5. CSV로 저장
    """
    # ============================
    # 1. 종목 종가 불러오기
    # ============================
    price_data = {}
    for name, code in tickers.items():
        df = fdr.DataReader(code, start, end)[["Close"]].rename(columns={"Close": name})
        price_data[name] = df
    df_prices = pd.concat(price_data.values(), axis=1)

    # ============================
    # 2. 일간 수익률 계산
    # ============================
    df_returns = df_prices.pct_change().dropna()

    # ============================
    # 3. 무위험 금리 (CD91) => 91일 양도성예금증서 금리
    # ============================
    df_cd = pd.read_csv(cd_csv_path)
    df_cd = df_cd.rename(columns={"거래일": "Date", "CD수익률": "RiskFree"})
    df_cd["Date"] = pd.to_datetime(df_cd["Date"], format="%Y-%m-%d")
    df_cd = df_cd.sort_values(by="Date")
    df_cd.set_index("Date", inplace=True)
    df_cd["RiskFree"] = df_cd["RiskFree"] / 100 / 252  # 연율 → 일별 수익률

    # ============================
    # 4. 수익률과 금리 align
    # ============================
    df_returns_reset = df_returns.reset_index().rename(columns={'index': 'Date'})
    df_all = pd.merge(df_returns_reset, df_cd.reset_index(), on="Date", how="inner")
    df_all.set_index("Date", inplace=True)

    df_cd = df_cd.reindex(df_returns.index).ffill() # 이전값으로 채움
    df_all = df_returns.join(df_cd["RiskFree"], how="left")

    # ============================
    # 5. 초과수익률 및 60일 롤링 샤프비율 계산
    # ============================
    excess_returns = df_all[tickers.keys()].sub(df_all["RiskFree"], axis=0)
    df_sharpe_rolling = pd.DataFrame(index=excess_returns.index)
    for col in excess_returns.columns:
        rolling_mean = excess_returns[col].rolling(window).mean()
        rolling_std = excess_returns[col].rolling(window).std().replace(0, np.nan)
        df_sharpe_rolling[col] = rolling_mean / rolling_std

    # ============================
    # 6. csv로 저장 (롤링 샤프비율만)
    # ============================
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df_sharpe_rolling.to_csv(output_file, index=True, encoding="utf-8-sig")
    print(f"CSV 파일이 저장되었습니다: {output_file}")

    return df_sharpe_rolling
# ============================
# 실행 예시
# ============================
if __name__ == "__main__":
    tickers = {
        "Samsung": "005930",
        "Hyundai": "005380",
        "SKHynix": "000660",
         "KaKao": "035720",
         "Naver": "035420",
    }
    start = "2025-01-01"
    end = "2025-09-18"
    cd_csv_path = r"C:\Users\dbjin\DATA\CD91_25.csv"  # ECOS에서 다운로드한 CD91 CSV
    output_file = r"C:\Users\dbjin\DATA\rolling_sharpe.csv"

    df_sharpe = Sharpratio(
        tickers=tickers,
        start=start,
        end=end,
        cd_csv_path=cd_csv_path,
        output_file=output_file,
        window=60
    )
    print(df_sharpe.head())
    print(df_sharpe.tail())