"""
SIGMA A 프로젝트 - 실시간 신호 생성기 (실전 확률 기반 confidence 버전)
"""

from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from .config import INTERNAL_SYMBOL, BULL_THRESHOLD, BEAR_THRESHOLD
from .kis_api_client import KISApiClient
from .data_processor import LiveDataProcessor
from .model_handler import run_inference
from .confidence_manager import ConfidenceManager
from .signal_store import get_recent_signals

KST = timezone(timedelta(hours=9))


def now_kst_iso() -> str:
    return datetime.now(tz=KST).isoformat()


def is_market_open() -> bool:
    now = datetime.now(tz=KST)

    if now.weekday() >= 5:
        print(f"[market] 주말이라 시장이 닫힘 ({now.weekday()})")
        return False

    if not (9 <= now.hour <= 15):
        print(f"[market] 장시간 아님. 현재 시각 {now.hour}:{now.minute}")
        return False

    if now.hour == 15 and now.minute > 30:
        print("[market] 15:30 이후 장 마감")
        return False

    return True


_live_proc = LiveDataProcessor()
_conf_manager = ConfidenceManager()
kis_client = KISApiClient()


def _classify_regime(score: float) -> str:
    if score >= BULL_THRESHOLD:
        return "bull"
    if score <= BEAR_THRESHOLD:
        return "bear"
    return "neutral"


def _get_last_real_signal(limit: int = 200) -> Optional[Dict[str, Any]]:
    try:
        arr = get_recent_signals(limit)
    except Exception as e:
        print(f"[signal_generator] 최근 신호 조회 실패: {e}")
        return None

    if not arr:
        return None

    for s in reversed(arr):
        if s.get("regime") != "market_closed" and s.get("score") is not None:
            return s

    return arr[-1]


def _build_market_closed_snapshot() -> Dict[str, Any]:
    print("[signal_generator] 시장 닫힘 → snapshot 생성")

    last = _get_last_real_signal()
    now = now_kst_iso()

    if not last:
        return {
            "timestamp": now,
            "symbol": INTERNAL_SYMBOL,
            "price": None,
            "regime": "market_closed",
            "score": None,
            "confidence": 0.0,
            "models": [],
            "raw_preds": {},
            "market_closed": True,
            "snapshot": {
                "next_open_regime": "neutral",
                "next_open_score": 0.0,
                "next_open_confidence": 0.0,
                "scenarios": [],
            },
        }

    last_score = float(last.get("score") or 0.0)
    last_conf = float(last.get("confidence") or 0.0)
    last_regime = last.get("regime", "neutral")

    def decide_action(score: float) -> str:
        if score >= BULL_THRESHOLD:
            return "BUY"
        if score <= BEAR_THRESHOLD:
            return "SELL"
        return "HOLD"

    scenarios = [
        {
            "change": "+1%",
            "score": round(last_score + 0.1, 3),
            "action": decide_action(last_score + 0.1),
        },
        {
            "change": "0%",
            "score": round(last_score, 3),
            "action": decide_action(last_score),
        },
        {
            "change": "-1%",
            "score": round(last_score - 0.1, 3),
            "action": decide_action(last_score - 0.1),
        },
    ]

    return {
        "timestamp": now,
        "symbol": INTERNAL_SYMBOL,
        "price": None,
        "regime": "market_closed",
        "score": None,
        "confidence": 0.0,
        "models": last.get("models", []),
        "raw_preds": last.get("raw_preds", {}),
        "market_closed": True,
        "snapshot": {
            "next_open_regime": last_regime,
            "next_open_score": last_score,
            "next_open_confidence": last_conf,
            "scenarios": scenarios,
        },
    }


async def generate_signal_once() -> Dict[str, Any]:
    print("[signal_generator] === generate_signal_once ===")

    if not is_market_open():
        return _build_market_closed_snapshot()

    try:
        price = await kis_client.get_realtime_price()
    except Exception as e:
        return _error_signal(None, f"price_fetch_error: {e}")

    if price is None:
        return _error_signal(None, "price_is_None")

    try:
        model_input = _live_proc.update(price)
    except Exception as e:
        return _error_signal(price, f"input_error: {e}")

    try:
        infer = run_inference(model_input)
    except Exception as e:
        return _error_signal(price, f"model_inference_error: {e}")

    models = infer.get("models", [])
    ensemble_score = infer.get("ensemble_score")
    raw_preds = infer.get("raw_preds", {})
    meta_prob = infer.get("meta_probability", None)

    if ensemble_score is None:
        return _error_signal(price, "no_model_output")

    # meta_probability 없으면 ensemble_score 기반으로 fallback
    if meta_prob is None:
        meta_prob = 1.0 / (1.0 + math.exp(-float(ensemble_score) * 4.0))

    # 실전 신뢰도 계산용 model_scores
    model_scores = [float(m.get("signal", 0.0)) for m in models]

    cm_res = _conf_manager.compute(
        model_scores=model_scores,
        meta_probability=float(meta_prob),
    )

    regime = _classify_regime(float(ensemble_score))

    return {
        "timestamp": now_kst_iso(),
        "symbol": INTERNAL_SYMBOL,
        "price": float(price),
        "regime": regime,
        "score": float(ensemble_score),
        "confidence": float(cm_res.final_confidence),
        "agreement": float(cm_res.agreement),
        "variance": float(cm_res.variance),
        "meta_probability": float(cm_res.meta_probability),
        "models": models,
        "raw_preds": raw_preds,
        "market_closed": False,
    }


def _error_signal(price: Optional[float], msg: str) -> Dict[str, Any]:
    print(f"[signal_generator] 에러: {msg}")
    return {
        "timestamp": now_kst_iso(),
        "symbol": INTERNAL_SYMBOL,
        "price": float(price) if price is not None else None,
        "regime": "error",
        "score": None,
        "confidence": 0.0,
        "models": [],
        "raw_preds": {},
        "error": msg,
        "market_closed": False,
    }


async def signal_loop(callback, interval_sec: float = 1.0):
    print(f"[signal_generator] signal_loop 시작 (interval={interval_sec})")
    while True:
        try:
            sig = await generate_signal_once()
            await callback(sig)
        except Exception as e:
            print(f"[signal_generator] 루프 중 오류: {e}")
        await asyncio.sleep(interval_sec)
