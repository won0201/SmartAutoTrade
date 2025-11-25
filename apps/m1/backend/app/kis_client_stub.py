# KIS API 실제 연동을 위한 모듈 자리 (샘플 스텁)
# 실제로는 Secrets Manager에서 키를 불러오고 REST/WS로 시세를 가져와야 함.

def fetch_latest_price():
    # 샘플: 실제 구현에서는 한국투자증권 Open API 호출
    return {
        "symbol": "KOSPI200",
        "price": 305.2
    }
