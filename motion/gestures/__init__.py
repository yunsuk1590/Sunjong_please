"""동작 목록과 판정 담당.

새 동작을 추가하는 방법
  1) 이 폴더의 arms_up.py 를 복사해 새 파일을 만든다(예: squat.py).
  2) name, states, check() 를 새 동작에 맞게 고친다.
  3) 아래 make_gestures() 의 목록에 한 줄을 추가한다.
  4) 판정 기준을 docs/gesture-rules.md 에 적는다(기준의 원본은 그 문서).
"""

from collections import deque

from .arms_up import ArmsUp
from .base import Frame, Gesture, Result
from .lean import Lean

HISTORY_SECONDS = 2.0   # 반복 동작 판정에 쓸 수 있도록 최근 몇 초를 기억할지


def make_gestures(args):
    """판정할 동작 목록. 새 동작은 여기에 한 줄 추가한다."""
    return [
        ArmsUp(),
        Lean(enter=args.lean_enter, exit=args.lean_exit),
    ]


class Judge:
    """사람 자리 하나의 동작 판정 담당. 자리마다 기록과 직전 상태를 따로 가진다."""

    def __init__(self, gestures):
        self.gestures = gestures
        self.history = deque()
        self.previous = {g.name: None for g in gestures}

    def update(self, frame):
        """사진 한 장을 판정해서 {동작 이름: Result} 를 돌려준다."""
        self.history.append(frame)
        while self.history and frame.time - self.history[0].time > HISTORY_SECONDS:
            self.history.popleft()
        results = {}
        for gesture in self.gestures:
            result = gesture.check(frame, self.history, self.previous[gesture.name])
            self.previous[gesture.name] = result.state
            results[gesture.name] = result
        return results


__all__ = ["Frame", "Gesture", "Judge", "Result", "make_gestures"]
