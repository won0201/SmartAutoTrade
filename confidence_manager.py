# confidence_manager.py
import pandas as pd
import numpy as np
import os
from config import ARTIFACTS_DIR

EMPIRICAL_DB_PATH = f"{ARTIFACTS_DIR}/empirical_backtest.csv"
MIN_CASES_FOR_CONFIDENCE = 10 # 최소 10건의 과거 사례가 있어야 신뢰도 계산

class ConfidenceManager:
    def __init__(self):
        self.db_path = EMPIRICAL_DB_PATH
        try:
            self.db = pd.read_csv(self.db_path)
            print(f"✅ '경험적 신뢰도 DB' 로드 완료. (초기 {len(self.db)}건)")
        except FileNotFoundError:
            print(f"⚠️ [경고] 'empirical_backtest.csv'를 {ARTIFACTS_DIR}에서 찾을 수 없습니다.")
            print("   -> Colab 10-B 단계를 실행하여 DB 파일을 생성하고 artifacts_golden 폴더에 넣어주세요.")
            print("   -> 경험적 신뢰도 대신 50% 기본값을 사용합니다.")
            self.db = pd.DataFrame(columns=['Strength', 'VIX', 'Outcome_Success'])
        except Exception as e:
            print(f"⚠️ '경험적 신뢰도 DB' 로드 중 오류 발생: {e}")
            self.db = pd.DataFrame(columns=['Strength', 'VIX', 'Outcome_Success'])


    def get_empirical_confidence(self, current_strength: float, current_vix: float) -> float:
        """
        과거 DB(백테스트)를 조회하여 '현재와 비슷한 상황'에서의
        '과거 실제 성공률'을 계산합니다.
        
        :param current_strength: 현재 예측된 강도 (Capped)
        :param current_vix: 현재 시장 VIX (Scaled 0~1)
        :return: 경험적 신뢰도 (0.0 ~ 1.0)
        """
        if self.db.empty:
            return 0.50 # DB 없으면 50% 반환 (기본값)

        # 1. '현재 강도'와 비슷한 과거 사례 필터링
        strength_bin_low = current_strength - 0.5
        strength_bin_high = current_strength + 0.5
        
        # 2. '현재 VIX'와 비슷한 과거 사례 필터링
        vix_bin_low = current_vix - 0.2
        vix_bin_high = current_vix + 0.2
        
        similar_cases = self.db[
            (self.db['Strength'] >= strength_bin_low) &
            (self.db['Strength'] < strength_bin_high) &
            (self.db['VIX'] >= vix_bin_low) &
            (self.db['VIX'] < vix_bin_high)
        ]

        if len(similar_cases) < MIN_CASES_FOR_CONFIDENCE:
            # VIX 조건 없이 Strength만으로 재검색
            similar_cases_strength_only = self.db[
                (self.db['Strength'] >= strength_bin_low) &
                (self.db['Strength'] < strength_bin_high)
            ]
            if len(similar_cases_strength_only) < MIN_CASES_FOR_CONFIDENCE:
                 return 0.50 # 그래도 부족하면 50%
            
            return float(similar_cases_strength_only['Outcome_Success'].mean())
        
        # 3. 과거 실제 성공률(Historical Accuracy) 계산
        empirical_confidence = similar_cases['Outcome_Success'].mean()
        
        return float(empirical_confidence) 

    def add_new_outcome(self, strength: float, vix: float, outcome_success: int):
        """
        (동적 학습) 봇의 실시간 예측 결과를 DB에 추가하고 CSV 파일로 저장합니다.
        """
        try:
            new_record = pd.DataFrame([{
                'Strength': strength, 
                'VIX': vix, 
                'Outcome_Success': outcome_success
            }])
            
            self.db = pd.concat([self.db, new_record], ignore_index=True)
            
            # (매 틱마다 저장하면 느리므로, 100번에 한번 또는 비동기 저장 권장)
            # 여기서는 안정성을 위해 매번 저장
            self.db.to_csv(self.db_path, index=False)
            
            print(f"🧠 [동적 학습] 신규 경험 추가 (Strength: {strength:.2f}, VIX: {vix:.2f}, Success: {outcome_success}). DB 총 {len(self.db)}건")

        except Exception as e:
            print(f"⚠️ [동적 학습] DB 저장 실패: {e}")