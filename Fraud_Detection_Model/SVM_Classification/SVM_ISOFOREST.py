import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

def detect_svm_outliers(df_svm_results: pd.DataFrame,
                        all_assets: list,
                        N: int = 120,
                        contamination: float = 0.1,
                        save_path: str = None):

    # 1) 최근 N일 매도 신호 비율 계산
    # SVM 신호 계산
    svm_ratio = df_svm_results.groupby('asset')['svm_signal'].rolling(window=N, min_periods=1).mean().reset_index()
    svm_ratio.rename(columns={'svm_signal': 'sell_ratio_svm'}, inplace=True)

    # 2) Isolation Forest 이상치 탐지
    # SVM 이상치
    iso_svm = IsolationForest(contamination=0.5, random_state=42)

    svm_features = (
        svm_ratio.groupby('asset')['sell_ratio_svm'].mean()
        .reindex(all_assets)  # 모든 자산 보존
        .values.reshape(-1, 1)
    )
    ''
    iso_svm.fit(svm_features)
    svm_outlier = iso_svm.predict(svm_features)

    svm_outlier_df = pd.DataFrame({
        'asset': all_assets,
        'outlier_flag_svm': svm_outlier  # SVM 기반 이상치 여부 (-1: 이상치, 1: 정상)
    })

    print("\n=== SVM 이상치 플래그 ===") #이상치 여부 (-1: 이상치, 1: 정상)
    print(svm_outlier_df)

    # svm_ratio와 svm_outlier_df에 Date 매핑
    if 'Date' not in svm_ratio.columns:
        svm_ratio = svm_ratio.merge(
            df_svm[['asset', 'Date']],  # 기존 SVM 시그널 CSV에서 날짜 가져오기
            on='asset',
            how='left'
        )

    if 'Date' not in svm_outlier_df.columns:
        svm_outlier_df = svm_outlier_df.merge(
            df_svm[['asset', 'Date']],  # 동일하게 SVM 날짜 매핑
            on='asset',
            how='left'
        )

    # CSV 저장
    if save_path:
        result_df = pd.merge(svm_ratio, svm_outlier_df, on=['asset', 'Date'], how='left')
        columns_order = ['Date', 'asset', 'sell_ratio_svm', 'outlier_flag_svm']
        result_df = result_df[[col for col in columns_order if col in result_df.columns]]
        result_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        print(f"CSV 저장 완료: {save_path}")

    return svm_ratio, svm_outlier_df

# =============================
# 시각화
# =============================
def plot_svm_outliers(svm_ratio, svm_outlier_df):
    svm_mean = svm_ratio.groupby('asset')['sell_ratio_svm'].mean().reset_index()
    plot_df = pd.merge(svm_mean, svm_outlier_df, on='asset')

    # 단일 축 생성
    fig, ax = plt.subplots(figsize=(12,6))

    # 산점도 표시
    for i, row in plot_df.iterrows():
        color = 'green' if row['outlier_flag_svm'] == -1 else 'blue'
        ax.scatter(row['sell_ratio_svm'], 0, color=color, s=100)
        ax.text(row['sell_ratio_svm'] + 0.01, 0, row['asset'], fontsize=9)

    # 그래프 설정
    ax.set_xlabel('SVM SELL Ratio')
    ax.set_yticks([])
    ax.set_title('SVM Asset Anomaly Detection')
    ax.grid(True)

    plt.tight_layout()
    plt.show()

# ============================
# 4) 메인 실행
# ============================
if __name__ == "__main__":
    # 데이터 로드
    df_svm = pd.read_csv("C:/Users/dbjin/Data/svm_signal_results.csv")  # asset, Date, svm_signal
    all_assets = df_svm['asset'].unique().tolist()

    # SVM 이상치 탐지
    svm_ratio, svm_outlier_df = detect_svm_outliers(df_svm, all_assets,
                                                    N=120,
                                                    contamination=0.1,
                                                    save_path="C:/Users/dbjin/Data/svm_outlier.csv")

    # 시각화
    plot_svm_outliers(svm_ratio, svm_outlier_df)


