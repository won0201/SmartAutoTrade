# signal_store.py
"""
SIGMA A 프로젝트 - 최근 신호 저장소
순환 import 방지 & 단순 저장/조회 역할만 담당
"""

from typing import List, Dict
from collections import deque

# 최근 신호 버퍼 (최대 500개 저장)
_SIGNAL_BUFFER = deque(maxlen=500)


def append_signal(sig: Dict):
    """
    새로운 신호를 저장한다.
    """
    _SIGNAL_BUFFER.append(sig)


def get_recent_signals(limit: int = 120) -> List[Dict]:
    """
    최근 N개 신호 반환.
    limit<=0 이면 전체 반환.
    """
    if limit <= 0:
        return list(_SIGNAL_BUFFER)
    return list(_SIGNAL_BUFFER)[-limit:]
