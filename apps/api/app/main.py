from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

app = FastAPI(title="Graduation Project Shared API")


class SourceEnum(str, Enum):
    m1 = "m1"   # 시장상황 분석 / 프론트 1
    m2 = "m2"   # 옵션 스큐 + BOCPD 알고리즘 쪽
    m3 = "m3"   # 리스크 관리 / 실전 매매
    other = "other"


class SideEnum(str, Enum):
    buy = "BUY"
    sell = "SELL"
    hold = " HOLD"


class SignalRequest(BaseModel):
    source: SourceEnum = Field(..., description="신호를 보낸 모듈 ID (m1, m2, m3 등)")
    strategy: str = Field(..., description="전략 이름 예: iv_skew_bocpd_v1")
    symbol: str = Field(..., description="종목/자산 예: KODEX200, KOSPI200_F")
    side: SideEnum = Field(..., description="매수/매도/홀드")
    size: float = Field(..., description="수량 (또는 비중)")
    price: Optional[float] = Field(None, description="신호 생성 시점 기준 참고 가격")
    confidence: Optional[float] = Field(
        None, description="0~1 사이 신뢰도 점수 (없으면 None)"
    )
    meta: Optional[Dict[str, float]] = Field(
        None, description="추가 지표 (iv_skew, vol, regime 등 자유롭게)"
    )


# 👉 응답은 요청 필드 + id, received_at
class SignalResponse(SignalRequest):
    id: int
    received_at: datetime


signals: List[SignalResponse] = []
next_id = 1


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "shared-api", "time": datetime.utcnow()}


@app.post("/signals", response_model=SignalResponse)
def create_signal(signal: SignalRequest):
    global next_id

    data = SignalResponse(
        id=next_id,
        received_at=datetime.utcnow(),
        **signal.model_dump(),
    )
    signals.append(data)
    next_id += 1
    return data


@app.get("/signals/latest", response_model=List[SignalResponse])
def get_latest(limit: int = 10, source: Optional[SourceEnum] = None):
    """
    가장 최근 신호 여러 개 조회 (테스트용)
    - /signals/latest?limit=5
    - /signals/latest?source=m2
    """
    if source:
        filtered = [s for s in signals if s.source == source]
    else:
        filtered = signals
    return list(reversed(filtered[-limit:]))
