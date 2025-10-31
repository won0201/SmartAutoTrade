# kis_api_client.py
import os
import json
import base64
import asyncio
import time
import traceback
from typing import Optional, Dict, Any

import requests
import websockets

# AES-CBC 복호화
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ★ 키/시크릿은 config.py에서 불러옵니다
from config import KIS_APP_KEY, KIS_APP_SECRET

# ---------------------------------------------------------------------------
# 설정: 모의투자 REST/WS 엔드포인트
BASE_URL = os.getenv("KIS_BASE_URL", "https://openapivts.koreainvestment.com:29443")
WEBSOCKET_URL = os.getenv("KIS_WS_URL", "ws://ops.koreainvestment.com:31000")  # 모의투자: 31000

# ---------------------------------------------------------------------------
# 공통 HTTP 유틸
def _post_json(url: str, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
    """POST 요청을 보내고 JSON 응답을 반환하는 헬퍼 함수"""
    default_headers = {"content-type": "application/json; charset=utf-8"}
    if headers:
        default_headers.update(headers)
    resp = requests.post(url, data=json.dumps(body), headers=default_headers, timeout=timeout)
    text = resp.text
    try:
        j = resp.json()
    except Exception:
        raise RuntimeError(f"JSON 디코딩 실패 (status={resp.status_code}): {text[:500]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP 오류 status={resp.status_code}, 응답={j}")
    return j

# ---------------------------------------------------------------------------
# 인증
def get_access_token() -> str:
    """API 접근 토큰 발급"""
    url = f"{BASE_URL}/oauth2/tokenP"  # 모의: tokenP
    body = {"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "appsecret": KIS_APP_SECRET}
    res_json = _post_json(url, body)
    token = res_json.get("access_token")
    if not token:
        raise KeyError(f"API 응답에 'access_token' 없음: {res_json}")
    return token

def get_approval_key() -> str:
    """웹소켓 접속을 위한 실시간 승인 키 발급"""
    url = f"{BASE_URL}/oauth2/Approval"
    body = {"grant_type": "client_credentials", "appkey": KIS_APP_KEY, "secretkey": KIS_APP_SECRET}  # 바디에 포함!
    res_json = _post_json(url, body)
    approval_key = res_json.get("approval_key")
    if not approval_key:
        raise KeyError(f"API 응답에 'approval_key' 없음: {res_json}")
    return approval_key

# ---------------------------------------------------------------------------
# 실시간 메시지 파서 (KOSPI 200 지수 기준)
def parse_realtime_message(plain: str) -> Optional[Dict[str, Any]]:
    """
    실시간 메시지를 파싱하여 'price'와 'timestamp'를 추출합니다.
    (KOSPI 200 지수 'H0STASP0' 기준)
    """
    if not plain or plain[0] not in ("0", "1"):
        return None
    
    parts = plain.split("|")
    if len(parts) < 4:
        return None
    
    tr_id = parts[1]
    
    # KOSPI 200 지수(업종) TR ID
    if tr_id != "H0STASP0":
        return None
        
    try:
        # H0STASP0의 필드 정의에 따라 인덱스 조정 필요
        # (예시: 2번 인덱스가 지수, 3번 인덱스가 시간)
        price = float(parts[2]) # 현재 지수
        ts = parts[3] # 체결 시간
    except Exception:
        return None
        
    return {"tr_id": tr_id, "price": price, "timestamp": ts}

# ---------------------------------------------------------------------------
# 복호화 유틸 (SUBSCRIBE SUCCESS의 key/iv 사용)
def _decrypt_payload(b64_cipher: str, key: str, iv: str) -> Optional[str]:
    """암호화된 실시간 데이터를 복호화합니다."""
    try:
        cipher_bytes = base64.b64decode(b64_cipher)
        cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
        plain = unpad(cipher.decrypt(cipher_bytes), AES.block_size)
        return plain.decode("utf-8", errors="ignore")
    except Exception:
        return None

# ---------------------------------------------------------------------------
# 웹소켓 연결/구독 (메인 로직)
async def connect_websocket(
    data_queue: "asyncio.Queue[Dict[str, Any]]",
    tr_id: str = "H0STASP0",     # KOSPI 200 지수
    tr_key: str = "201",         # KOSPI 200 코드
    auto_reconnect: bool = True,
    reconnect_delay_sec: int = 3,
    watchdog_sec: int = 60,      # N초간 아무 메시지도 없으면 안내 로그
    simulate_if_idle: bool = True,
    simulate_after_sec: int = 30 # N초간 실데이터가 없으면 더미 틱 주입
):
    """
    - KIS 모의투자 웹소켓(31000)에 연결합니다.
    - PINGPONG을 처리하여 연결을 유지합니다.
    - 실시간 데이터를 구독하고 복호화합니다.
    - 파싱된 데이터를 data_queue에 넣습니다.
    - (옵션) 장 마감 시 더미 틱을 주입하여 봇 테스트를 돕습니다.
    """
    print("1. 접근 토큰 발급...")
    access_token = get_access_token()
    print("2. 웹소켓 접속 키 발급...")
    approval_key = get_approval_key()

    # 구독 요청 메시지 (JSON)
    subscribe_req = {
        "header": {
            "approval_key": approval_key,
            "custtype": "P",             # 개인(P)
            "tr_type": "1",              # 1=구독
            "appkey": KIS_APP_KEY,
            "token": f"Bearer {access_token}",
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": tr_id, "tr_key": tr_key}},
    }

    aes_key: Optional[str] = None
    aes_iv: Optional[str] = None

    while True:
        try:
            print(f"3. 웹소켓 연결 시도: {WEBSOCKET_URL}")
            async with websockets.connect(
                WEBSOCKET_URL,
                ping_interval=60,  # 라이브러리 레벨 핑
                ping_timeout=20,
            ) as ws:
                print("   - 웹소켓 연결 성공! 실시간 데이터 수신 대기...")
                await ws.send(json.dumps(subscribe_req))
                print(f"   - 구독 요청 완료: tr_id={tr_id}, tr_key={tr_key}")

                last_any_msg_ts = time.time()   # PINGPONG 포함 '모든' 메시지 기준
                last_realdata_ts = time.time()  # 실데이터(파싱 성공) 기준

                while True:
                    # 메시지 수신 대기
                    raw = await ws.recv()
                    now = time.time()

                    # (워치독) N초 동안 아무 메시지도 없으면 로그 출력
                    if now - last_any_msg_ts > watchdog_sec:
                        print(f"[WS][INFO] {watchdog_sec}초 동안 메시지 없음(장이 닫혔거나 이벤트 부재). 연결 유지 중.")
                        last_any_msg_ts = now

                    # 1. JSON 프레임 (PINGPONG / 구독응답 / 오류 등)
                    if raw and (raw.startswith("{") or raw.startswith("[")):
                        try:
                            obj = json.loads(raw)
                        except Exception:
                            print(f"[WS][JSON-parse-error] {raw[:300]}")
                            last_any_msg_ts = now
                            continue

                        header = obj.get("header", {})
                        tr = header.get("tr_id")

                        # PINGPONG (앱 레벨 Keepalive) -> 수신 즉시 응답
                        if tr == "PINGPONG":
                            await ws.send(raw)
                            print("[WS] PINGPONG ↔ (keepalive)")
                            last_any_msg_ts = now

                            # ★ 더미 틱 주입 (시뮬레이션 옵션) ★
                            # PINGPONG은 장 마감 후에도 계속 오므로,
                            # 여기서 더미 틱 주입 로직을 실행
                            if simulate_if_idle and (now - last_realdata_ts > simulate_after_sec):
                                fake = {
                                    "tr_id": tr_id,
                                    "price": 300.0, # 테스트용 임의 가격
                                    "timestamp": time.strftime("%H:%M:%S"),
                                    "simulated": True
                                }
                                await data_queue.put(fake)
                                print(f"[WS][SIMULATED] {fake}  # 장 마감 테스트용 더미")
                                last_realdata_ts = now # 더미 주입도 수신으로 간주
                            continue

                        # SUBSCRIBE SUCCESS (복호화 키/IV 수신)
                        if tr == tr_id and obj.get("body", {}).get("rt_cd") == "0":
                            out = obj.get("body", {}).get("output", {}) or {}
                            aes_iv = out.get("iv")
                            aes_key = out.get("key")
                            print(f"[WS][SUBSCRIBE] SUCCESS (iv/key 수신 완료)")
                            last_any_msg_ts = now
                            continue

                        # 기타 JSON (오류 등)
                        print(f"[WS][JSON] {raw[:300]}")
                        last_any_msg_ts = now
                        continue

                    # 2. 텍스트 프레임 (실시간 데이터)
                    got_realdata = False
                    if raw:
                        parsed_ok = False

                        # A) 평문 포맷 시도 (e.g., "0|H0STASP0|...")
                        if raw[0] in ("0", "1"):
                            msg = parse_realtime_message(raw)
                            if msg:
                                await data_queue.put(msg)
                                print(f"[WS][PARSED] {msg}")
                                parsed_ok = True
                                got_realdata = True

                        # B) 암호화 포맷 시도 (복호화)
                        if not parsed_ok and aes_key and aes_iv:
                            plain = _decrypt_payload(raw, aes_key, aes_iv)
                            if plain:
                                msg = parse_realtime_message(plain)
                                if msg:
                                    await data_queue.put(msg)
                                    print(f"[WS][PARSED-DECRYPTED] {msg}")
                                    got_realdata = True

                    # 타임스탬프 갱신
                    if raw:
                        last_any_msg_ts = now
                    if got_realdata:
                        last_realdata_ts = now

        except asyncio.CancelledError:
            print("웹소켓 태스크가 취소되었습니다. 종료합니다.")
            raise
        except Exception as e:
            print(f"웹소켓 연결/수신 오류: {e}")
            traceback.print_exc()

        if not auto_reconnect:
            break
        print(f"재연결 대기 {reconnect_delay_sec}초...")
        await asyncio.sleep(reconnect_delay_sec)