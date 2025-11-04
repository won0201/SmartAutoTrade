from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import io
import base64
from Portfolio_Optimization.ES_Optimization import  optimize_minvar_with_cvar_cap  # 기존 함수 불러오기

optimize_router = APIRouter(prefix="/optimize")

@optimize_router.get("/plot")
def run_optimization():
    # === 데이터 불러오기 ===
    df_returns = pd.read_csv("C:/Users/dbjin/DATA/real_returns.csv", index_col=0, parse_dates=True)
    df_oos = df_returns["2025-01-01":]
    R_scen = df_oos.values

    # === 최적화 실행 ===
    alpha = 0.95
    es_cap = 0.04
    res = optimize_minvar_with_cvar_cap(R_scen, alpha=alpha, es_cap=es_cap)

    # === 그래프 생성 ===
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # (a) Pie chart
    weights = res["weights"]
    labels = df_returns.columns[:len(weights)]
    axes[0].pie(weights, labels=labels, autopct="%1.1f%%", startangle=90)
    axes[0].set_title("Optimized asset weight (Pie Chart)")

    # (b) 손실 분포
    port_losses = -R_scen @ weights
    VaR = np.quantile(port_losses, alpha)
    CVaR = port_losses[port_losses >= VaR].mean()

    axes[1].hist(port_losses, bins=50, alpha=0.6, color="skyblue", density=True)
    axes[1].axvline(VaR, color="red", linestyle="--", label=f"VaR({alpha * 100:.0f}%)")
    axes[1].axvline(CVaR, color="darkred", linestyle="-", label=f"CVaR ≈ {CVaR:.4f}")
    axes[1].axvline(es_cap, color="green", linestyle=":", label=f"ES cap {es_cap}")
    axes[1].set_title("portfolio loss distribution")
    axes[1].legend()

    plt.tight_layout()

    # === 이미지 인코딩 ===
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()

    return JSONResponse(content={"image": f"data:image/png;base64,{img_base64}"})

if __name__ == "__main__":
    run_optimization()