# data_processor.py
import pandas as pd
import yfinance as yf
import numpy as np
import joblib
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime, timedelta
import os
import warnings
import traceback # 오류 추적을 위해 추가

# ta 라이브러리 (Colab 1단계에서 설치)
try:
    from ta.trend import SMAIndicator, MACD, CCIIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
except ImportError:
    print("❌ 'ta' 라이브러리가 필요합니다. 'pip install ta'를 실행하세요.")
    exit()

from sklearn.preprocessing import MinMaxScaler

# config.py에서 설정값 가져오기
from config import (
    GOLDEN_FEATURES, ARIMA_ORDER, ARIMA_FEATURE_NAME, EXOG_TICKERS,
    SCALER_PATH, ARTIFACTS_DIR, SEQUENCE_LENGTH
)

warnings.filterwarnings("ignore")


def _calculate_technical_indicators(df):
    """Colab 2단계: 기술적 지표 계산 (ta 라이브러리)"""
    df_ta = df.copy()
    df_ta["MA5"]   = SMAIndicator(close=df_ta["Close"], window=5).sma_indicator()
    df_ta["MA20"]  = SMAIndicator(close=df_ta["Close"], window=20).sma_indicator()
    df_ta["MA60"]  = SMAIndicator(close=df_ta["Close"], window=60).sma_indicator()
    df_ta["MA120"] = SMAIndicator(close=df_ta["Close"], window=120).sma_indicator()

    _macd = MACD(close=df_ta["Close"], window_slow=26, window_fast=12, window_sign=9)
    df_ta["MACD"]        = _macd.macd()
    df_ta["MACD_Signal"] = _macd.macd_signal()

    df_ta["RSI"] = RSIIndicator(close=df_ta["Close"], window=14).rsi()

    _stoch = StochasticOscillator(high=df_ta["High"], low=df_ta["Low"], close=df_ta["Close"], window=14, smooth_window=3)
    df_ta["STOCHk_14_3_3"] = _stoch.stoch()
    df_ta["STOCHd_14_3_3"] = _stoch.stoch_signal()

    df_ta["CCI"] = CCIIndicator(high=df_ta["High"], low=df_ta["Low"], close=df_ta["Close"], window=20).cci()

    _bb = BollingerBands(close=df_ta["Close"], window=20, window_dev=2)
    df_ta["Bollinger_Upper"] = _bb.bollinger_hband()
    df_ta["Bollinger_Lower"] = _bb.bollinger_lband()

    df_ta["ATR"] = AverageTrueRange(high=df_ta["High"], low=df_ta["Low"], close=df_ta["Close"], window=14).average_true_range()

    df_ta["Volume"] = df_ta["Volume"].astype(float)
    return df_ta

def _add_custom_and_time_features(df):
    """Colab 2-B단계: 커스텀 및 시간 피처 추가"""
    df_custom = df.copy()
    # 시간 기반
    df_custom['Month'] = df_custom.index.month
    df_custom['DayOfWeek'] = df_custom.index.dayofweek
    df_custom['Quarter'] = df_custom.index.quarter

    # 커스텀 피처
    df_custom['Volatility_20D'] = df_custom['Price'].pct_change().rolling(window=20).std() * 100
    # MA20이 먼저 계산되어 있어야 함
    if 'MA20' in df_custom.columns:
        df_custom['MA_Ratio_20'] = (df_custom['Price'] / df_custom['MA20'] - 1) * 100
    else:
        # MA20이 없는 경우 (오류 방지)
        temp_ma20 = SMAIndicator(close=df_custom["Close"], window=20).sma_indicator()
        df_custom['MA_Ratio_20'] = (df_custom['Price'] / temp_ma20 - 1) * 100
        
    return df_custom

def _add_arima_residuals(df, price_col='Price'):
    """Colab 4단계: ARIMA 잔차 피처 추가"""
    df_arima = df.copy()
    try:
        model = ARIMA(df_arima[price_col].dropna(), order=ARIMA_ORDER)
        model_fit = model.fit()
        # 원본 길이에 맞게 잔차를 재인덱싱
        df_arima[ARIMA_FEATURE_NAME] = model_fit.resid.reindex(df_arima.index)
    except Exception as e:
        print(f"⚠️ ARIMA 모델 학습 실패 (데이터 부족 등): {e}. 잔차를 0으로 채웁니다.")
        df_arima[ARIMA_FEATURE_NAME] = 0.0
    return df_arima

