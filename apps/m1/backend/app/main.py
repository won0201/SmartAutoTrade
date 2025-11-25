# app/main.py
"""
SIGMA A 프로젝트 - FastAPI 엔트리 포인트

Endpoints:
  GET  /signals?limit=N   → 최근 N개 신호 조회
  POST /predict           → 즉시 신호 1회 생성
  WS   /ws                → 실시간 스트림(WebSocket)

내부 로직:
  - 시장 열림 상태: 정상 신호 생성
  - 시장 닫힘 상태: snapshot 생성 (next-open, scenario report)
  - 백그라운드 작업으로 1초 주기 자동 신호 생성
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import asyncio

# 내부 모듈
from .signal_store import append_signal, get_recent_signals
from .signal_generator import generate_signal_once, signal_loop
from .kis_api_client import close_clients

app = FastAPI(title="SIGMA A PROJECT API")

# ----------------------------------------------------------------
# CORS
# ----------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ----------------------------------------------------------------
# WebSocket 연결 관리자
# ----------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self.active.remove(ws)
        except:
            pass

    async def broadcast(self, message: Dict[str, Any]):
        alive = []
        for ws in self.active:
            try:
                await ws.send_json(message)
                alive.append(ws)
            except:
                pass
        self.active = alive

manager = ConnectionManager()

# ----------------------------------------------------------------
# REST API
# ----------------------------------------------------------------

@app.get("/signals")
async def signals(limit: int = 120):
    """
    최근 N개의 신호 반환

    FastAPI가 내부적으로 Request 객체를 함수에 넘기지 않도록
    단일 positional 인자(limit)만 받도록 구성.
    """
    return get_recent_signals(limit)


@app.post("/predict")
async def predict_once():
    """
    강제 신호 생성
    (시장 열림/닫힘 여부와 관계 없이 generate_signal_once가 snapshot 포함 생성)
    """
    sig = await generate_signal_once()

    # 저장
    append_signal(sig)

    # 실시간 방송
    asyncio.create_task(manager.broadcast(sig))

    return sig


# ----------------------------------------------------------------
# WebSocket 실시간 스트림
# ----------------------------------------------------------------

@app.websocket("/ws")
async def ws_stream(ws: WebSocket):
    await manager.connect(ws)
    try:
        # 클라이언트가 아무것도 보내지 않아도 연결 유지됨
        while True:
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


# ----------------------------------------------------------------
# 백그라운드 자동 신호 생성
# ----------------------------------------------------------------

async def auto_signal_task():
    """
    1초마다 신호 생성 → 저장 → WebSocket broadcast
    시장이 닫혀 있으면 snapshot 자동 생성
    """
    async def on_signal(sig):
        append_signal(sig)
        await manager.broadcast(sig)

    await signal_loop(on_signal, interval_sec=1.0)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_signal_task())
    print("🚀 SIGMA A 프로젝트 서버 시작 (auto-signal enabled)")


@app.on_event("shutdown")
async def shutdown_event():
    await close_clients()
    print("🛑 서버 종료 완료")
