# signal_generator.py
import json
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================================
# ★ 5단계 신호를 위한 임계값 설정
# ==========================================================
STRENGTH_Q_THRESHOLD = 0.70  # 1차 필터: 상위 30%만 통과
CONFIDENCE_THRESHOLD_CAUTIOUS = 0.55 # 2차 필터: 55% 이상 '조심스러운'
CONFIDENCE_THRESHOLD_STRONG = 0.80   # 2차 필터: 80% 이상 '강한'
STRENGTH_MAX_CAP = 20.0 # 강도 상한선 (비정상적인 폭발 방지)

# (100% 버그 관련 설정 모두 삭제)

def generate_signal(*, 
                    empirical_confidence: float, # ★ 1. '경험적 신뢰도'를 직접 받음
                    mu, var, last_price, strength, 
                    recent_strengths, 
                    recent_prices, # (사용 안 함)
                    ir_var=None, ir_rv=None
                    # (vol_recent 사용 안 함)
                    ):
    
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 강도(Strength) Capping (폭발 방지)
    original_strength = strength # 로그용
    capped_strength = min(strength, STRENGTH_MAX_CAP) # 계산용
    
    # 2. 기본 방향 결정
    direction = "매수" if mu > last_price else "매도"

    # 3. 1차 필터 (강도)
    strengths_list = list(recent_strengths) + [capped_strength]
    strengths = pd.Series(strengths_list) 
    
    if len(strengths) >= 20:
        q_strength = strengths.quantile(STRENGTH_Q_THRESHOLD)
    else:
        q_strength = max(2.0, strengths.mean() + strengths.std(ddof=0))
        
    pass_stage1 = (capped_strength >= q_strength)
    
    # ==========================================================
    # ★★★ [수정] 2차 필터 (신뢰도) ★★★
    # ==========================================================
    # 1. main.py로부터 주입받은 '경험적 신뢰도'를 사용
    emp_conf = empirical_confidence
    # ==========================================================

    # 5. 5단계 신호 결정 (사유 포함)
    failure_reason = ""
    if not pass_stage1:
        final_action = "관망"
        failure_reason = f"1차 필터(강도) 탈락 (Strength {capped_strength:.2f} < q{int(STRENGTH_Q_THRESHOLD*100)} {q_strength:.2f})"
    else:
        if emp_conf >= CONFIDENCE_THRESHOLD_STRONG:
            final_action = "강한 " + direction
            failure_reason = "필터 통과 (Strong)"
        elif emp_conf >= CONFIDENCE_THRESHOLD_CAUTIOUS:
            final_action = "조심스러운 " + direction
            failure_reason = "필터 통과 (Cautious)"
        else:
            final_action = "관망"
            failure_reason = f"2차 필터(신뢰도) 탈락 (Conf {emp_conf:.2f} < {CONFIDENCE_THRESHOLD_CAUTIOUS})"

    # 6. 로그 출력 (사유 포함)
    confidence_percent = emp_conf * 100
    
    # (수정) "경험적" 신뢰도임을 로그에 명시
    print(f"➡️  {now_ts} | 신호: {final_action} (경험적 신뢰도 {confidence_percent:.1f}%) | 사유: {failure_reason} | (Raw Strength: {original_strength:.2f})")

    # 7. JSON 출력 (사유 포함)
    signal = {
        "signal": final_action,
        "confidence_percent": round(confidence_percent, 2),
        "strength": round(capped_strength, 4),
        "reason": failure_reason,
        "timestamp": now_ts
    }
    
    # 8. Capped된 strength를 main.py로 반환 (1차 필터 버그 수정용)
    return json.dumps(signal, ensure_ascii=False, indent=2), capped_strength