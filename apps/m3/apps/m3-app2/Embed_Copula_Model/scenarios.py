import FinanceDataReader as fdr
import numpy as np
import seaborn as sns
import scipy.stats as stats
import matplotlib.pyplot as plt
import pandas as pd
from itertools import combinations # 조합 함수를 사용하기 위해 추가
from scipy.stats import kendalltau
from copulas.bivariate import Clayton
from typing import Optional
from Embed_Copula_Model.PPF import empirical_pit
from Embed_Copula_Model.PPF import  EmpiricalPPF

# ==========================================
# 3) 시나리오 생성: 클레이톤 코퓰라 + Kendall tau 평균으로 theata 추정 + 주변분포(Marginal Distribution) 역변환 시뮬레이션
# ==========================================
# Clayton Copula 샘플링
def sample_clayton_copula(theta: float, d: int, n: int, rng: Optional[np.random.Generator]=None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    W = rng.gamma(shape=1/theta, scale=1.0, size=n)  # (n,)
    U = rng.uniform(size=(n, d))                     # (n,d)
    V = (1 - np.log(U) / W[:, None]) ** (-1/theta)   # 변환
    return V

#다차원 클레이톤 시나리오 생성
def simulate_scenarios_clayton(returns_window: pd.DataFrame, n_sims: int = 10000, rng: Optional[np.random.Generator]=None) -> np.ndarray:
    X = returns_window.values
    U = np.column_stack([empirical_pit(X[:, j]) for j in range(X.shape[1])])
    ppfs = [EmpiricalPPF(X[:, j]) for j in range(X.shape[1])]

#Kendall tau 평균으로 theta 추정
    taus = []
    for i in range(U.shape[1]):
        for j in range(i+1, U.shape[1]):
            tau_ij = stats.kendalltau(U[:, i], U[:, j])[0]
            if not np.isnan(tau_ij):
                taus.append(tau_ij)
    tau_mean = np.mean(taus)
    theta = max(2 * tau_mean / (1 - tau_mean), 1e-3)  # 안정성 보정

# === Copula 샘플 ===
    U_sim = sample_clayton_copula(theta, U.shape[1], n_sims, rng)

# === Marginal 역변환 ===
    sims = np.column_stack([ppfs[j].ppf(U_sim[:, j]) for j in range(U.shape[1])])
    return sims

# === 사용 예시 (5자산) ===
if __name__ == "__main__":
 """np.random.seed(42)
 df_example = pd.DataFrame(np.random.randn(500,5)*0.01,
                         # columns=[f"Asset_{i+1}" for i in range(5)])
 """

 # 1.시뮬레이션을 동작하도록 csv파일 읽기 코드를 먼저 작성한다.
df_returns = pd.read_csv("../data/real_returns.csv", index_col=0)
sims = simulate_scenarios_clayton(df_returns, n_sims=5000)

# 2.읽어들인 데이터에서 시뮬레이션 데이터로 판다스 데이타프레임으로 sim를 정의한다.(재정의)
df_sims = pd.DataFrame(sims, columns=df_returns.columns)

# 3.Tail dependence plot (좌측 5% 극단 구간) ===
alpha = 0.05
pairs = list(combinations(range(df_sims.shape[1]), 2)) # 모든조합
fig, axes = plt.subplots(1, len(pairs), figsize=(len(pairs)*4, 4))

for ax, (i,j) in zip(axes, pairs):
    # 좌측 5% 극단 구간 선택
    mask = (df_sims.iloc[:,i] < df_sims.iloc[:,i].quantile(alpha)) & \
           (df_sims.iloc[:,j] < df_sims.iloc[:,j].quantile(alpha))
    x_tail = df_sims.iloc[:, i][mask]
    y_tail = df_sims.iloc[:, j][mask]

    sns.kdeplot(x=x_tail, y=y_tail, fill=True, cmap="Pastel1", ax=ax, alpha=0.6, thresh=0.05)
    ax.scatter(x_tail, y_tail, alpha=0.3, s=10, color="Black")
    ax.set_title(f"Tail Dependence: {df_sims.columns[i]} vs {df_sims.columns[j]}")
    ax.set_xlabel(df_sims.columns[i])
    ax.set_ylabel(df_sims.columns[j])

# 의존관계 산점도 그래프
plt.tight_layout()
plt.show()

print("The result of the tail dependency of the real assets", sims.shape)
print(pd.DataFrame(sims, columns=df_sims.columns).head())