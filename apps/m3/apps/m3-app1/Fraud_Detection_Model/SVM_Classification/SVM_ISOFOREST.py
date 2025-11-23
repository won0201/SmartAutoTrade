import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
import io

# ============================
# SVM 이상치 탐지 함수
# ============================
def detect_svm_outliers(df_svm_results: pd.DataFrame,
                        all_assets: list,
                        N: int = 120,
                        contamination: float = 0.1,
                        save_path: str = None):
    # 1) 최근 N일 매도 신호 비율 계산
    svm_ratio = df_svm_results.groupby('asset')['svm_signal'].rolling(window=N, min_periods=1).mean().reset_index()
    svm_ratio.rename(columns={'svm_signal': 'sell_ratio_svm'}, inplace=True)

    # 2) Isolation Forest 이상치 탐지
    iso_svm = IsolationForest(contamination=contamination, random_state=42)
    svm_features = svm_ratio.groupby('asset')['sell_ratio_svm'].mean().reindex(all_assets).values.reshape(-1, 1)
    iso_svm.fit(svm_features)
    svm_outlier = iso_svm.predict(svm_features)

    svm_outlier_df = pd.DataFrame({
        'asset': all_assets,
        'outlier_flag_svm': svm_outlier
    })

    # Date 컬럼 병합
    if 'Date' in df_svm_results.columns:
        svm_ratio = svm_ratio.merge(df_svm_results[['asset', 'Date']], on='asset', how='left')
        svm_outlier_df = svm_outlier_df.merge(df_svm_results[['asset', 'Date']], on='asset', how='left')

    # CSV 저장
    if save_path:
        result_df = pd.merge(svm_ratio, svm_outlier_df, on=['asset', 'Date'], how='left') \
            if 'Date' in svm_ratio.columns and 'Date' in svm_outlier_df.columns \
            else pd.merge(svm_ratio, svm_outlier_df, on='asset', how='left')
        columns_order = ['Date', 'asset', 'sell_ratio_svm', 'outlier_flag_svm']
        result_df = result_df[[col for col in columns_order if col in result_df.columns]]
        result_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"CSV 저장 완료: {save_path}")

    return svm_ratio, svm_outlier_df

# ============================
# 시각화 함수
# ============================
def plot_svm_outliers(svm_ratio, svm_outlier_df):
    svm_mean = svm_ratio.groupby('asset')['sell_ratio_svm'].mean().reset_index()
    plot_df = pd.merge(svm_mean, svm_outlier_df, on='asset')

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, row in plot_df.iterrows():
        color = 'yellow' if row['outlier_flag_svm'] == -1 else 'green'
        ax.scatter(row['sell_ratio_svm'], 0, color=color, s=100)
        ax.text(row['sell_ratio_svm'] + 0.01, 0, row['asset'], fontsize=9)

    ax.set_xlabel('SVM SELL Ratio')
    ax.set_yticks([])
    ax.set_title('SVM Asset Anomaly Detection')
    ax.grid(True)
    plt.tight_layout()

    return fig  # Figure 반환


# FastAPI 앱 및 라우터
svm_plot_router = APIRouter()

def generate_svm_figure():
    df_svm = pd.read_csv("C:/Users/dbjin/Data/svm_signal_results.csv")
    assets = df_svm['asset'].unique()

    fig, axes = plt.subplots(len(assets), 1, figsize=(8, 3*len(assets)), sharex=True)

    for i, asset in enumerate(assets):
        g = df_svm[df_svm['asset'] == asset]
        axes_i = axes[i] if len(assets) > 1 else axes
        axes_i.plot(g['Date'], g['pred_ES'], label='Predicted ES')
        axes_i.set_title(f"Asset: {asset}")
        axes_i.legend()
        plt.setp(axes_i.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    return fig

@svm_plot_router.get("/plot/svm_iso")
def svm_plot():
    try:
        # CSV에서 데이터 로드
        df_svm = pd.read_csv("C:/Users/dbjin/Data/svm_signal_results.csv")
        all_assets = df_svm['asset'].unique().tolist()

        # 이상치 탐지
        svm_ratio, svm_outlier_df = detect_svm_outliers(df_svm, all_assets)

        # 시각화
        fig, ax = plt.subplots(figsize=(12,6))
        svm_mean = svm_ratio.groupby('asset')['sell_ratio_svm'].mean().reset_index()
        plot_df = pd.merge(svm_mean, svm_outlier_df, on='asset')

        for _, row in plot_df.iterrows():
            color = 'yellow' if row['outlier_flag_svm'] == -1 else 'green'
            ax.scatter(row['sell_ratio_svm'], 0, color=color, s=100)
            ax.text(row['sell_ratio_svm'] + 0.01, 0, row['asset'], fontsize=9)

        ax.set_xlabel("SVM SELL Ratio")
        ax.set_yticks([])
        ax.set_title("SVM Asset Anomaly Detection")
        ax.grid(True)
        plt.tight_layout()

        # PNG를 메모리 스트림으로 변환
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        # FastAPI StreamingResponse로 반환
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(content={"error": str(e)})
