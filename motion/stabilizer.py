"""떨림 방지.

동작 판정(RAW)은 사진 한 장마다 나온다. 사람이 가만히 있어도 관절 점이 조금씩 흔들려서
판정이 한두 장 튀는 일이 있다. 그래서 결과가 **일정 시간 이어져야** 바뀌게 한다(STABLE).

- 켜질 때: 새 상태가 on 초 동안 이어져야 바뀐다.
- 꺼질 때: "없음"이 off 초 동안 이어져야 꺼진다.
- 기다리는 시간만큼 반응이 늦어진다. 안정성과 빠르기는 서로 맞바꾸는 관계다.
- 사람이 잠깐(lost 초보다 짧게) 안 잡히면 결과를 그대로 둔다. lost 초 이상 안 보이면 모두 끈다.
"""

DEFAULT_TIMING = (0.15, 0.2)   # 시간을 따로 정하지 않은 동작에 쓰는 (켜짐, 꺼짐) 초
_WAITING_NOTHING = object()    # "바뀌려고 기다리는 상태 없음" 표시(None 은 "동작 없음"이라 따로 둔다)


class GestureStabilizer:
    """동작 하나의 떨림 방지."""

    def __init__(self, on_seconds, off_seconds):
        self.on_seconds = on_seconds
        self.off_seconds = off_seconds
        self.state = None                      # 지금 인정된 상태(STABLE). None = 동작 없음
        self._candidate = _WAITING_NOTHING     # 바뀌려고 기다리는 상태
        self._since = 0.0                      # 그 상태가 시작된 시각

    def update(self, raw_state, now):
        if raw_state == self.state:
            self._candidate = _WAITING_NOTHING
            return self.state
        if self._candidate is _WAITING_NOTHING or raw_state != self._candidate:
            self._candidate = raw_state
            self._since = now
        wait = self.off_seconds if raw_state is None else self.on_seconds
        if now - self._since >= wait:
            self.state = raw_state
            self._candidate = _WAITING_NOTHING
        return self.state

    def reset(self):
        self.state = None
        self._candidate = _WAITING_NOTHING


class SlotStabilizer:
    """사람 자리 하나의 떨림 방지. 동작마다 GestureStabilizer 를 하나씩 가진다."""

    def __init__(self, timings, lost_seconds):
        self.timings = timings            # {동작 이름: (켜짐 초, 꺼짐 초)}
        self.lost_seconds = lost_seconds
        self.gestures = {}
        self._missing_since = None

    def update(self, raw_results, person_present, now):
        """raw_results: {동작 이름: Result}. 돌려주는 값: {동작 이름: 인정된 상태 또는 None}"""
        if not person_present:
            if self._missing_since is None:
                self._missing_since = now
            if now - self._missing_since >= self.lost_seconds:
                for g in self.gestures.values():
                    g.reset()
            return {name: g.state for name, g in self.gestures.items()}
        self._missing_since = None
        stable = {}
        for name, result in raw_results.items():
            if name not in self.gestures:
                self.gestures[name] = GestureStabilizer(*self.timings.get(name, DEFAULT_TIMING))
            stable[name] = self.gestures[name].update(result.state, now)
        return stable


def make_stabilizer(args):
    """config 의 시간 설정으로 자리 하나의 떨림 방지를 만든다. 새 동작의 시간은 여기에 한 줄 추가한다."""
    timings = {
        "ARMS_UP": (args.arms_on, args.arms_off),
        "LEAN": (args.lean_on, args.lean_off),
    }
    return SlotStabilizer(timings, args.lost)
