"""
SIGMA A 프로젝트 공통 설정 모듈

- 경로/파일 위치
- 시퀀스 길이, 심볼 이름
- KIS API 및 데모 모드 설정

이 파일만 수정해도 나머지 모듈들이 자동으로 따라오도록 설계돼 있다.
"""

from pathlib import Path
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


# === 기본 경로 설정 =====================================================

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = BASE_DIR / "artifacts_golden"

MARKET_DATA_PATH = ARTIFACTS_DIR / "market_data.csv"
STEP6_PATH = ARTIFACTS_DIR / "step6_data.npz"
SCALER_PATH = ARTIFACTS_DIR / "scaler.pkl"
EMPIRICAL_BACKTEST_PATH = ARTIFACTS_DIR / "empirical_backtest.csv"

MODEL_WEIGHTS = {
    "gru_attention_reg":      ARTIFACTS_DIR / "tmp_gru_attention_reg.weights.h5",
    "lstm_attention_reg":     ARTIFACTS_DIR / "tmp_lstm_attention_reg.weights.h5",
    "transformer_reg":        ARTIFACTS_DIR / "tmp_transformer_reg.weights.h5",
    "tcn_reg":                ARTIFACTS_DIR / "tmp_tcn_reg.weights.h5",
    "patchtst_like_reg":      ARTIFACTS_DIR / "tmp_patchtst_like_reg.weights.h5",
    "tft_lite_reg":           ARTIFACTS_DIR / "tmp_tft_lite_reg.weights.h5",
    "attn_lstm_cnn_reg":      ARTIFACTS_DIR / "tmp_attn_lstm_cnn_reg.weights.h5",
    "champion_model": "app/artifacts_golden/CHAMPION_MODEL.keras",

}

CHAMPION_DL_MODEL_PATH = ARTIFACTS_DIR / "CHAMPION_MODEL.keras"


# === 시계열 / 심볼 관련 설정 ============================================

SEQUENCE_LENGTH: int = 60
SEQ_LEN: int = SEQUENCE_LENGTH
N_FEATURES: int = 16

INTERNAL_SYMBOL: str = "KOSPI200"
YFINANCE_SYMBOL: str = "^KS200"


# === KIS API / 데모 모드 설정 ===========================================

USE_KIS_API: bool = os.getenv("USE_KIS_API", "false").lower() == "true"

KIS_APP_KEY: str | None = os.getenv("KIS_APP_KEY", "")
KIS_APP_SECRET: str | None = os.getenv("KIS_APP_SECRET", "")
KIS_ACCOUNT_NO: str | None = os.getenv("KIS_ACCOUNT_NO", "")

KIS_BASE_URL: str = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")
KIS_WS_URL: str   = os.getenv("KIS_WS_URL",   "wss://openapi.koreainvestment.com:9443")


# === 신호/신뢰도 관련 설정 ==============================================

BULL_THRESHOLD: float = 0.2
BEAR_THRESHOLD: float = -0.2

STRENGTH_MAX_CAP: float = 20.0
EMPIRICAL_K: int = 100

BASE_CONFIDENCE_MIN: float = 0.55
BASE_CONFIDENCE_MAX: float = 0.98


# === 기타 ===============================================================

def ensure_artifacts_exist() -> None:
    missing = []

    if not STEP6_PATH.exists():
        missing.append(f"step6_data.npz: {STEP6_PATH}")
    if not EMPIRICAL_BACKTEST_PATH.exists():
        missing.append(f"empirical_backtest.csv: {EMPIRICAL_BACKTEST_PATH}")
    if not MARKET_DATA_PATH.exists():
        missing.append(f"market_data.csv: {MARKET_DATA_PATH}")

    for name, path in MODEL_WEIGHTS.items():
        if not path.exists():
            missing.append(f"{name} weights: {path}")

    if missing:
        msg = (
            "[config.ensure_artifacts_exist] 필요한 아티팩트 파일이 없습니다.\n"
            "Colab 파이프라인 artifacts_golden 폴더를 backend app 폴더로 복사했는지 확인하세요.\n\n"
            "누락 목록:\n  - " + "\n  - ".join(missing)
        )
        raise FileNotFoundError(msg)


# === (추가) 시장 개장/마감 체크 기능 ======================================

KST = ZoneInfo("Asia/Seoul")

def is_kospi_open(dt: datetime | None = None) -> bool:
    """KOSPI 정규장: 평일 09:00 ~ 15:30"""
    if dt is None:
        dt = datetime.now(KST)
    else:
        dt = dt.astimezone(KST)

    # 주말
    if dt.weekday() >= 5:
        return False

    open_t = time(9, 0)
    close_t = time(15, 30)
    return open_t <= dt.time() <= close_t


def get_market_status(dt: datetime | None = None) -> str:
    return "open" if is_kospi_open(dt) else "closed"
