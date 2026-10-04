"""속도와 지연을 재는 도우미.

- 화면에 보여 줄 숫자는 최근 1초 동안의 값으로 계산한다(숫자가 덜 흔들리게).
- 프로그램을 끌 때는 전체 기록으로 '보통 값(중간값)'과 '느린 쪽 5%' 값을 낸다.
"""

import time
from collections import deque


class RateMeter:
    """최근 1초 동안 몇 번 일어났는지(초당 횟수)."""

    def __init__(self):
        self._times = deque()

    def tick(self, now):
        self._times.append(now)

    def rate(self, now=None):
        now = time.perf_counter() if now is None else now
        while self._times and now - self._times[0] > 1.0:
            self._times.popleft()
        return len(self._times)


class RecentAverage:
    """최근 1초 동안 값들의 평균. 전체 기록도 모아 둔다."""

    def __init__(self):
        self._recent = deque()
        self.history = []

    def add(self, now, value):
        self._recent.append((now, value))
        self.history.append(value)

    def average(self, now):
        while self._recent and now - self._recent[0][0] > 1.0:
            self._recent.popleft()
        if not self._recent:
            return 0.0
        return sum(v for _, v in self._recent) / len(self._recent)


def percentile(values, fraction):
    """값들을 작은 순서로 세웠을 때 fraction(0~1) 위치의 값. 0.5 = 중간값, 0.95 = 느린 쪽 5% 경계."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))
    return ordered[index]
