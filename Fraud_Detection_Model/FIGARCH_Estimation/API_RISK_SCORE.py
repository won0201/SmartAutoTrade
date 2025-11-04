from fastapi import APIRouter, WebSocket, Query
from pydantic import BaseModel
import json

riskscore_router = APIRouter()
clients: list[WebSocket] = []

# 요청용 Pydantic 모델
class RiskUpdate(BaseModel):
    asset: str
    z: float
    score: float
    level: str
    risk_timestamp: str
    data_timestamp: str = Query(...)
    mode: str = "abs"

# GET 요청으로 리스크 업데이트
@riskscore_router.get("/riskscore/update")
async def update_risk_get(
    asset: str = Query(...),
    z: float = Query(...),
    score: float = Query(...),
    level: str = Query(...),
    timestamp: str = Query(...),
    mode: str = Query("abs")
):
    msg = {
        "asset": asset,
        "z": z,
        "score": score,
        "level": level,
        "timestamp": timestamp,
        "mode": mode
    }

    print(f"[{level}] {asset} | Z={z} | Score={score} | Mode={mode} | Time={timestamp}")

    # 연결된 모든 WebSocket 클라이언트에 전송
    disconnected = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception as e:
            print(f"WebSocket 전송 실패: {e}")
            disconnected.append(ws)

    # 연결 끊긴 클라이언트 제거
    for ws in disconnected:
        if ws in clients:
            clients.remove(ws)

    return {"status": "ok"}

# WebSocket 알림 수신
@riskscore_router.websocket("/ws/alerts")
async def alerts_ws(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # 클라이언트 메시지는 무시
    except Exception as e:
        print(f"WebSocket 연결 종료: {e}")
    finally:
        if ws in clients:
            clients.remove(ws)