import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import autoscale
from sklearn.ensemble import IsolationForest

def detect_ann_outliers(df_ann_results: pd.DataFrame,
                        all_assets: list,
                        N: int = 120,
                        contamination: float = 0.1,
                        save_path: str = None):

    # 1) 최근 N일 매도 신호 비율 계산
    # ANN 신호 계산
    ann_ratio = df_ann_results.groupby('asset')['ann_signal'].rolling(window=N, min_periods=1).mean().reset_index()
    ann_ratio.rename(columns={'ann_signal': 'sell_ratio_ann'}, inplace=True)

    # 2) Isolation Forest 이상치 탐지
    # ANN 이상치
    iso_ann = IsolationForest(
        contamination=0.05,
        random_state=42)

    ann_features = (
        ann_ratio.groupby('asset')['sell_ratio_ann'].mean()
        .reindex(all_assets)
        .values.reshape(-1, 1)
    )

    iso_ann.fit(ann_features)
    ann_outlier = iso_ann.predict(ann_features)

    ann_outlier_df = pd.DataFrame({
        'asset': ann_ratio['asset'].unique(),
        'outlier_flag_ann': ann_outlier  # ANN 기반 이상치 여부 (-1: 이상치, 1: 정상)
    })
    df_sorted = ann_outlier_df.copy()
    df_sorted['asset'] = df_sorted['asset'].str.strip()
    df_sorted = df_sorted.sort_values(by='asset', ascending=True)

    # 출력
    print("=== ANN 이상치 플래그 ===")
    for idx, row in df_sorted.iterrows():
        print(f"{row['asset']:<10}  {row['outlier_flag_ann']:>3}")

    # ann_ratio, ann_outlier_df에 Date 매핑
    if 'Date' not in ann_ratio.columns:
        ann_ratio = ann_ratio.merge(
            df_svm[['asset', 'Date']],  # 기존 SVM 데이터에서 Date 가져오기
            on='asset',
            how='left'
        )

    if 'Date' not in ann_outlier_df.columns:
        ann_outlier_df = ann_outlier_df.merge(
            df_svm[['asset', 'Date']],
            on='asset',
            how='left'
        )

    # 이제 merge 가능
    result_df = pd.merge(ann_ratio, ann_outlier_df, on=['asset', 'Date'], how='left')

    # 3) CSV 저장
    if save_path:
        result_df = pd.merge(ann_ratio, ann_outlier_df, on=['asset', 'Date'], how='left')
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
        color = 'green' if row['outlier_flag_ann'] == -1 else 'blue'
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
    # 데이터 로드
    df_svm = pd.read_csv("C:/Users/dbjin/Data/ann_signal_results.csv")  # asset, Date, svm_signal
    all_assets = df_svm['asset'].unique().tolist()

    # ANN 이상치 탐지
    ann_ratio, ann_outlier_df = detect_ann_outliers(df_svm, all_assets,
                                                    N=120,
                                                    contamination=0.1,
                                                    save_path="C:/Users/dbjin/Data/ann_outlier.csv")

    # 시각화
    plot_ann_outliers(ann_ratio, ann_outlier_df)