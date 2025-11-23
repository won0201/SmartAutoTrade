from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import os
import time
import threading
from io import BytesIO
import traceback  # <-- 추가

es_cutoff_router = APIRouter()

CACHE_PATH = "/app/data/cache_es_cutoff_all_plot.png"
os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

CACHE_LIFETIME = 3600
cache_lock = threading.Lock()

@es_cutoff_router.get("/plot/es_cutoff_all")
def plot_all_assets(
    q_level: float = Query(0.8),
    path: str = Query("/app/data/svm_ann_target_data.csv")
):
    try:
        # 캐시 사용
        with cache_lock:
            if os.path.exists(CACHE_PATH) and (
                time.time() - os.path.getmtime(CACHE_PATH) < CACHE_LIFETIME
            ):
                return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")

        # CSV 읽기
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found at {path}")

        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        assets = df["asset"].unique()

        fig, axes = plt.subplots(len(assets), 1, figsize=(10, 3 * len(assets)), sharex=True)

        for i, asset in enumerate(assets):
            g = df[df["asset"] == asset].copy()
            g["abs_ES"] = g["pred_ES"].abs()
            cutoff = g["abs_ES"].quantile(q_level)

            ax = axes[i] if len(assets) > 1 else axes
            ax.plot(g["Date"], g["abs_ES"], label="|Pred ES|")
            ax.axhline(cutoff, color="red", linestyle="--", label=f"Cutoff q={q_level}")
            ax.set_title(f"Asset {asset}")
            ax.legend()
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        tmp_path = CACHE_PATH + ".tmp"
        with cache_lock:
            fig.savefig(tmp_path, format="png", bbox_inches="tight")
            plt.close(fig)
            os.replace(tmp_path, CACHE_PATH)

        return StreamingResponse(open(CACHE_PATH, "rb"), media_type="image/png")
    
    except Exception as e:
        # 여기서 실제 traceback과 에러를 JSON으로 반환
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
  
  