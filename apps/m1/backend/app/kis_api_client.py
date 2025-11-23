# kis_api_client.py
"""
SIGMA A 프로젝트 - 실시간 데이터 제공 모듈 (정상화된 버전)

외부에서는 KISApiClient 하나만 import해서 사용하도록 통합함.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import yfinance as yf

from .config import (
    USE_KIS_API,
    KIS_APP_KEY,
    KIS_APP_SECRET,
    KIS_ACCOUNT_NO,
    KIS_BASE_URL,
    YFINANCE_SYMBOL,
)

# ======================================================================
# 0. 공통
# ======================================================================

KST = timezone(timedelta(hours=9))

def now_kst_str() -> str:
    return datetime.now(tz=KST).isoformat()


# ======================================================================
# 1. 데모 모드(yfinance)
# ======================================================================

class YFinanceStreamer:
    def __init__(self, symbol: str = YFINANCE_SYMBOL):
        self.symbol = symbol
        self._cache_price = None
        self._last_ts = 0

    async def get_price(self) -> float:
        now = time.time()
        if self._cache_price is not None and now - self._last_ts < 1:
            return self._cache_price

        try:
            df = yf.Ticker(self.symbol).history(period="1d", interval="1m")
            if df.empty:
                raise ValueError("yfinance empty")
            price = float(df["Close"].iloc[-1])
            self._cache_price = price
            self._last_ts = now
            return price
        except:
            return self._cache_price if self._cache_price else 0.0


_yf = YFinanceStreamer()


# ======================================================================
# 2. 실제 KIS REST
# ======================================================================

class KISRestClient:
    def __init__(self):
        self.app_key = KIS_APP_KEY
        self.app_secret = KIS_APP_SECRET
        self.access_token: Optional[str] = None
        self.session = aiohttp.ClientSession()

    async def request_token(self):
        url = f"{KIS_BASE_URL}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        async with self.session.post(url, json=payload) as resp:
            data = await resp.json()
            if "access_token" in data:
                self.access_token = data["access_token"]
                print("[KISRestClient] access_token 발급 완료")
            else:
                raise RuntimeError(f"토큰 실패: {data}")

    async def _headers(self):
        if not self.access_token:
            await self.request_token()

        return {
            "content-type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

    async def get_price(self, symbol="101600"):
        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/price"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
        }
        headers = await self._headers()

        async with self.session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            try:
                return float(data["output"]["stck_prpr"])
            except:
                print("[KISRestClient] get_price 실패:", data)
                return None


_kis = KISRestClient()


# ======================================================================
# 3. 🔥 통합 API 클래스 — KISApiClient (외부에서 import하는 클래스)
# ======================================================================

class KISApiClient:
    """
    외부에서는 이 클래스만 import하여 사용하면 됨.

    - USE_KIS_API = True → 실제 KIS API
    - USE_KIS_API = False → yfinance 데모 스트림
    """

    async def get_realtime_price(self) -> float:
        if USE_KIS_API:
            price = await _kis.get_price("101600")
            return float(price) if price else 0.0
        else:
            return await _yf.get_price()


# ======================================================================
# 4. 세션 정리
# ======================================================================

async def close_clients():
    try:
        await _kis.session.close()
    except:
        pass
