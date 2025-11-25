import React from "react";

export default function ChampionModel() {
  return (
    <div className="px-4 py-10 text-gray-100">
      <header className="mb-8">
        <h1 className="text-4xl font-extrabold gradient-text">최종 모델 (CHAMPION MODEL)</h1>
        <div className="text-slate-400 mt-2">
          7개 딥러닝 모델 + XGBoost 앙상블 구조를 기반으로 최종 선정된 CHAMPION MODEL
        </div>
      </header>

      {/* Summary Card */}
      <div className="glass-card p-6 mb-8">
        <h3 className="text-xl font-semibold mb-3">🎯 CHAMPION_MODEL.keras 개요</h3>
        <p className="text-slate-300 leading-relaxed text-sm">
          이 모델은 전체 7개 딥러닝 기반 레짐 분석 모델(LSTM·Transformer·TCN·GRU-Attention 등)의 
          결과를 통합하여 XGBoost로 메타 학습한 최종 예측 모델입니다.
        </p>

        <ul className="mt-4 space-y-2 text-slate-300 text-sm">
          <li>• 입력 특징: 전처리된 KOSPI200 수치형 특징 + 모델별 시그널 + Confidence</li>
          <li>• 출력: 레짐 스코어(−1 ~ +1), 방향성 판단 및 집중도(score)</li>
          <li>• 구조: Deep Feature Ensemble → XGBoost → Sigmoid/Linear Regression</li>
          <li>• 활용: MarketDashboard의 최종 스코어 생성</li>
        </ul>
      </div>

      {/* Architecture */}
      <div className="glass-card p-6 mb-8">
        <h3 className="text-lg font-semibold mb-4">🧠 CHAMPION MODEL 구조</h3>
        <ul className="space-y-2 text-slate-300 text-sm">
          <li>1) 7개 개별 모델에서 나온 시그널(signal)·신뢰도(confidence)를 입력</li>
          <li>2) 전처리된 시장 데이터(스케일링)와 함께 Feature Vector 구성</li>
          <li>3) XGBoost Regressor가 Feature Importance 기반으로 통합 예측</li>
          <li>4) 회귀값을 최종 score로 변환 → MarketDashboard에 표시</li>
        </ul>
      </div>

      {/* Why this model */}
      <div className="glass-card p-6 mb-8">
        <h3 className="text-lg font-semibold mb-3">📌 왜 챔피언 모델인가?</h3>

        <p className="text-slate-300 text-sm leading-relaxed">
          전 모델 조합을 학습한 결과, XGBoost 기반 앙상블 모델이
          단일 모델 대비 더 높은 안정성과 일반화 성능을 달성했습니다.
          실제 시뮬레이션과 과거 데이터 백테스트에서도 
          변동성이 큰 구간에서 더 안정적인 방향성 판단을 보여 
          SIGMA의 최종 의사결정 모델로 선정되었습니다.
        </p>
      </div>

      {/* Confidence Explanation */}
      <div className="glass-card p-6 mb-8">
        <h3 className="text-lg font-semibold mb-3">🔍 Confidence(신뢰도) 계산 방식</h3>
        <p className="text-slate-300 text-sm leading-relaxed">
          CHAMPION MODEL에서 사용하는 신뢰도는 다음 세 요소로 구성됩니다:
        </p>

        <ul className="mt-3 space-y-2 text-slate-300 text-sm">
          <li>• 모델 출력을 둘러싼 로지스틱 기반 확률 변환</li>
          <li>• 7개 모델의 Signal Agreement(동일 방향성) 비율</li>
          <li>• 최근 구간 성능(rolling accuracy)의 가중치 반영</li>
        </ul>

        <p className="text-slate-400 text-xs mt-2">
          → 이 값은 단순 평균이 아니라 과거 구간별 “예측 적중률 기반 가중치”를 반영한 수치입니다.
        </p>
      </div>

      {/* Footer */}
      <footer className="text-center text-slate-600 mt-12 text-sm">
        CHAMPION_MODEL.keras는 SIGMA 시스템의 최신 버전입니다.  
        재학습 및 개선이 가능하도록 구조가 모듈화되어 있습니다.
      </footer>
    </div>
  );
}
