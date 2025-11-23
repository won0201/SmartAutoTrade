from fastapi import APIRouter, WebSocket, Query
from pydantic import BaseModel
import pandas as pd
import json
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

riskscore_router = APIRouter()
clients: list[WebSocket] = []

CSV_PATH = "C:/Users/dbjin/DATA/ALL_score.csv"

# ===============================
# REST API: CSV 전체 반환
# ===============================
@riskscore_router.get("/riskscore/update")
async def get_all_risks():
    try:
        df = pd.read_csv(CSV_PATH)
        records = df.to_dict(orient="records")
        return records
    except Exception as e:
        return {"error": str(e)}

# ===============================
# WebSocket: 실시간 Z-score 알림
# ===============================
@riskscore_router.websocket("/ws/alerts")
async def alerts_ws(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    print("클라이언트 연결됨:", ws)
    try:
        while True:
            # CSV 읽어서 메시지 생성
            try:
                df = pd.read_csv(CSV_PATH)
                records = df.to_dict(orient="records")
                message = json.dumps(records)  # JSON 배열 형태
            except Exception as e:
                message = json.dumps([{"asset": "-", "Zscore": None, "Score": None, "Level": "-", "LevelClass": "level-Normal", "Date": "-"}])
                print("CSV 읽기 실패:", e)

            # 모든 연결된 클라이언트에 전송
            to_remove = []
            for client in clients:
                try:
                    await client.send_text(message)
                except Exception as e:
                    print("전송 오류:", e)
                    to_remove.append(client)
            for client in to_remove:
                clients.remove(client)

            await asyncio.sleep(5)  # 5초마다 전송
    except WebSocketDisconnect:
        print("클라이언트 연결 종료")
    finally:
        if ws in clients:
            clients.remove(ws)

