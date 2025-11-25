"""
SIGMA A 프로젝트 - 실시간 데이터 전처리 모듈
(단순 버전, scaler.pkl 완전 무시)

- 학습 당시 feature 수 = 16개 구성 유지
- SCALER 파일을 사용하지 않고, 원시 값 그대로 모델에 넣는 버전
"""

from __future__ import annotations

import os
from collections import deque
from typing import Deque

import numpy as np
import pandas as pd

from .config import SEQ_LEN

# ------------------------------------------------------------
# 피처 생성 함수 (16개)
# ------------------------------------------------------------
def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    학습 당시 사용했던 16개 feature를 동일하게 생성.
    df: index=datetime, columns=[open, high, low, close, volume]
    """

    feat = pd.DataFrame(index=df.index)

    # 기본 가격
    feat["close"] = df["close"]
    feat["open"] = df["open"]
    feat["high"] = df["high"]
    feat["low"] = df["low"]
    feat["volume"] = df["volume"]

    # 파생 피처
    feat["change"] = df["close"].pct_change().fillna(0)
    feat["volatility"] = (df["high"] - df["low"]).fillna(0)
    feat["return_5"] = df["close"].pct_change(5).fillna(0)
    feat["return_10"] = df["close"].pct_change(10).fillna(0)

    # rolling 평균 (FutureWarning 없애려고 bfill() 사용)
    feat["ma_5"] = df["close"].rolling(5).mean().bfill()
    feat["ma_10"] = df["close"].rolling(10).mean().bfill()
    feat["ma_20"] = df["close"].rolling(20).mean().bfill()

    feat["std_5"] = df["close"].rolling(5).std().fillna(0)
    feat["std_10"] = df["close"].rolling(10).std().fillna(0)

    # RSI 14
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    rs = (up.rolling(14).mean() / down.rolling(14).mean()).replace(
        [np.inf, -np.inf], 0
    ).fillna(0)
    feat["rsi_14"] = 100 - 100 / (1 + rs)

    # 실시간에는 VIX 사용 불가 → 스케일된 0 값 사용
    feat["vix_scaled"] = 0.0

    # 최종 16개 feature 유지
    return feat


# ------------------------------------------------------------
# 실시간 데이터 누적 & 전처리기
# ------------------------------------------------------------
class LiveDataProcessor:
    """
    실시간 가격 시계열을 받아서 (1, SEQ_LEN, 16) 형태의 모델 입력 생성
    """

    def __init__(self):
        # (필요하면 나중에 활용할 수 있는 buffer, 지금은 df가 메인)
        self.buffer: Deque[float] = deque(maxlen=SEQ_LEN)
        self.df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    def update(self, price: float) -> np.ndarray:
        """
        실시간 가격 1개 받아서 → 피처 16개 생성 → window → (1, SEQ_LEN, 16) 반환
        """

        new_row = {
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 0.0,   # 실시간에선 volume 사용 어려움 → 0 처리
        }
        self.df.loc[len(self.df)] = new_row

        # 최소 window 확보
        if len(self.df) < SEQ_LEN:
            raise RuntimeError(f"데이터 부족: {len(self.df)} / {SEQ_LEN}")

        # 최근 SEQ_LEN 구간만 유지
        df_tail = self.df.tail(SEQ_LEN)

        # feature 16개 생성
        feat_df = make_features(df_tail)

        # 결측치 보완
        feat_df = feat_df.ffill().bfill()

        # ndarray 변환
        X = feat_df.values.astype(float)

        # 🔥 scaler 전혀 사용 안 함 (원시 값 그대로)
        X_scaled = X

        # (SEQ_LEN, 16) → (1, SEQ_LEN, 16)
        return np.expand_dims(X_scaled, axis=0)


# ------------------------------------------------------------
# load_market_data() - snapshot 용 Fallback 데이터 로더
# ------------------------------------------------------------

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts_golden")
CSV_PATH = os.path.join(ARTIFACT_DIR, "empirical_backtest.csv")
NPZ_PATH = os.path.join(ARTIFACT_DIR, "step6_data.npz")


def load_market_data() -> pd.DataFrame:
    """
    실시간 또는 fallback 데이터를 반환.
    반환값(df)은 반드시 columns=[open, high, low, close, volume] 형태.

    여기서는 snapshot 용으로 사용(랜딩 페이지 지표 등),
    실시간 스트림은 LiveDataProcessor.update() 를 사용.
    """

    # ---------------------------------------------------------
    # 1) CSV fallback
    # ---------------------------------------------------------
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            # 필요한 만큼 뒤에서 자르기
            if len(df) >= SEQ_LEN:
                df = df.tail(SEQ_LEN)
            df = df[["open", "high", "low", "close", "volume"]]
            print("[data_processor] CSV fallback 사용")
            return df
        except Exception as e:
            print(f"[data_processor] ⚠️ CSV 로드 실패: {e}")

    # ---------------------------------------------------------
    # 2) NPZ fallback
    # ---------------------------------------------------------
    if os.path.exists(NPZ_PATH):
        try:
            npz = np.load(NPZ_PATH)
            arr = npz["X"]  # (N, 16) 또는 (N, seq, feat) 형식일 수 있음

            # 여기서는 단순하게 첫 feature를 close 처럼 사용
            if arr.ndim == 3:
                # (N, seq, feat) 인 경우 → 마지막 시퀀스의 첫 feature 사용
                close = arr[-1, :, 0]
            else:
                # (N, feat) 인 경우 → 전 구간 close 처럼 사용
                close = arr[:, 0]

            df = pd.DataFrame(
                {
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "volume": np.zeros_like(close),
                }
            )

            if len(df) >= SEQ_LEN:
                df = df.tail(SEQ_LEN)

            print("[data_processor] NPZ fallback 사용")
            return df
        except Exception as e:
            print(f"[data_processor] ⚠️ NPZ 로드 실패: {e}")

    # ---------------------------------------------------------
    # 3) 최종 fallback → 안전 dummy 데이터
    # ---------------------------------------------------------
    print("[data_processor] ❗ 모든 로드 실패 → dummy 데이터 사용")
    df = pd.DataFrame(
        [
            {
                "open": 300.0,
                "high": 300.0,
                "low": 300.0,
                "close": 300.0,
                "volume": 0.0,
            }
        ]
    )

    return df
