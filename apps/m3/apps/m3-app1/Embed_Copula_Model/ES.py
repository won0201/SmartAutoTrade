from numpy import ndarray, asarray,quantile
# =========================
# 0) 유틸: ES(CVaR) 계산
# =========================
def es(losses: ndarray, alpha: float = 0.95) -> float:
    """시뮬레이션 손실 배열에서 Expected Shotrfall 계산 공식"""
    losses = asarray(losses)
    var = quantile(losses, alpha)
    tail = losses[losses >= var]
    return float(tail.mean()) if tail.size else float(var)
