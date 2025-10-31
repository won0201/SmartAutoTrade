# config.py

import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# --- API 설정 (환경 변수에서 불러오기) ---
KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")

# (중요) 키가 없는 경우 봇이 중단되도록 확인
if not KIS_APP_KEY or not KIS_APP_SECRET or not KIS_ACCOUNT_NO:
    raise ValueError("필수 API 정보(KEY, SECRET, ACCOUNT_NO)가 .env 파일에 설정되지 않았습니다.")


# --- 모델 및 데이터 경로 (실제 파일 기준) ---
ARTIFACTS_DIR = "artifacts_golden"
SCALER_PATH = f"{ARTIFACTS_DIR}/scaler.pkl"

# Colab 12단계 챔피언 모델 경로
DL_MODEL_PATH = f"{ARTIFACTS_DIR}/CHAMPION_MODEL.keras" 

# --- 데이터 및 모델링 설정 (Colab 2-C, 4, 6단계 기준) ---
SEQUENCE_LENGTH = 60  # Colab 6단계에서 설정한 시퀀스 길이

# Colab 2-C단계에서 선별된 Top 15 골든 피처
GOLDEN_FEATURES = [
    'Price', 'MA5', 'NASDAQ', 'USD_KRW', 'MA20', 'Bollinger_Upper',
    'Bollinger_Lower', 'MA60', 'MA_Ratio_20', 'STOCHk_14_3_3', 'MA120',
    'VIX', 'Volatility_20D', 'Month', 'RSI'
]

# Colab 4단계 ARIMA 설정
ARIMA_ORDER = (2, 1, 0)
ARIMA_FEATURE_NAME = 'ARIMA_Residual'

# Colab 2-B단계 외부 지표 티커
EXOG_TICKERS = {
    '^GSPC': 'SP500',
    '^IXIC': 'NASDAQ',
    '^VIX': 'VIX',
    'USDKRW=X': 'USD_KRW',
    '^TNX': 'US_10Y_Treasury',
    'CL=F': 'WTI_Oil'
}

print("config.py 로드 완료: 환경 변수에서 API 키를 성공적으로 불러왔습니다.")