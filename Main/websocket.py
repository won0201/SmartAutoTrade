# test_ws.py
import asyncio
import websockets


async def test_ws():
    uri = "ws://localhost:8085/ws/alerts"  # FastAPI WebSocket URL
    try:
        async with websockets.connect(uri) as ws:
            print("[WebSocket 연결 성공]")
            # 서버로 메시지 전송
            await ws.send("테스트 메시지")
            # 서버에서 메시지 수신 (옵션)
            msg = await ws.recv()
            print("서버로부터 받은 메시지:", msg)
    except Exception as e:
        print(" 연결 실패:", e)


# 메인에서 실행
if __name__ == "__main__":
    asyncio.run(test_ws())
