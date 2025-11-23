import redis
import json
from fastapi import FastAPI, WebSocket
import asyncio
import uvicorn
import pandas as pd
from Main.main import app

# ============================================
# ⚡Redis에 피처 저장
# ============================================
def save_features_to_redis(df, redis_host="localhost", redis_port=6379, db=0):
    r = redis.StrictRedis(host=redis_host, port=redis_port, db=db, decode_responses=True)
    success, fail = 0, 0

    # Timestamp → 문자열 변환
    for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
        df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    for asset, group in df.groupby("asset"):
        key = f"feature:{asset}"
        try:
            rows = group.to_dict(orient="records")
            r.hset(key, mapping={"data": json.dumps(rows, ensure_ascii=False)})
            success += 1
            print(f"[저장] {key} → {list(group.columns)}")
        except Exception as e:
            fail += 1
            print(f"[Redis 저장 실패] {key}: {e}")
    print(f"\nRedis에 총 {success}개 자산 피처 저장 완료")

    # =============================
    # 🚀FastAPI + WebSocket 서버
    # =============================
    app = FastAPI()
    r = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

    @app.get("/features/{asset}")
    async def get_features(asset: str):
        key = f"feature:{asset}"
        data_json = r.hget(key, "data")
        if data_json:
            return json.loads(data_json)
        return {"error": "No data found"}

    @app.websocket("/ws/features/{asset}")
    async def websocket_features(websocket: WebSocket, asset: str):
        await websocket.accept()
        key = f"feature:{asset}"
        try:
            while True:
                data_json = r.hget(key, "data")
                if data_json:
                    await websocket.send_text(data_json)
                await asyncio.sleep(1)  # 1초마다 갱신
        except Exception as e:
            await websocket.close()
            print(f"WebSocket 종료: {e}")

# ============================
# Main
# ============================
if __name__ == "__main__":
    output_path = r"C:\Users\dbjin\DATA\svm_ann_target_data.csv"

#  SVM 결과 CSV 저장
df = pd.read_csv(r"C:\Users\dbjin\DATA\svm_ann_target_data.csv")  # df_labeled 예시

quantile_cutoff = 0.8
df["abs_ES"] = df["pred_ES"].abs()
df["true_label"] = (df["abs_ES"] >= df["abs_ES"].quantile(quantile_cutoff)).astype(int)

# Redis 저장
save_features_to_redis(df)

# Redis 저장
r = redis.StrictRedis(host="0.0.0.0", port=6379, db=0, decode_responses=True)



