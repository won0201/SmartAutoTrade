# confidence_manager.py
"""
SIGMA A 프로젝트 - 실전 신뢰도 계산 엔진

입력:
    - model_scores: 각 모델의 신호 값 리스트 (ex: [-0.2, 0.1, 0.05, ...])
    - meta_probability: 0~1 확률값 (ensemble_score 기반 softmax)

출력:
    - agreement: 모델 방향 일치율 (0~1)
    - variance: 모델 산포도 (0~1 역전환)
    - final_confidence: 최종 신뢰도 (0~1)
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class ConfidenceResult:
    agreement: float
    variance: float
    meta_probability: float
    final_confidence: float


class ConfidenceManager:

    def compute(self, model_scores, meta_probability: float) -> ConfidenceResult:
        scores = np.array(model_scores, dtype=float)

        # ----------------------------------------------------
        # 1) 모델 방향 일치율 (agreement)
        # ----------------------------------------------------
        signs = np.sign(scores)
        pos_ratio = np.mean(signs > 0)
        neg_ratio = np.mean(signs < 0)
        agreement = float(max(pos_ratio, neg_ratio))

        # ----------------------------------------------------
        # 2) 산포도 기반 variance (표준편차 → 0~1로 정규화)
        # ----------------------------------------------------
        std = float(np.std(scores))
        variance = float(1.0 - min(std, 1.0))   # std=0일수록 best → 1.0

        # ----------------------------------------------------
        # 3) 메타 확률 (ensemble → softmax 변환)
        # ----------------------------------------------------
        meta_probability = float(max(0.0, min(1.0, meta_probability)))

        # ----------------------------------------------------
        # 4) 최종 confidence 종합
        # ----------------------------------------------------
        final_conf = (
            0.5 * agreement +
            0.3 * variance +
            0.2 * meta_probability
        )

        return ConfidenceResult(
            agreement=agreement,
            variance=variance,
            meta_probability=meta_probability,
            final_confidence=float(max(0.0, min(1.0, final_conf)))
        )
