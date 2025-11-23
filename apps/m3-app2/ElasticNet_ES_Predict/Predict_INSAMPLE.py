import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import ElasticNetCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from features import build_features_from_window
from Embed_Copula_Model.ES import es
#import scipy.stats as stats
#from itertools import combinations

def in_sample_es_prediction(df_returns: pd.DataFrame,
                            win_feat: int = 500,
                            horizon: int = 20,
                            alpha_es: float = 0.05) -> pd.DataFrame:
    X = []
    for t in range(win_feat, len(df_returns)):
        X.append(df_returns.iloc[t - win_feat:t].values.flatten())  # <-- win_feat 사용

    """
    내표본(in-sample) 기반으로 ElasticNet ES 예측
    """
    N = df_returns.shape[1]

    # 1) Feature 생성
    feats_list = []
    for t in range(len(df_returns)):
        window = df_returns.iloc[:t+1]
        feats = build_features_from_window(window, alpha_tail=0.05)
        feats_list.append(list(feats.values()))
    X = np.array(feats_list)

    # 2) Target ES 계산
    y_list = []
    for t in range(len(df_returns) - horizon):
        future = df_returns.iloc[t:t+horizon]
        y_t_assets = [es(future.iloc[:, j].values, alpha=alpha_es) for j in range(N)]
        y_list.append(y_t_assets)

    X = X[:len(y_list)]
    y = np.array(y_list)

    # ==============================
    # NaN 처리 → 평균값으로 대체
    # ==============================
    # X 처리
    col_means_X = np.nanmean(X, axis=0)
    inds_X = np.where(np.isnan(X))
    X[inds_X] = np.take(col_means_X, inds_X[1])

    # y 처리
    col_means_y = np.nanmean(y, axis=0)
    inds_y = np.where(np.isnan(y))
    y[inds_y] = np.take(col_means_y, inds_y[1])

    # 3) ElasticNet 학습 & 예측
    y_pred = np.zeros_like(y)
    pipe_list = [Pipeline([
                    ("scaler", StandardScaler()),
                    ("enet", ElasticNetCV(
                        alphas=np.logspace(-3,1,30),
                        l1_ratio=[0.3,0.7],
                        cv=5,
                        max_iter=5000
                    ))
                 ]) for _ in range(N)]

    for j in range(N):
        pipe_list[j].fit(X, y[:, j])
        y_pred[:, j] = pipe_list[j].predict(X)

    # 4) DataFrame 변환
    y_pred_df = pd.DataFrame(
        y_pred,
        index=df_returns.index[:len(y_pred)],
        columns=df_returns.columns[:N]
    )
    return y_pred_df

# ==============================
# Main 백테스트
# ==============================
if __name__ == "__main__":
    # 1) CSV 불러오기
    df_returns= pd.read_csv(r"C:\Users\dbjin\DATA\real_returns.csv",index_col=0, parse_dates=True)

    # 2) 내표본 ES 예측
    y_pred_df = in_sample_es_prediction(df_returns,
                                        win_feat=500,
                                        horizon=20,
                                        alpha_es=0.05)

    # 3) 결과 출력
    print("\n=== 내표본 ES 예측 (상위 5행) ===")
    print(y_pred_df.head())
    print("\n=== 내표본 ES 예측 (마지막 5행) ===")
    print(y_pred_df.tail())

    # 4) 시각화
    plt.figure(figsize=(12,6))
    for col in y_pred_df.columns:
        plt.plot(y_pred_df.index, y_pred_df[col], label=col)
    plt.title("In-sample ES prediction (per asset, 2020-2024)")
    plt.xlabel("Date")
    plt.ylabel("Expected Shortfall")
    plt.legend()
    plt.show()

print(df_returns.dtypes)

output_csv = r"C:\Users\dbjin\DATA\es_in_sample_pred.csv"
y_pred_df.to_csv(output_csv)
print(f"ES 예측 결과가 CSV로 저장되었습니다: {output_csv}")
