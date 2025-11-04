from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import pandas as pd
import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates


es_cutoff_router = APIRouter()

@es_cutoff_router.get("/plot/es_cutoff_all")
def plot_all_assets(
    q_level: float = Query(0.8),
    path: str = Query(r"C:\Users\dbjin\DATA\svm_ann_target_data.csv")
):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])  # Date를 datetime로 변환해야 날짜 정확히 표기
    assets = df["asset"].unique()

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

        # 날짜 축 포맷 지정
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)  # 날짜 라벨 회전

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)
    return StreamingResponse(buf, media_type="image/png")