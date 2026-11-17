"""떨림 방지.

동작 판정(RAW)은 사진 한 장마다 나온다. 사람이 가만히 있어도 관절 점이 조금씩 흔들려서
판정이 한두 장 튀는 일이 있다. 그래서 결과가 **일정 시간 이어져야** 바뀌게 한다(STABLE).

- 켜질 때: 새 상태가 on 초 동안 이어져야 바뀐다.
- 꺼질 때: "없음"이 off 초 동안 이어져야 꺼진다.
- 기다리는 시간만큼 반응이 늦어진다. 안정성과 빠르기는 서로 맞바꾸는 관계다.
- 사람이 잠깐(lost 초보다 짧게) 안 잡히면 결과를 그대로 둔다. lost 초 이상 안 보이면 모두 끈다.
- 짧은 끊김 봐주기(grace): 바뀌려고 기다리는 동안 RAW 가 grace 초보다 짧게 다른 값으로 튀면
  못 본 것으로 치고 기다린 시간을 이어 간다. 0 이면 끊길 때마다 처음부터 다시 기다린다(11/17 전 방식).
"""

DEFAULT_TIMING = (0.15, 0.2)   # 시간을 따로 정하지 않은 동작에 쓰는 (켜짐, 꺼짐) 초
_WAITING_NOTHING = object()    # "바뀌려고 기다리는 상태 없음" 표시(None 은 "동작 없음"이라 따로 둔다)


class GestureStabilizer:
    """동작 하나의 떨림 방지."""

    def __init__(self, on_seconds, off_seconds, grace_seconds=0.0):
        self.on_seconds = on_seconds
        self.off_seconds = off_seconds
        self.grace_seconds = grace_seconds
        self.state = None                      # 지금 인정된 상태(STABLE). None = 동작 없음
        self._candidate = _WAITING_NOTHING     # 바뀌려고 기다리는 상태
        self._since = 0.0                      # 그 상태가 시작된 시각
        self._gap_since = None                 # 기다리는 상태가 끊기기 시작한 시각

    def update(self, raw_state, now):
        started = now
        if self._candidate is not _WAITING_NOTHING and raw_state != self._candidate:
            if self._gap_since is None:
                self._gap_since = now
            if now - self._gap_since < self.grace_seconds:
                return self.state              # 짧은 끊김: 못 본 것으로 치고 계속 기다린다
            started = self._gap_since          # 끊김이 길다: 끊기기 시작한 때부터 새로 센다
        self._gap_since = None
        if raw_state == self.state:
            self._candidate = _WAITING_NOTHING
            return self.state
        if self._candidate is _WAITING_NOTHING or raw_state != self._candidate:
            self._candidate = raw_state
            self._since = started
        wait = self.off_seconds if raw_state is None else self.on_seconds
        if now - self._since >= wait:
            self.state = raw_state
            self._candidate = _WAITING_NOTHING
        return self.state

    def reset(self):
        self.state = None
        self._candidate = _WAITING_NOTHING
        self._gap_since = None


class SlotStabilizer:
    """사람 자리 하나의 떨림 방지. 동작마다 GestureStabilizer 를 하나씩 가진다."""

    def __init__(self, timings, lost_seconds, grace_seconds=0.0):
        self.timings = timings            # {동작 이름: (켜짐 초, 꺼짐 초)}
        self.lost_seconds = lost_seconds
        self.grace_seconds = grace_seconds
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
                self.gestures[name] = GestureStabilizer(*self.timings.get(name, DEFAULT_TIMING),
                                                        self.grace_seconds)
            stable[name] = self.gestures[name].update(result.state, now)
        return stable


def make_stabilizer(args):
    """config 의 시간 설정으로 자리 하나의 떨림 방지를 만든다. 새 동작의 시간은 여기에 한 줄 추가한다."""
    timings = {
        "ARMS": (args.arms_on, args.arms_off),   # 팔 동작 4개(두 팔·왼팔·오른팔·T자)가 함께 씀
        "LEAN": (args.lean_on, args.lean_off),
    }
    return SlotStabilizer(timings, args.lost, args.grace)
