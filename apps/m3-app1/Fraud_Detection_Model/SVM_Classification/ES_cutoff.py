import pandas as pd
import matplotlib.pyplot as plt

# ============================
# 1) 파일 불러오기 (wide format)
# ============================
def df_svm_target_data(path_sharpe, path_es, q_level=0.8, show_plot=True, save_path=None):
    df_ret = pd.read_csv("C:\\Users\\dbjin\\DATA\\rolling_sharpe.csv", parse_dates=["Date"])
    df_es  = pd.read_csv("C:\\Users\\dbjin\\DATA\\es_out_sample_pred.csv", parse_dates=["Date"])

# Wide -> Long format
    df_ret_long = df_ret.melt(id_vars=["Date"], var_name="asset", value_name="pred_sharpe")
    df_es_long  = df_es.melt(id_vars=["Date"], var_name="asset", value_name="pred_ES")

# 공통 날짜 기준 병합
    df = pd.merge(df_ret_long, df_es_long, on=["Date","asset"])
    df = df.sort_values(["asset","Date"]).reset_index(drop=True)

    output_path = "C:\\Users\\dbjin\\DATA\\merged_data.csv"
    df.to_csv(output_path, index=False)

    # Date 기준 오름차순 정렬
    df = df.sort_values(by=["Date", "asset"]).reset_index(drop=True)

    if save_path:
        df.to_csv(save_path, index=False)
        print(f"Merged data saved to {save_path}")

    return df

# ============================
# 2) 자산별 절댓값 ES 기반 레이블링 (동적 cutoff)
# ============================
def label_by_es(df, q_level=0.8, show_plot=True):
    q_level = 0.8  # 상위 20%
    labels = []

    for asset, g in df.groupby("asset"):
        g = g.copy()  # 경고 방지 (SettingWithCopyWarning)
        g["abs_ES"] = g["pred_ES"].abs()
        cutoff = g["abs_ES"].quantile(q_level)
        g["label"] = (g["abs_ES"] >= cutoff).astype(int)

        # 그래프 확인
        if show_plot:
            plt.figure(figsize=(10, 3))
            plt.plot(g["Date"], g["abs_ES"], label="|Predicted ES|")
            plt.axhline(cutoff, color="red", linestyle="--", label=f"Cutoff q={q_level}")
            plt.title(f"Asset {asset} Predicted ES with Cutoff")
            plt.legend()
            plt.show()

        labels.append(g)

    df_labeled = pd.concat(labels).reset_index(drop=True)
    return df_labeled

# ============================
# Main
# ============================
if __name__ == "__main__":
    rolling_sharpe_path = r"C:\Users\dbjin\DATA\rolling_sharpe.csv"
    es_pred_path = r"C:\Users\dbjin\DATA\es_out_sample_pred.csv"
    output_path = r"C:\Users\dbjin\DATA\svm_ann_target_data.csv"

    # 1) CSV 병합
    df_target = df_svm_target_data(
        path_sharpe=rolling_sharpe_path,
        path_es=es_pred_path,
        save_path=output_path
    )

    # 2) 자산별 절댓값 ES 기반 레이블링
    df_target_labeled = label_by_es(df_target, q_level=0.8, show_plot=True)

    # -------------------------
    # 콘솔 출력 확인
    # -------------------------
    print("\n=== 자산별 행 개수 확인 ===")
    print(df_target.groupby("asset").size())  # 각 자산별 데이터 수

    print("\n=== 데이터 컬럼 확인 ===")
    print(df_target.columns)

    print("\n=== 기본 통계 확인 ===")
    print(df_target.describe())

