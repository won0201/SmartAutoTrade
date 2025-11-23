# =========================================================
# 4) ES 예측용 피처(X) 생성 (하방의존성 + eq 통계)
# =========================================================
from itertools import combinations # Needed for combinations
import pandas as pd
import numpy as np
import scipy.stats as stats
from typing import Dict
from Embed_Copula_Model.PPF import empirical_pit

def build_features_from_window(window: pd.DataFrame, alpha_tail: float = 0.05) -> Dict[str, float]:
    N = window.shape[1]
    eq_ret = window.mean(axis=1)

    def clayton_theta_from_tau(tau):
        # Clayton copula에서 Kendall's tau ↔ θ 변환
        return 2 * tau / (1 - tau)

    def clayton_lambda_L(theta):
        # Clayton copula의 lower tail dependence λ_L 계산
        return 2 ** (-1 / theta)

    # PIT 변환
    U = np.column_stack([empirical_pit(window.iloc[:, j].values) for j in range(N)])

    # Kendall's tau 통계
    taus = []
    for i, j in combinations(range(N), 2):
        x, y = U[:, i], U[:, j]

        if len(x) < 10 or len(y) < 10 or np.std(x) == 0 or np.std(y) == 0:
            tau_ij = 0.0
        else:
            tau_ij = stats.kendalltau(x, y)[0]
            if np.isnan(tau_ij):
                tau_ij = 0.0
        taus.append(tau_ij)

    tau_mean = float(np.mean(taus)) if taus else 0.0
    tau_max  = float(np.max(taus)) if taus else 0.0
    tau_min  = float(np.min(taus)) if taus else 0.0

    # Clayton λ_L (이론치)
    theta = clayton_theta_from_tau(max(min(tau_mean, 0.99), -0.99)) if tau_mean > 0 else 1e-6
    lam_clayton = clayton_lambda_L(theta) if theta > 0 else 0.0

    # 경험적 λ_L 평균(모든 쌍)
    lam_emp_list = []
    for i, j in combinations(range(N), 2):
        u1, u2 = U[:, i], U[:, j]
        left1, left2 = (u1 < alpha_tail), (u2 < alpha_tail)
        p_left1 = left1.mean()
        lam_emp = (left1 & left2).mean() / p_left1 if p_left1 > 0 else 0.0
        lam_emp_list.append(lam_emp)
    lam_emp_mean = float(np.mean(lam_emp_list)) if lam_emp_list else 0.0

    # 피쳐 계산
    eq_vol_20_series = eq_ret.rolling(20).std()
    eq_vol_20_val = eq_vol_20_series.iloc[-1] if not eq_vol_20_series.empty and pd.notna(eq_vol_20_series.iloc[-1]) else np.nan

    eq_vol_60_series = eq_ret.rolling(60).std()
    eq_vol_60_val = eq_vol_60_series.iloc[-1] if not eq_vol_60_series.empty and pd.notna(eq_vol_60_series.iloc[-1]) else np.nan

    eq_skew_60_series = eq_ret.rolling(60).skew()
    eq_skew_60_val = eq_skew_60_series.iloc[-1] if not eq_skew_60_series.empty and pd.notna(eq_skew_60_series.iloc[-1]) else np.nan

    eq_kurt_60_series = eq_ret.rolling(60).kurt()
    eq_kurt_60_val = eq_kurt_60_series.iloc[-1] if not eq_kurt_60_series.empty and pd.notna(eq_kurt_60_series.iloc[-1]) else np.nan

# 피쳐선택
    feats = {
        "eq_vol_20":  eq_vol_20_val,
        "eq_vol_60":  eq_vol_60_val,
        "eq_skew_60": eq_skew_60_val,
        "eq_kurt_60": eq_kurt_60_val,
        "tau_mean":   tau_mean,
        "tau_max":    tau_max,
        "tau_min":    tau_min,
        "lam_emp_mean": lam_emp_mean,
        "lam_clayton": lam_clayton,
    }
    return feats


