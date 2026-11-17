"""팔 동작 (ARMS): 두 팔 들기, 왼팔 들기, 오른팔 들기, 팔 양옆으로 벌리기(T자).

이음제용 상체 동작 4개(11/17 sunbell 결정)를 한 묶음으로 판정한다. 한 묶음 안에서는 상태가
하나만 켜지므로, 두 팔을 들었을 때 한 팔 들기가 같이 켜지는 일이 없다.
(파일 이름은 원래 두 팔 들기만 있을 때 붙인 것이다)

팔 하나를 먼저 넷 중 하나로 본다.
  UP   (들림) 손목이 코보다 위. 손목이 화면 밖이거나 잘 안 보이면 팔꿈치가 어깨보다 확실히 위
             (2026-10-04 sunbell 결정: 손목 또는 팔꿈치 / 11/17 sunbell: 한 팔 들기도 코보다 위)
             거기에 어깨→손목 선이 수평에서 UP_ANGLE(50도) 이상 위를 향해야 한다. 수평에서 살짝 올린 팔을
             막기 위한 것(11/17 sunbell 시험, 두 팔 들기에도 같이 적용하기로 함)
  OUT  (옆)   손목이 어깨 높이 근처에 있고, 어깨에서 바깥쪽으로 충분히 멀리 있음
  DOWN (내림) 손목이 어깨보다 아래(옆으로 벌린 것이 아님)
  MID  (중간) 비스듬히 들었거나, 어느 쪽인지 알 수 없음
두 팔을 짝지어 상태를 정한다.
  UP + UP → ARMS_UP,  UP + DOWN → 들린 쪽의 LEFT_UP / RIGHT_UP,  OUT + OUT → T_POSE
  그 밖(예: 한 팔은 들고 한 팔은 옆, 비스듬히 든 팔)은 아무것도 켜지지 않는다.
왼쪽·오른쪽은 체험자 본인 기준이다(화면을 거울처럼 뒤집은 뒤 판정하므로 화면 왼쪽 = 체험자 왼쪽).

이미 켜져 있을 때는 더 너그럽게 본다(경계에서 깜빡임 방지).
  들림: 어깨 아래로 내려가야 꺼짐 / 옆: 어깨 높이에서 더 많이 벗어나야 꺼짐
"""

import math

from mediapipe.tasks.python.vision import PoseLandmark

from .base import Gesture, Result

# 들림은 높이(손목이 코보다 위)에 더해, 어깨에서 손목으로 가는 선이 수평에서 이만큼 이상 위를 향해야 한다(도).
# 11/17 sunbell 결정: 두 팔 들기에도 같은 조건을 쓴다. 시작값이라 웹캠으로 맞춘다. 이미 켜진 뒤에는 KEEP 이상이면 유지
UP_ANGLE = 50.0
UP_KEEP_ANGLE = 30.0

# 팔꿈치는 어깨보다 "어깨너비 × 이 값"만큼 위에 있어야 든 것으로 본다
ELBOW_MARGIN = 0.15

# 옆으로 벌리기(T자). 숫자는 모두 어깨너비에 곱하는 값(시작값, 11/17)
OUT_REACH = 1.0          # 손목이 어깨에서 바깥쪽으로 이만큼 멀어야 함
OUT_REACH_ELBOW = 0.5    # 손목이 안 보일 때 팔꿈치가 바깥쪽으로 이만큼 멀어야 함
OUT_BAND = 0.5           # 손목(또는 팔꿈치)이 어깨 높이에서 위아래로 이 안에 있어야 켜짐
OUT_BAND_KEEP = 0.8      # 이미 T자로 켜져 있을 때는 이 안에 있으면 유지

# (어깨, 팔꿈치, 손목) — MediaPipe 이름 기준 두 팔
ARMS = [
    (PoseLandmark.LEFT_SHOULDER, PoseLandmark.LEFT_ELBOW, PoseLandmark.LEFT_WRIST),
    (PoseLandmark.RIGHT_SHOULDER, PoseLandmark.RIGHT_ELBOW, PoseLandmark.RIGHT_WRIST),
]

