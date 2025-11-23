from typing import Tuple, Dict, List
import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNetCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from features import build_features_from_window
import matplotlib.pyplot as plt
#from data.syn import generate_synthetic_returns
from Embed_Copula_Model.ES import es

# =========================================================
# 5) Elastic Net: ES 예측기 - 확장(Expanding) 학습으로 외표본 ES 예측값 생성 (자산별)
# =========================================================
def fit_es_predictor_expanding_assets(
        df: pd.DataFrame,
        win_feat: int = 100, #1월~3월까지 학습
        horizon: int = 20,  #앞으로 약 1개월의 ES값을 예측한다.
        es_alpha_target: float = 0.05,
        alpha_tail_feat: float = 0.05,
) -> Tuple[pd.DataFrame, List[Dict[str, float]]]:
    """
    매 시점 t에 대해:
      - 과거 win_feat 기간 window로 X(feat) 구성
      - 각 자산별로 '다음 horizon' 구간 실현 ES 계산 → 학습 샘플 추가
      확장학습은 계속해서 데이터를 추가하는 방식이다.
      - ElasticNetCV(표준화)로 '확장 학습' 후 각 자산별 y_pred 생성
    반환: 시계열 ES
      - y_pred_df: (시점 × 자산) 예측 ES DataFrame
      - feat_list: 각 시점별 피처 dict (공통)
    """
    N = df.shape[1]   # 자산 개수
    X_hist, y_hist = [], []
    idx_list = []
    y_pred_records = []
    feat_list = []

    t0 = win_feat
    T = len(df)

    pipe_list = [None] * N  # 자산별 pipeline 저장

    for t in range(t0, T - horizon):   # range(100, 175-20) = range(100, 155)
        window = df.iloc[t - win_feat:t]
        future = df.iloc[t:t + horizon]

        # 공통 피처 생성
        feats = build_features_from_window(window, alpha_tail=alpha_tail_feat)
        feat_vec = list(feats.values())
        feat_vec_cleaned = np.nan_to_num(feat_vec, nan=0.0)

        # 자산별 target ES 계산
        y_t_assets = []
        for j in range(N):
            asset_future = future.iloc[:, j].values
            y_t_assets.append(es(asset_future, alpha=es_alpha_target))

        # 누적 학습셋에 추가
        X_hist.append(feat_vec_cleaned)
        y_hist.append(y_t_assets)
        idx_list.append(df.index[t])

        # 예측
        y_hat_assets = []
        if len(y_hist) >= 60:  # 최소 샘플 수 확보
            X_np = np.array(X_hist)
            Y_np = np.array(y_hist)  # (샘플 × 자산)

            for j in range(N):
                if pipe_list[j] is None:
                    pipe_list[j] = Pipeline([
                        ("scaler", StandardScaler()),
                        ("enet", ElasticNetCV(
                            alphas=np.logspace(-3, 1, 30),
                            l1_ratio=[0.3, 0.7],
                            cv=5,
                            max_iter=5000
                        ))
                    ])
                pipe_list[j].fit(X_np, Y_np[:, j])
                y_hat = float(pipe_list[j].predict([feat_vec_cleaned])[0])
                y_hat_assets.append(y_hat)
        else:
            # 워밍업 구간 → 과거 평균
            y_hat_assets = np.mean(y_hist, axis=0).tolist()

        y_pred_records.append(y_hat_assets)
        feat_list.append(feats)

    # DataFrame으로 변환 (자산별 열)
    y_pred_df = pd.DataFrame(y_pred_records, index=idx_list, columns=df.columns[:N])
    return y_pred_df, feat_list

if __name__ == "__main__":
    df_returns = pd.read_csv(r"C:\Users\dbjin\DATA\real_returns.csv",
                             index_col=0, parse_dates=True)

    # 외표본 시점 2025-01-01 이후 데이터 선택
    df_out_sample = df_returns[df_returns.index >= "2025-01-01"]
    print("외표본 데이터 shape:", df_out_sample.shape)

    """  #(1) 합성 데이터 생성
    df_returns = generate_synthetic_returns(T=1000, N=5, seed=42)
   """
    #(2) ElasticNet 기반 ES 예측 실행
    y_pred_df, feat_list = fit_es_predictor_expanding_assets(
        df=df_out_sample,
        win_feat=100,
        horizon=20,
        es_alpha_target=0.05,
        alpha_tail_feat=0.05,
    )
    print("\n=== ElasticNet ES 예측 (상위 5행) ===")
    print(y_pred_df.head())
    print("\n=== ElasticNet ES 예측 (마지막 5행) ===")
    print(y_pred_df.tail())

    """
    # 시간에 따른 각 자산별 예측 ES 시각화
    plt.figure(figsize=(12, 6))
    for col in y_pred_df.columns:
        plt.plot(y_pred_df.index, y_pred_df[col], label=col)
    plt.title("ElasticNet based ES prediction (per asset)")
    plt.xlabel("Date")
    plt.ylabel("Expected Shortfall")
    plt.legend()
    plt.show()
    """
    #외표본 결과 시각화
    plt.figure(figsize=(12, 6))
    for col in y_pred_df.columns:  # 컬럼명 = 자산 이름
        plt.plot(y_pred_df.index, y_pred_df[col], label=col)

    plt.title("ElasticNet based ES prediction (out-of-sample, 2025)")
    plt.xlabel("Date")
    plt.ylabel("Expected Shortfall")
    plt.legend()
    plt.show()

output_csv = r"C:\Users\dbjin\DATA\es_out_sample_pred.csv"

y_pred_df.index.name = "Date" # 인덱스 이름을 'Date'로 지정
y_pred_df_reset = y_pred_df.reset_index() # 인덱스를 컬럼으로 변환
y_pred_df_reset.to_csv(output_csv, index=False, encoding="utf-8-sig") # CSV 저장 (index=False로 중복 인덱스 방지)

print(f"외표본 ES 예측 결과 CSV 저장 완료: {output_csv}")