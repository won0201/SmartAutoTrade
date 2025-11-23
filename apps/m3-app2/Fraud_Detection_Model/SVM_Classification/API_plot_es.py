#API_plot_es.py
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import time
import threading
from io import BytesIO

es_cutoff_router = APIRouter()

# -----------------------------
CACHE_PATH = r"C:\Users\dbjin\DATA\cache_es_cutoff_all_plot.png"
CACHE_LIFETIME = 3600
os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

cache_lock = threading.Lock()
# -----------------------------

@es_cutoff_router.get("/plot/es_cutoff_all")
def plot_all_assets(
    q_level: float = Query(0.8),
    path: str = Query(r"C:\Users\dbjin\DATA\svm_ann_target_data.csv")
):
    try:
        # -----------------------------
        # 캐시가 유효하면 파일 그대로 반환
        with cache_lock:
            if os.path.exists(CACHE_PATH) and (time.time() - os.path.getmtime(CACHE_PATH) < CACHE_LIFETIME):
                return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")
        # -----------------------------

        # CSV 읽기
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        assets = df["asset"].unique()

        # Figure 생성
        fig, axes = plt.subplots(len(assets), 1, figsize=(10, 3 * len(assets)), sharex=True)

        for i, asset in enumerate(assets):
            g = df[df["asset"] == asset].copy()
            g["abs_ES"] = g["pred_ES"].abs()
            cutoff = g["abs_ES"].quantile(q_level)

            ax = axes[i] if len(assets) > 1 else axes
            ax.plot(g["Date"], g["abs_ES"], label="|Predicted ES|")
            ax.axhline(cutoff, color="red", linestyle="--", label=f"Cutoff q={q_level}")
            ax.set_title(f"Asset {asset}")
            ax.legend()

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        # -----------------------------
        # PNG 저장 (atomic replace)
        tmp_path = CACHE_PATH + ".tmp"
        with cache_lock:
            fig.savefig(tmp_path, format="png", bbox_inches="tight")
            plt.close(fig)
            os.replace(tmp_path, CACHE_PATH)

        # PNG 파일 반환
        return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")

    except Exception as e:
        # 에러 시 빈 PNG 반환 또는 status code
        return StreamingResponse(BytesIO(), media_type="image/png", status_code=500)