# 상태 → (화면 왼쪽 팔, 화면 오른쪽 팔). 직전 상태에서 팔마다 무엇이었는지 알 때 쓴다
ARM_PAIRS = {
    "ARMS_UP": ("UP", "UP"),
    "LEFT_UP": ("UP", "DOWN"),
    "RIGHT_UP": ("DOWN", "UP"),
    "T_POSE": ("OUT", "OUT"),
}
STATE_OF_PAIR = {pair: state for state, pair in ARM_PAIRS.items()}


def upward_angle(shoulder, point):
    """어깨에서 손목(또는 팔꿈치)으로 가는 선이 수평에서 위로 몇 도 올라갔는지. 수평 0도, 똑바로 위 90도, 아래는 음수."""
    return math.degrees(math.atan2(shoulder.y - point.y, abs(point.x - shoulder.x)))


def arm_kind(shoulder, elbow, wrist, outward, head_y, shoulder_width, was, up_angle=UP_ANGLE, keep_angle=UP_KEEP_ANGLE):
    """팔 하나를 UP / OUT / DOWN / MID 중 하나로. outward: 바깥쪽이 화면 왼쪽이면 -1, 오른쪽이면 +1.

    was: 직전 상태에서 이 팔이 무엇이었는지(없으면 None). 돌려주는 값: (판정에 쓴 부위, 종류)
    """
    if wrist.visible:
        part, point, reach = "wrist", wrist, OUT_REACH
        up = wrist.y < (shoulder.y if was == "UP" else head_y)
    elif elbow.visible:
        part, point, reach = "elbow", elbow, OUT_REACH_ELBOW
        limit = shoulder.y if was == "UP" else shoulder.y - shoulder_width * ELBOW_MARGIN
        up = elbow.y < limit
    else:
        return "none", "MID"
    # 11/17 sunbell: 수평에서 살짝 올린 팔이 UP 으로 판정되는 문제. 높이에 더해 위로 향한 각도도 본다
    if up and upward_angle(shoulder, point) < (keep_angle if was == "UP" else up_angle):
        up = False
    if up:
        return part, "UP"
    band = OUT_BAND_KEEP if was == "OUT" else OUT_BAND
    away = (point.x - shoulder.x) * outward
    if away >= shoulder_width * reach and abs(point.y - shoulder.y) <= shoulder_width * band:
        return part, "OUT"
    if point.y > shoulder.y:
        return part, "DOWN"
    return part, "MID"


class ArmsUp(Gesture):
    name = "ARMS"
    states = ("ARMS_UP", "LEFT_UP", "RIGHT_UP", "T_POSE")

    def __init__(self, up_angle=UP_ANGLE, up_keep_angle=UP_KEEP_ANGLE):
        self.up_angle = up_angle
        self.up_keep_angle = up_keep_angle

    def check(self, frame, history, previous):
        if frame.person is None:
            return Result(detail="ARMS: no person")
        left, right = frame.shoulders()
        if not (left.visible and right.visible):
            return Result(detail="ARMS: shoulders not visible")

        shoulder_width = abs(right.x - left.x)
        nose = frame.point(PoseLandmark.NOSE)
        # 코가 안 보이면 어깨보다 어깨너비 절반만큼 위를 "머리 높이"로 본다
        head_y = nose.y if nose.visible else (left.y + right.y) / 2 - shoulder_width * 0.5
        was_pair = ARM_PAIRS.get(previous, (None, None))

        arms = []   # (화면 x, 어깨, 팔꿈치, 손목)
        for shoulder_id, elbow_id, wrist_id in ARMS:
            shoulder = frame.point(shoulder_id)
            arms.append((shoulder.x, shoulder, frame.point(elbow_id), frame.point(wrist_id)))
        arms.sort(key=lambda arm: arm[0])   # 화면 왼쪽 팔부터

        judged = []   # (부위, 종류)
        for (_, shoulder, elbow, wrist), outward, was in zip(arms, (-1, 1), was_pair):
            judged.append(arm_kind(shoulder, elbow, wrist, outward, head_y, shoulder_width, was,
                                   self.up_angle, self.up_keep_angle))

        state = STATE_OF_PAIR.get((judged[0][1], judged[1][1]))
        text = "  ".join(f"{side} {part} {kind}" for side, (part, kind) in zip("LR", judged))
        return Result(state=state, detail=f"ARMS: {text}")
