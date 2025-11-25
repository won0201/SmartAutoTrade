# app.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from datetime import datetime
import asyncio

app = FastAPI()

# CORS 설정 (프런트가 다른 포트에서 열려도 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 0) 스냅샷 페이로드 함수
#    (여기만 나중에 실제 A 프로젝트 결과로 바꾸면 됨)
# -----------------------------
def snapshot_payload():
    # TODO: empirical_backtest.csv, results.json, 포지션 정보에서 계산
    # 프런트엔드(main.js)가 기대하는 key 이름에 맞춰서 반환
    return {
        "r2": 0.888,                        # 예측 R²
        "signal": 0.72,                     # 시그널 강도 ([-1, 1] 권장)
        "var": 0.019,                       # VaR (0~0.1 등 비율)
        "pos": "Long 3 / Short 1",          # 포지션 문자열
        "dd": -0.034,                       # 최대 드로우다운 비율
        "updated": datetime.now().strftime("%H:%M"),
    }


# -----------------------------
# 1) 정적 파일 서빙 (index.html / main.css / main.js)
#    → http://localhost:8000 들어가면 바로 SIGMA 화면이 뜨도록
# -----------------------------
@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/main.css")
async def serve_css():
    return FileResponse("main.css")

@app.get("/main.js")
async def serve_js():
    return FileResponse("main.js")


# -----------------------------
# 2) REST 폴백 API
#    /api/snapshot
# -----------------------------
@app.get("/api/snapshot")
async def api_snapshot():
    return JSONResponse(snapshot_payload())


# -----------------------------
# (선택) 직접 실행용
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
