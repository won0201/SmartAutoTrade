from typing import Optional
import numpy as np
import cvxpy as cp
import matplotlib.pyplot as plt
import pandas as pd
# =========================================================
# 6) CVaR(ES) 제약 최소분산 최적화
# =========================================================
def optimize_minvar_with_cvar_cap(
        R_scen: np.ndarray,  # (S x N) 시뮬레이션 수익률 행렬 (S개 시나리오, N자산)
        alpha: float,  # CVaR 신뢰수준 (예: 0.95)
        es_cap: float,  # 허용 가능한 CVaR(ES) 상한값
        cov_ref: Optional[np.ndarray] = None,  # 레퍼런스 공분산행렬 (없으면 샘플로)
        allow_short: bool = False,  # 숏 허용 여부
        l2_reg: float = 1e-8,  # 정규화(수치 안정성용)
        solver: str = "ECOS",
) -> dict:

    R_scen = np.asarray(R_scen, dtype=np.float64) #넘파이 어레이로 변환
    es_cap = float(es_cap)
    S, N = R_scen.shape

    if cov_ref is None:
        cov_ref = np.cov(R_scen.T, bias=True).astype(np.float64)
    Sigma = cov_ref + l2_reg * np.eye((cov_ref.shape[0]))
    Sigma = 0.5 * (Sigma + Sigma.T)  # 대칭 보정

    w = cp.Variable(N)  # 포트폴리오 가중치 #다차원 정의
    t = cp.Variable()  # VaR(quantile) 근사값
    z = cp.Variable(S, nonneg=True)  # slack 변수 (tail 손실 초과분)

    losses = -R_scen @ w  # 포트폴리오 손실 힘수 정의
    cvar = t + (1.0 / ((1.0 - alpha) * S)) * cp.sum(z) # ES계산

    cons :  list[cp.Constraint] = []
    cons.append(cp.sum(w) == 1.0)  # 가중치 합 = 1

    if not allow_short:
            cons.append(w >= 0)
    cons.append(z >= losses - t)
    cons.append(cvar <= es_cap) # 지정해둔 es상한 이하로 제한                                                          ->  제약 조건을 빽뺵하게 해두면 리밸런싱이 적게 이루어져 최종 결과 리밸런싱 1번 수행

    prob = cp.Problem(cp.Minimize(cp.quad_form(w, Sigma)), cons) #목적함수
    prob.solve(solver=solver, verbose=False) #  solver로 최적화 실행

    print("타입(losses):", type(losses))
    print("타입(z >= losses - t):", type(z >= losses - t))
    print("타입(cvar <= es_cap):", type(cvar <= es_cap))

    print("\nCVaR 최적값:", np.round(cvar.value, 6))
    print("VaR(t) 최적값:", np.round(t.value, 6))

    if prob.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(f"Optimization failed: status={prob.status}")

    return {
        "status": prob.status,
        "weights": w.value,  # 최적 가중치
        "cvar": cvar.value,  # 실제 계산된 CVaR
        "t": t.value,  # VaR 임계값
        "objective": prob.value,  # 최소분산 값
    }

if __name__ == "__main__":
    # === 1) 테스트 데이터 생성 === # N, S = 5, 1000 #mu = np.zeros(N)  #Sigma_true = 0.0001 * (0.5 * np.ones((N, N)) + 0.5 * np.eye(N)) #R_scen = np.random.multivariate_normal(mu, Sigma_true, size=S)

    # 1) CSV에서 실제 수익률 불러오기
    df_returns = pd.read_csv(r"C:\Users\dbjin\DATA\real_returns.csv",
                            index_col=0, parse_dates=True)

    # 2) OOS/외표본 데이터 선택 (예: 2025년 예측 구간)
    df_oos = df_returns["2025-01-01":]  # 외표본

    # 3) numpy array 형태로 변환
    R_scen = df_oos.values  # (S x N) #외표본 데이터 x 자산 수 #시나리오에서의 수익률

    # === 2) 최적화 실행 ===
    alpha = 0.95 #ES의 신뢰수준
    es_cap = 0.04 #상한값
    res = optimize_minvar_with_cvar_cap(R_scen, alpha=alpha, es_cap=es_cap)

    # === 3) 결과 출력 ===
    print("최적화 상태:", res["status"])
   # print("최소분산:", res["objective"])
    print("\n포트폴리오 변동성:", np.sqrt(res["objective"]))
    print("가중치:", np.round(res["weights"], 4))

    # === 3) 시각화 ===
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # (a) 최적화 가중치 pie chart
    weights = res["weights"]
    labels = [col for col in df_returns.columns[:len(weights)]]  # 실제 자산명
    axes[0].pie(weights, labels=labels, autopct="%1.1f%%", startangle=90)
    axes[0].set_title("Optimized asset weight(Pie Chart)")

    # (b) 손실분포 + VaR / CVaR 라인
    port_losses = -R_scen @ res["weights"]
    VaR = np.quantile(port_losses, alpha)
    CVaR = port_losses[port_losses >= VaR].mean()

    axes[1].hist(port_losses, bins=50, alpha=0.6, color="skyblue", density=True)
    axes[1].axvline(VaR, color="red", linestyle="--", label=f"VaR({alpha * 100:.0f}%)")
    axes[1].axvline(CVaR, color="darkred", linestyle="-", label=f"CVaR ≈ {CVaR:.4f}")
    axes[1].axvline(es_cap, color="green", linestyle=":", label=f"ES cap {es_cap}")
    axes[1].set_title("portfolio loss distribution")
    axes[1].legend()

    plt.tight_layout()
    plt.show()

