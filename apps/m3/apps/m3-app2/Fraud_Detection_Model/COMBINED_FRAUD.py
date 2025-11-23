import pandas as pd
import matplotlib.pyplot as plt
#============================
# 1) CSV 불러오기
# ============================
def csv_merge():
    df_merged = pd.read_csv("C:\\Users\\dbjin\\DATA\\merged_data.csv", parse_dates=["Date"])
    df_svm = pd.read_csv("C:\\Users\\dbjin\\DATA\\svm_signal_results.csv", parse_dates=["Date"])
    df_ann = pd.read_csv("C:\\Users\\dbjin\\DATA\\ann_signal_results.csv", parse_dates=["Date"])
    df_svm_outlier = pd.read_csv("C:\\Users\\dbjin\\DATA\\svm_outlier.csv", parse_dates=["Date"])
    df_ann_outlier = pd.read_csv("C:\\Users\\dbjin\\DATA\\ann_outlier.csv", parse_dates=["Date"])

    # 공백 제거
    df_merged.columns = df_merged.columns.str.strip()
    df_svm.columns = df_svm.columns.str.strip()
    df_ann.columns = df_ann.columns.str.strip()
    df_svm_outlier.columns = df_svm_outlier.columns.str.strip()
    df_ann_outlier.columns = df_ann_outlier.columns.str.strip()

    # Merge
    df = (
        df_merged
        .merge(df_svm, on=["Date", "asset"], how="left")
        .merge(df_ann, on=["Date", "asset"], how="left")
        .merge(df_svm_outlier, on=["Date", "asset"], how="left")
        .merge(df_ann_outlier, on=["Date", "asset"], how="left")
    )
    return df  # 🔥return해야 외부에서 함수 호출 가능

# ============================
# 2) 통합 신호 생성
# ============================
# 절댓값 ES 컬럼 추가
def generate_combined_signals(df, q_level=0.8):
    df["abs_ES"] = df["pred_ES"].abs()

    cutoffs = df.groupby("asset")["abs_ES"].quantile(q_level).to_dict()
    df["ES_Cutoff"] = df["asset"].map(cutoffs)

    # ES 초과 여부 (abs_ES vs cutoff)
    df["ES_Exceed"] = df["abs_ES"] >= df["ES_Cutoff"]

    # Isolation 이상치: -1이 이상치인 경우
    df["Outlier_Flag"] = (df["outlier_flag_svm"] == -1) | (df["outlier_flag_ann"] == -1)

    # Combined Signal: ES 초과 + SVM/ANN 매도 + Isolation 이상치
    df["Combined_Signal"] = (
    df["ES_Exceed"] &
     ((df["svm_signal"] == 1) | (df["ann_signal"] == 1)) &
    df["Outlier_Flag"]
)

    return df  # ← 반드시 반환

# ============================
# 3) 자산별 시각화
# ============================
def plot_signals(df, q_level=0.8):
    assets = df['asset'].unique()
    n_assets = len(assets)
    fig, axes = plt.subplots(n_assets, 1, figsize=(15, 5 * n_assets), sharex=True)

#axes가 1개일 경우 리스트로 변환
    if n_assets == 1:
        axes = [axes]

    for ax, asset in zip(axes, assets):
        data = df[df["asset"] == asset]

        # abs_ES 시계열
        ax.plot(data["Date"], data["abs_ES"], label="|Predicted ES|", color="blue", lw=2, zorder=1)

        # ES 컷오프
        ax.axhline(data["ES_Cutoff"].iloc[0], color="red", linestyle="--", lw=2,
               label=f"ES Cutoff (q={q_level})")

        # ES 초과
        ax.scatter(data["Date"][data["ES_Exceed"]], data["abs_ES"][data["ES_Exceed"]],
               color="red", marker="o", s=120, alpha=0.5, label="ES Exceed", zorder=3)

        # 모델 매도 신호
        ax.scatter(data['Date'][data['svm_signal'] == 1], data['abs_ES'][data['svm_signal'] == 1],
               color='orange', marker='^', s=550, label='SVM Sell Signal', edgecolors='black', zorder=4)
        ax.scatter(data['Date'][data['ann_signal'] == 1], data['abs_ES'][data['ann_signal'] == 1],
               color='green', marker='v', s=550, label='ANN Sell Signal', edgecolors='black', zorder=4)

        # Isolation Forest 이상치
        ax.scatter(data['Date'][data['outlier_flag_svm'] == -1], data['abs_ES'][data['outlier_flag_svm'] == -1],
               facecolor='none', edgecolor='orange', s=900, linewidth=1.5, marker='o', label='SVM Isolation Outlier',
               zorder=5)
        ax.scatter(data['Date'][data['outlier_flag_ann'] == -1], data['abs_ES'][data['outlier_flag_ann'] == -1],
               facecolor='none', edgecolor='green', s=900, linewidth=1.5, marker='s', label='ANN Isolation Outlier',
               zorder=5)

        # Combined Signal (가장 위)
        combined_idx = data['Combined_Signal'] == 1
        ax.scatter(data['Date'][combined_idx], data['abs_ES'][combined_idx],
               color='purple', marker='*', s=250, label='Combined Signal',
               edgecolors='yellow', linewidths=2, zorder=10)

        ax.set_title(f'{asset}: |Predicted ES| vs Cutoff, Signals & Outliers', fontsize=14)
        ax.set_ylabel('|Predicted ES|')
        ax.grid(True)
        ax.legend(loc='upper right', fontsize=9)

    plt.xlabel('Date')
    plt.tight_layout()
    plt.show()

# 메인 실행
if __name__ == "__main__":
    # 1) CSV 병합
    df = csv_merge()
    print(df.head())

    # 2) Combined  Signal 생성
    df = generate_combined_signals(df,q_level=0.8)
    print("\n=== Combined Signal 확인 ===")
    print(df[['Date', 'asset', 'abs_ES', 'ES_Cutoff', 'ES_Exceed', 'Outlier_Flag', 'Combined_Signal']].head())

    # 3) 시각화
    plot_signals(df, q_level=0.8)