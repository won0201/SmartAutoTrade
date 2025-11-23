#API_optimize_plot.py
import os
import time
import matplotlib
matplotlib.use("Agg")  # 서버 환경용
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastapi import FastAPI, APIRouter, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from Portfolio_Optimization.ES_Optimization import optimize_minvar_with_cvar_cap
from io import BytesIO
import threading
import os

# FastAPI 앱 설정
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

optimize_router = APIRouter(prefix="/optimize")

# ----------------------------CACHE_PATH 설정 확인
CACHE_PATH = "/app/data/cache_portfolio_opt_plot.png"
dir_path = os.path.dirname(CACHE_PATH)

if dir_path:  # 빈 문자열이면 makedirs 호출 안 함
    os.makedirs(dir_path, exist_ok=True)

CACHE_LIFETIME = 3600  # 1시간
cache_lock = threading.Lock()
# -----------------------------

def make_optimization_figure():
    df_returns = pd.read_csv("/app/data/real_returns.csv", index_col=0, parse_dates=True)
    df_oos = df_returns["2025-01-01":]
    R_scen = df_oos.values

    res = optimize_minvar_with_cvar_cap(R_scen, alpha=0.95, es_cap=0.04)
    weights = res["weights"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Pie chart
    labels = df_returns.columns[:len(weights)]
    axes[0].pie(weights, labels=labels, autopct="%1.1f%%", startangle=90)
    axes[0].set_title("Optimized asset weight (Pie Chart)")

    # Loss distribution
    port_losses = -R_scen @ weights
    VaR = np.quantile(port_losses, 0.95)
    CVaR = port_losses[port_losses >= VaR].mean()

    axes[1].hist(port_losses, bins=50, alpha=0.6, color="skyblue", density=True)
    axes[1].axvline(VaR, color="red", linestyle="--", label=f"VaR(95%)")
    axes[1].axvline(CVaR, color="darkred", linestyle="-", label=f"CVaR ≈ {CVaR:.4f}")
    axes[1].set_title("Portfolio loss distribution")
    axes[1].legend()

    plt.tight_layout()
    return fig

@optimize_router.get("/plot")
def run_optimization():
    try:
        # -----------------------------
        # 캐시 유효하면 파일 그대로 반환
        with cache_lock:
            if os.path.exists(CACHE_PATH) and (time.time() - os.path.getmtime(CACHE_PATH) < CACHE_LIFETIME):
                return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")
        # -----------------------------

        # Figure 생성
        fig = make_optimization_figure()

        # 임시 저장 후 atomic replace
        tmp_path = CACHE_PATH + ".tmp"
        with cache_lock:
            fig.savefig(tmp_path, format="png", bbox_inches="tight")
            plt.close(fig)
            os.replace(tmp_path, CACHE_PATH)

        # PNG 파일 반환
        return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")

    except Exception as e:
        # 에러 시 빈 PNG 반환
        return StreamingResponse(BytesIO(), media_type="image/png", status_code=500)

# 라우터 등록
app.include_router(optimize_router)

def ensure_cache_dir():
    print("CACHE_PATH:", CACHE_PATH)
    print("dir_path:", dir_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

if __name__ == "__main__":
    ensure_cache_dir()


