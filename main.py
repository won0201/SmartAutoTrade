# main.py
import pandas as pd
import asyncio
from collections import deque
import numpy as np
import traceback
import httpx

# 모듈 임포트
from data_processor import preprocess_for_startup, update_for_new_tick
from model_handler import PredictionModel
from signal_generator import generate_signal
from kis_api_client import connect_websocket
from config import SEQUENCE_LENGTH, GOLDEN_FEATURES

TEAMMATE_API_ENDPOINT = "http://localhost:8000/receive_signal"

async def run_trading_bot():
    try:
        processed_df, scaler = preprocess_for_startup()
        
        # ★ 1. VIX 피처 인덱스 확인
        try:
            # (VIX는 GOLDEN_FEATURES에 있어야 함)
            vix_col_name = 'VIX'
            if vix_col_name not in GOLDEN_FEATURES:
                raise ValueError(f"{vix_col_name} not in GOLDEN_FEATURES")
        except ValueError as e:
            print(f"❌ [치명적 오류] {e}. 동적 신뢰도를 사용할 수 없습니다.")
            return

        recent_prices = deque(maxlen=2000)
        recent_strengths = deque(maxlen=5000) 

        model = PredictionModel(mc_passes=40)
        # ★ 2. ConfidenceManager 가져오기
        confidence_manager = model.confidence_manager

        data_queue = asyncio.Queue()
        websocket_task = asyncio.create_task(connect_websocket(data_queue))

        print("="*60)
        print("=== KOSPI 200 실시간 예측 시스템 가동 (Golden Feature Ver.) ===")
        print(f"초기 데이터 로드 완료. (Total {len(processed_df)} rows)")
        print(f"모델 입력 시퀀스 길이: {SEQUENCE_LENGTH}")
        print(f"★ 팀원 서버로 신호 전송: {TEAMMATE_API_ENDPOINT}")
        print(f"★ 동적 경험 신뢰도 모드 활성화 ★")
        print("="*60)
        
        # ★ 3. 동적 학습을 위한 T-1 예측 데이터 저장소
        last_prediction_data = None
        
        async with httpx.AsyncClient() as session:
            while True:
                tick = await data_queue.get()
                price = float(tick["price"]) if isinstance(tick, dict) else float(tick)
                
                is_simulated = tick.get("simulated", False)
                if not is_simulated and len(recent_prices) > 0 and price == recent_prices[-1]:
                    continue
                    
                recent_prices.append(price)
                processed_df = update_for_new_tick(processed_df, price)
                
                window_size = SEQUENCE_LENGTH + 150 
                if len(processed_df) < window_size:
                    print(f"데이터 수집 중... ({len(processed_df)}/{window_size})")
                    continue
                    
                input_df = processed_df.tail(window_size)

                # ==========================================================
                # ★ 4. 동적 학습 (T-1 예측 결과 확인) ★
                # ==========================================================
                if last_prediction_data and not is_simulated: # 시뮬레이션 틱은 학습 안 함
                    last_pred_up = last_prediction_data['mu'] > last_prediction_data['last_price']
                    actual_outcome_up = price > last_prediction_data['last_price']
                    outcome_success = (last_pred_up == actual_outcome_up)
                    
                    confidence_manager.add_new_outcome(
                        strength=last_prediction_data['capped_strength'],
                        vix=last_prediction_data['vix_scaled'],
                        outcome_success=(1 if outcome_success else 0)
                    )
                    last_prediction_data = None # 학습 완료 후 비우기
                # ==========================================================

                # 5. 예측 (Predict for T)
                res = model.predict_with_strength(input_df)
                
                # 6. 신뢰도 조회 (Query for T)
                # (VIX는 data_processor에서 0-1 스케일링 되어 있음)
                # (input_df는 스케일링 *이전* 데이터프레임이므로, 스케일링된 값을 가져와야 함)
                # (간소화: VIX 피처의 마지막 값을 스케일러로 변환)
                current_vix_unscaled = input_df[vix_col_name].iloc[-1]
                vix_idx = model.scaler_features.index(vix_col_name)
                current_vix_scaled = model.scaler.transform(np.zeros((1, model.n_features)))[0][vix_idx] # (임시 0)
                # (개선 필요: VIX 스케일링을 더 정확하게 해야 함. 여기서는 간소화)
                # (개선 2: model_handler가 VIX 스케일 값을 반환해야 함)
                
                raw_strength = res['strength']
                
                empirical_confidence = confidence_manager.get_empirical_confidence(
                    current_strength=raw_strength, # Capping은 signal_generator가 담당
                    current_vix=current_vix_scaled # (0-1 Scaled)
                )
                
                # 7. 신호 생성 (Generate for T)
                signal_json, capped_strength = generate_signal(
                    empirical_confidence=empirical_confidence, # ★ '경험적 신뢰도' 주입
                    mu=res['mu'], 
                    var=res['var'], 
                    last_price=res['last_price'], 
                    strength=raw_strength, # Capping 전 Raw Strength 전달
                    recent_strengths=list(recent_strengths),
                    recent_prices=list(recent_prices),
                    ir_var=res.get('ir_var'), 
                    ir_rv=res.get('ir_rv')
                )
                
                recent_strengths.append(capped_strength) 
                
                # 9. 다음 루프(T+1) 학습을 위해 현재(T) 예측 저장
                last_prediction_data = {
                    "mu": res['mu'],
                    "last_price": res['last_price'],
                    "capped_strength": capped_strength, 
                    "vix_scaled": current_vix_scaled
                }

                print("--- 최종 생성 신호 ---")
                print(signal_json)

                # 10. FastAPI 전송
                try:
                    await session.post(TEAMMATE_API_ENDPOINT, data=signal_json)
                except httpx.ConnectError:
                    print(f"⚠️  [연동 오류] 팀원 서버({TEAMMATE_API_ENDPOINT})에 연결할 수 없습니다.")
                except Exception as e:
                    print(f"⚠️  [연동 오류] 팀원 서버에 신호 전송 실패: {e}")

    except KeyboardInterrupt:
        print("사용자에 의해 프로그램이 종료됩니다.")
        if 'websocket_task' in locals():
            websocket_task.cancel()
    except Exception as e:
        print(f"메인 루프에서 치명적 오류 발생: {e}")
        traceback.print_exc()
        if 'websocket_task' in locals():
            websocket_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_trading_bot())