import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from fastapi import APIRouter
import io
from starlette.responses import JSONResponse, StreamingResponse

def detect_ann_outliers(df_ann_results: pd.DataFrame,
                        all_assets: list,
                        N: int = 120,
                        contamination: float = 0.1,
                        save_path: str = None):
    # 최근 N일 매도 신호 비율 계산
    ann_ratio = df_ann_results.groupby('asset')['ann_signal'].rolling(window=N, min_periods=1).mean().reset_index()
    ann_ratio.rename(columns={'ann_signal': 'sell_ratio_ann'}, inplace=True)

    # Isolation Forest 이상치 탐지
    iso_ann = IsolationForest(contamination=contamination, random_state=42)
    ann_features = (
        ann_ratio.groupby('asset')['sell_ratio_ann'].mean()
        .reindex(all_assets)
        .values.reshape(-1, 1)
    )
    iso_ann.fit(ann_features)
    ann_outlier = iso_ann.predict(ann_features)

    ann_outlier_df = pd.DataFrame({
        'asset': ann_ratio['asset'].unique(),
        'outlier_flag_ann': ann_outlier
    })

    # **Date 컬럼 병합** - CSV에서 Date 가져오기
    if 'Date' in df_ann_results.columns:
        ann_ratio = ann_ratio.merge(df_ann_results[['asset', 'Date']], on='asset', how='left')
        ann_outlier_df = ann_outlier_df.merge(df_ann_results[['asset', 'Date']], on='asset', how='left')

    # CSV 저장
    if save_path:
        if 'Date' in ann_ratio.columns and 'Date' in ann_outlier_df.columns:
            result_df = pd.merge(ann_ratio, ann_outlier_df, on=['asset', 'Date'], how='left')
        else:
            result_df = pd.merge(ann_ratio, ann_outlier_df, on='asset', how='left')

        columns_order = ['Date', 'asset', 'sell_ratio_ann', 'outlier_flag_ann']
        result_df = result_df[[col for col in columns_order if col in result_df.columns]]
        result_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"CSV 저장 완료: {save_path}")

    return ann_ratio, ann_outlier_df

# =============================
# 시각화
# =============================
def plot_ann_outliers(ann_ratio, ann_outlier_df):
    ann_mean = ann_ratio.groupby('asset')['sell_ratio_ann'].mean().reset_index()
    plot_df = pd.merge(ann_mean, ann_outlier_df, on='asset')

    # 단일 축 생성
    fig, ax = plt.subplots(figsize=(12,6))

    # 산점도 표시
    for i, row in plot_df.iterrows():
        color = 'yellow' if row['outlier_flag_ann'] == -1 else 'green'
        ax.scatter(row['sell_ratio_ann'], 0, color=color, s=100)
        ax.text(row['sell_ratio_ann'] + 0.01, 0, row['asset'], fontsize=9)

    # 그래프 설정
    ax.set_xlabel('ANN SELL Ratio')
    ax.set_yticks([])
    ax.set_title('ANN Asset Anomaly Detection')
    ax.grid(True)

    plt.tight_layout()
    plt.show()

# ============================
# 4) 메인 실행
# ============================
if __name__ == "__main__":
    try:
        # 1️⃣ 데이터 로드
        data_path = "C:/Users/dbjin/Data/ann_signal_results.csv"
        df_ann = pd.read_csv(data_path)  # asset, Date, ann_signal
        all_assets = df_ann['asset'].unique().tolist()

        # 2️⃣ ANN 이상치 탐지
        ann_ratio, ann_outlier_df = detect_ann_outliers(
            df_ann_results=df_ann,
            all_assets=all_assets,
            N=120,
            contamination=0.1,
            save_path="C:/Users/dbjin/Data/ann_outlier.csv"
        )

        # 3️⃣ 시각화
        plot_ann_outliers(ann_ratio, ann_outlier_df)

    except Exception as e:
        import traceback
        print("=== 오류 발생 ===")
        print(traceback.format_exc())

    # 시각화
    plot_ann_outliers(ann_ratio, ann_outlier_df)


ann_plot_router = APIRouter()

@ann_plot_router.get("/plot/ann_iso")
def ann_plot():
    try:
        df = pd.read_csv("C:/Users/dbjin/Data/ann_signal_results.csv")
        all_assets = df['asset'].unique().tolist()
        ann_ratio, ann_outlier_df = detect_ann_outliers(df, all_assets)

        plot_df = pd.merge(
            ann_ratio.groupby('asset')['sell_ratio_ann'].mean().reset_index(),
            ann_outlier_df,
            on='asset'
        )

        # PNG 스트리밍
        fig, ax = plt.subplots(figsize=(12,6))
        for _, row in plot_df.iterrows():
            color = 'yellow' if row['outlier_flag_ann'] == -1 else 'green'
            ax.scatter(row['sell_ratio_ann'], 0, color=color, s=100)
            ax.text(row['sell_ratio_ann'] + 0.01, 0, row['asset'], fontsize=9)
        ax.set_xlabel("ANN SELL Ratio")
        ax.set_yticks([])
        ax.set_title("ANN Asset Anomaly Detection")
        ax.grid(True)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)