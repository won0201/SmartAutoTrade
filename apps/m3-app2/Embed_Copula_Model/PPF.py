import numpy as np
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from data.real_returns import returns

# ============================================
# 2) 주변분포(Marginal Distribution): 경험적 CDF/PIT & 역변환(ECDF-PPF)
# ============================================
def empirical_pit(x: np.ndarray) -> np.ndarray:
    """경험적 CDF 기반 PIT (rank-based)."""
    ranks = stats.rankdata(x, method="average")
    u = (ranks - 0.5) / len(x)  # 순위를 0과 1사이의 값으로 정규화하며(PIT) 경험적 CDF를 적용한 결과이다.
    return u  # PIT로 변환된 값 반환

class EmpiricalPPF:
    def __init__(self, samples: np.ndarray):
        self.sorted = np.sort(samples).astype(float)  # 오름차순으로 정렬
        self.grid = (np.arange(1, len(samples) + 1) - 0.5) / len(samples)

    def ppf(self, u: np.ndarray) -> np.ndarray:
        u = np.asarray(u, dtype=float)  # float로 명시적으로 변환
        return np.interp(u, self.grid, self.sorted)


if __name__ == "__main__":
    df = pd.read_csv(r"C:\Users\dbjin\DATA\real_returns.csv")

    selected_assets = ["Samsung", "Hyundai", "SKHynix", "Kakao", "Naver"]
    N = len(selected_assets)
    fig, axes = plt.subplots(N, 3, figsize=(15, 4 * N))

    x_dict = {}
    u_dict = {}
    x_recovered_dict = {}


    for name in returns.columns:
         x = returns[name].dropna().values
         x = np.round(x, 6)  # 소수점 정밀도를 높인다.
         x = pd.Series(x).drop_duplicates().values  # 중복을 제거한다.

         u = empirical_pit(x)
         ppf_model = EmpiricalPPF(x)
         x_recovered = ppf_model.ppf(u)

         x_dict[name] = x   #수익률 배열
         u_dict[name] = u   #PIT 변환된 배열
         x_recovered_dict[name] = x_recovered # PPF역변환된 배열

         # 1) Original data distribution
    for i, name in enumerate(returns.columns):
        sns.histplot(x, bins=30, kde=True, ax=axes[i, 0], color="steelblue")
        axes[i, 0].hist(x, bins=30, alpha=0.7, color="steelblue")
        axes[i, 0].set_title(f"{name} Original data distribution", fontsize=13)

        # 2) PIT transformation (균등분포)
    for i, name in enumerate(returns.columns):
        sns.histplot(u, bins=30, kde=True, ax=axes[i, 1], color="darkorange")
        axes[i, 1].hist(u, bins=30, alpha=0.7, color="orange")
        axes[i, 1].set_title(f"{name} PIT trans (Uniform[0,1])")

        # 3) Original data distribution vs PPF (Q-Q plot)
    for i, name in enumerate(returns.columns):
        axes[i, 2].scatter(x, x_recovered, alpha=0.5, color="seagreen", s=15)
        axes[i, 2].plot([min(x), max(x)], [min(x), max(x)], "r--", lw=1.5)
        axes[i, 2].set_title(f"{name} original data distribution vs PPF", fontsize=13)

     # PIT 변환
    u = empirical_pit(x)

    # PPF 역변환
    ppf_model = EmpiricalPPF(x)
    x_recovered = ppf_model.ppf(u)

    def plot_ppf(x, y):
        plt.plot(x, y)


    plt.tight_layout()
    plt.show()

    print(type(x))
    print(x[:5])
