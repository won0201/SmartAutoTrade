import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis
import json
from typing import List
import uvicorn
from fastapi.responses import HTMLResponse


# ============================
# ANN 모델 학습
# ============================
def train_ann_signals(df: pd.DataFrame,
                      features: list = ["pred_sharpe", "pred_ES"],
                      label_col: str = "label",
                      hidden_layers: tuple = (32, 16),
                      max_iter: int = 2500,
                      save_path: str = None):
    # 1) cutoff 기반 label 생성
    df = df.copy()
    df["abs_ES"] = df["pred_ES"].abs()
    df["true_label"] = df.groupby("asset")["abs_ES"].transform(lambda x: (x >= x.quantile(0.8)).astype(int))

    # 2) ANN 모델 구성 및 학습
    # 데이터 준비
    X_all = df[features].values  # 전체 데이터 feature
    y_all = df["true_label"].values  # 레이블

    ann_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('mlp', MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=2500, random_state=42))
    ])  # iter 반복 횟수를 증가시켜 수렴할수록 정확한 결과

    # 모델 학습
    ann_pipeline.fit(X_all, y_all)

    # 전체 데이터 예측
    df_ann_results = df.copy()  # Data프레임을 복사해서 ANN 예측 결과를 담기
    df_ann_results["ann_signal"] = ann_pipeline.predict(X_all)
    df_ann_results["ann_proba"] = ann_pipeline.predict_proba(X_all)[:, 1]

    # 결과 CSV 저장
    if save_path:
        df_ann_results[["Date", "asset", "ann_signal", "ann_proba"]].to_csv(save_path, index=False,
                                                                            encoding="utf-8-sig")

        print(f"\n")

    return ann_pipeline, df_ann_results


def evaluate_ann(df_ann_results):
    # 성능 평가
    y_true = df_ann_results["true_label"].astype(int).values
    y_pred = df_ann_results["ann_signal"].astype(int).values
    y_prob = df_ann_results["ann_proba"]

    # 자산별 신호 개수
    print("=== 자산별 매도 -> 1 /보유 -> 0 신호 개수 ===")
    signal_count = df_ann_results.groupby('asset')['ann_signal'].value_counts().unstack(fill_value=0)
    print(signal_count)

    # 분류 리포트
    print("\n=== ANN 분류 리포트 ===")
    print(classification_report(y_true, y_pred, digits=4))
    print("ROC-AUC:", roc_auc_score(y_true, y_prob))

    # Confusion Matrix
    print("\n=== Confusion Matrix ===")
    print(confusion_matrix(y_true, y_pred))

    # ROC-AUC 점수
    roc_auc = roc_auc_score(y_true, y_prob)
    print(f"\n=== ROC-AUC Score === {roc_auc:.4f}")


# ============================================
# ⚡Redis에 피처 저장
# ============================================
# Redis 연결
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


# Redis에서 특정 자산 조회 함수
def get_feature_from_redis(asset: str):
    key = f"feature:{asset}"
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None


# Redis에 자산 피처 저장 함수
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
            r.delete(key)  # 기존 키 삭제
            r.hset(key, mapping={"data": json.dumps(rows, ensure_ascii=False)})
            print(f"[저장] {key} → {len(rows)} rows")
        except Exception as e:
            print(f"[Redis 저장 실패] {key}: {e}")

    print(f"\nRedis에 총 {success}개 자산 피처 저장 완료, 실패: {fail}개")


# =============================
# 🚀FastAPI + WebSocket 서버
# =============================
app = FastAPI(title="ANN Signal Server")

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


# HTTP GET 예제: Redis에서 특정 자산 조회
@app.get("/feature/{asset}")
async def read_feature(asset: str):
    feature = get_feature_from_redis(asset)  # asset 이름 전달
    if feature:
        feature["asset"] = asset  # 클라이언트가 요청한 asset 이름
        print(f"Sending feature to client: {feature}")
        return feature  # HTTP GET은 await manager.send_personal_message 필요 없음
    else:
        error_msg = {"error": f"Asset '{asset}' not found"}
        print(f"Sending error: {error_msg}")
        return error_msg


# WebSocket: 실시간 업데이트
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("Client connected")
    try:
        while True:
            data = await websocket.receive_text()
            # 클라이언트에서 요청한 자산
            feature = get_feature_from_redis(data)
            if feature:
                # asset 이름 포함
                feature["asset"] = data
                await manager.send_personal_message(json.dumps(feature), websocket)
            else:
                # asset이 Redis에 없을 경우 에러 메시지 전송
                await manager.send_personal_message(
                    json.dumps({"error": f"Asset '{data}' not found"}), websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    #  ANN결과 CSV 저장
    df = pd.read_csv(r"C:\Users\dbjin\DATA\svm_ann_target_data.csv")  # df_labeled 예시

    quantile_cutoff = 0.8
    df["abs_ES"] = df["pred_ES"].abs()
    df["true_label"] = (df["abs_ES"] >= df["abs_ES"].quantile(quantile_cutoff)).astype(int)

    # 저장 경로
    output_path = r"C:\Users\dbjin\DATA\ann_signal_results.csv"

    # 모델 학습 및 결과 생성
    ann_model, df_ann_results = train_ann_signals(df, save_path=output_path)

    # 평가
    evaluate_ann(df_ann_results)
    print(f"\n ANN signal results saved to {output_path}")

    # Redis 저장
    save_features_to_redis(df)

    # FastAPI 서버 실행
    uvicorn.run(app, host="127.0.0.1", port=8082)