def preprocess_for_startup(start_date="2015-01-01"):
    """
    봇 시작 시 호출되는 함수.
    Colab 2, 2-B, 4단계의 모든 전처리 과정을 수행합니다.
    """
    print("1. KOSPI 200 원본 데이터 다운로드 중...")
    try:
        # (날짜 형식 오류 수정)
        end_date_obj = datetime.now() + timedelta(days=1)
        df = yf.download("^KS200", start=start_date, end=end_date_obj, auto_adjust=False, progress=False)

        if df.empty:
            raise RuntimeError("yfinance에서 KOSPI 200 데이터를 다운로드하지 못했습니다.")
        
        # (MultiIndex 오류 수정)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(-1)
            
        df.columns = [c.capitalize() for c in df.columns]
        df = df[["Open","High","Low","Close","Volume"]]
        df["Price"] = df["Close"]
    except Exception as e:
        raise RuntimeError(f"❌ KOSPI 200 데이터 다운로드 실패: {e}")

    print("2. 외부 경제 지표 다운로드 중 (NASDAQ, VIX 등)...")
    try:
        end_date_obj = datetime.now() + timedelta(days=1) # (날짜 형식 오류 수정)
        exog_data_raw = yf.download(list(EXOG_TICKERS.keys()), start=start_date, end=end_date_obj, progress=False)
        
        if not exog_data_raw.empty:
            exog_data = exog_data_raw['Close']
            
            if isinstance(exog_data.columns, pd.MultiIndex): # (MultiIndex 오류 수정)
                 exog_data.columns = exog_data.columns.droplevel(-1)
                 
            exog_data.rename(columns=EXOG_TICKERS, inplace=True)
            
            df = df.merge(exog_data, left_index=True, right_index=True, how='left')
            df.ffill(inplace=True)
        else:
            print("⚠️ 외부 경제 지표 다운로드 실패 (데이터 비어 있음). ffill로 계속 진행")
            
    except Exception as e:
        print(f"⚠️ 외부 지표 다운로드/병합 실패: {e}. (ffill로 계속 진행)")

    print("3. 기술적 지표 및 커스텀 피처 계산 중...")
    df = _calculate_technical_indicators(df)
    df = _add_custom_and_time_features(df)

    # 4. Colab 2-C: 골든 피처 선택
    features_to_keep = [f for f in GOLDEN_FEATURES if f in df.columns]
    missing_features = set(GOLDEN_FEATURES) - set(features_to_keep)
    if missing_features:
        print(f"⚠️ 일부 골든 피처를 계산/로드하지 못했습니다. 누락: {missing_features}")

    df_golden = df[features_to_keep].copy()

    print("5. ARIMA 잔차 피처 추가 중 (시간 소요)...")
    df_golden_arima = _add_arima_residuals(df_golden.dropna(subset=['Price']), price_col='Price')

    # 6. 최종 피처 목록 (모델 입력 순서)
    final_feature_list = GOLDEN_FEATURES + [ARIMA_FEATURE_NAME]
    processed_df = df_golden_arima[final_feature_list].dropna()

    print("7. 스케일러 학습 및 저장 중...")
    scaler = MinMaxScaler()
    scaler.fit(processed_df.values)

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    joblib.dump(scaler, SCALER_PATH)
    print(f"✅ 스케일러 저장 완료: {SCALER_PATH}")

    print("✅ 데이터 전처리 완료! 최종 Shape:", processed_df.shape)
    return processed_df, scaler

def update_for_new_tick(processed_df: pd.DataFrame, price: float):
    """
    실시간 틱 수신 시 호출되는 함수.
    새 가격으로 마지막 행의 피처를 '빠르게' 업데이트(근사)합니다.
    """
    last_row_values = processed_df.iloc[-1].values
    
    # ==========================================================
    # ★★★ [버그 수정] 인덱스를 날짜가 아닌 정수로 사용 ★★★
    # ==========================================================
    # 기존) name=datetime.now() -> 인덱스 꼬임(NaN) 유발
    # 수정) name=None -> 0, 1, 2... 정수 인덱스 사용
    new_row = pd.Series(last_row_values, index=processed_df.columns)
    # ==========================================================

    new_row['Price'] = price
    
    # [100% 신뢰도 버그 수정]
    # .values.tolist()로 값만 가져온 뒤, 새 Series를 만들어 계산
    price_values = processed_df['Price'].values.tolist() + [price]
    prices = pd.Series(price_values) # [0, 1, 2...] 인덱스로 생성
    
    # 이제 prices.pct_change().rolling().std()가 정상 작동
    
    if 'MA5' in new_row: new_row['MA5'] = prices.rolling(5).mean().iloc[-1]
    if 'MA20' in new_row: new_row['MA20'] = prices.rolling(20).mean().iloc[-1]
    if 'MA60' in new_row: new_row['MA60'] = prices.rolling(60).mean().iloc[-1]
    if 'MA120' in new_row: new_row['MA120'] = prices.rolling(120).mean().iloc[-1]

    if 'RSI' in new_row:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
        rs = gain / (loss + 1e-9)
        new_row['RSI'] = 100 - (100 / (1 + rs))

    if 'Bollinger_Upper' in new_row:
        ma20 = new_row['MA20']
        std20 = prices.rolling(20).std().iloc[-1]
        new_row['Bollinger_Upper'] = ma20 + 2 * std20
        new_row['Bollinger_Lower'] = ma20 - 2 * std20

    if 'STOCHk_14_3_3' in new_row:
        low14 = prices.rolling(14).min().iloc[-1]
        high14 = prices.rolling(14).max().iloc[-1]
        k = 100 * (price - low14) / (high14 - low14 + 1e-9)
        new_row['STOCHk_14_3_3'] = k

    if 'MA_Ratio_20' in new_row:
        new_row['MA_Ratio_20'] = (new_row['Price'] / new_row['MA20'] - 1) * 100

    if 'Volatility_20D' in new_row:
        # [중요] 변동성을 한 곳에서만 계산 (pct_change std * 100)
        new_row['Volatility_20D'] = prices.pct_change().rolling(20).std().iloc[-1] * 100

    # (외부/ARIMA 피처는 ffill)

    # [버그 수정] 정수 인덱스로 concat
    updated_df = pd.concat([processed_df, new_row.to_frame().T], ignore_index=True)
    return updated_df


if __name__ == "__main__":
    # data_processor.py를 직접 실행하여 전처리 및 스케일러 생성을 테스트
    print("🚀 데이터 프로세서 단독 실행 테스트 (초기 전처리)...")
    try:
        df, sc = preprocess_for_startup()
        print("\n--- 최종 데이터 샘플 ---")
        print(df.tail())
        print(f"\n✅ 스케일러 저장 확인: {SCALER_PATH}")
        print("\n🎉 초기 전처리 및 스케일러 생성을 성공적으로 완료했습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        traceback.print_exc()