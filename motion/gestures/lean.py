"""몸 좌우 기울이기 (LEAN_LEFT / LEAN_RIGHT).

두 어깨를 잇는 선이 얼마나 기울었는지(어깨 기울기, 도)로 판정한다.
화면 왼쪽 어깨가 내려가면 +, 오른쪽 어깨가 내려가면 - 이다.
  +ENTER 이상 → LEAN_LEFT,  -ENTER 이하 → LEAN_RIGHT  (체험자 본인 기준 왼쪽·오른쪽)
  이미 기울어 있을 때는 EXIT 아래로 돌아와야 꺼진다(경계에서 깜빡임 방지).

비교용으로 몸통 기울기(엉덩이 가운데 → 어깨 가운데 선이 수직에서 기운 정도)도 함께 잰다.
2026-10-04 sunbell 결정: 판정은 어깨 기울기로 하고, 몸통 숫자는 화면에 보여 주기만 한다.
(한 팔만 들어도 어깨가 기울어 LEAN 으로 잘못 뜰 수 있어서, 어느 쪽이 나은지 비교하려는 것)
"""

import math

from mediapipe.tasks.python.vision import PoseLandmark

from .base import Gesture, Result


def shoulder_tilt(frame):
    left, right = frame.shoulders()
    if not (left.visible and right.visible):
        return None
    return math.degrees(math.atan2(left.y - right.y, right.x - left.x))


def torso_tilt(frame):
    left, right = frame.shoulders()
    hip_a, hip_b = frame.point(PoseLandmark.LEFT_HIP), frame.point(PoseLandmark.RIGHT_HIP)
    if not (left.visible and right.visible and hip_a.visible and hip_b.visible):
        return None
    shoulder_x, shoulder_y = (left.x + right.x) / 2, (left.y + right.y) / 2
    hip_x, hip_y = (hip_a.x + hip_b.x) / 2, (hip_a.y + hip_b.y) / 2
    # 어깨 가운데가 엉덩이 가운데보다 화면 왼쪽으로 가면 +
    return math.degrees(math.atan2(hip_x - shoulder_x, hip_y - shoulder_y))


class Lean(Gesture):
    name = "LEAN"
    states = ("LEAN_LEFT", "LEAN_RIGHT")

    def __init__(self, enter=12.0, exit=7.0):
        self.enter = enter   # 이 각도 이상 기울면 켜짐
        self.exit = exit     # 켜진 뒤 이 각도 아래로 돌아오면 꺼짐

    def check(self, frame, history, previous):
        if frame.person is None:
            return Result(detail="LEAN: no person")
        tilt = shoulder_tilt(frame)
        if tilt is None:
            return Result(detail="LEAN: shoulders not visible")
        torso = torso_tilt(frame)

        if previous == "LEAN_LEFT" and tilt > self.exit:
            state = "LEAN_LEFT"
        elif previous == "LEAN_RIGHT" and tilt < -self.exit:
            state = "LEAN_RIGHT"
        elif tilt >= self.enter:
            state = "LEAN_LEFT"
        elif tilt <= -self.enter:
            state = "LEAN_RIGHT"
        else:
            state = None

        torso_text = f"{torso:+.0f} deg" if torso is not None else "-- (hips not visible)"
        detail = f"LEAN: shoulder {tilt:+.0f} deg   torso {torso_text}"
        return Result(state=state, detail=detail, amount=tilt, extra={"torso": torso})
