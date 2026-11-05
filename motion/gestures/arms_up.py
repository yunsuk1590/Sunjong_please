"""두 팔 들기 (ARMS_UP).

팔 하나가 "들렸다"를 이렇게 판정한다(2026-10-04 sunbell 결정: 손목 또는 팔꿈치).
  1) 손목이 잘 보이고 화면 안에 있으면 → 손목이 코보다 위인가
  2) 손목이 화면 밖이거나 잘 안 보이면 → 팔꿈치가 어깨보다 확실히 위인가
두 팔이 모두 들렸으면 ARMS_UP.

이미 켜져 있을 때는 더 너그럽게 본다(경계에서 깜빡임 방지).
  손목: 어깨 아래로 내려가야 꺼짐 / 팔꿈치: 어깨 아래로 내려가야 꺼짐
"""

from mediapipe.tasks.python.vision import PoseLandmark

from .base import Gesture, Result

# 팔꿈치는 어깨보다 "어깨너비 × 이 값"만큼 위에 있어야 든 것으로 본다
ELBOW_MARGIN = 0.15

# (어깨, 팔꿈치, 손목) — MediaPipe 이름 기준 두 팔
ARMS = [
    (PoseLandmark.LEFT_SHOULDER, PoseLandmark.LEFT_ELBOW, PoseLandmark.LEFT_WRIST),
    (PoseLandmark.RIGHT_SHOULDER, PoseLandmark.RIGHT_ELBOW, PoseLandmark.RIGHT_WRIST),
]


class ArmsUp(Gesture):
    name = "ARMS_UP"
    states = ("ARMS_UP",)

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
        was_up = previous == "ARMS_UP"

        arms = []   # (화면 x, 판정에 쓴 부위, 들렸나)
        for shoulder_id, elbow_id, wrist_id in ARMS:
            shoulder = frame.point(shoulder_id)
            elbow = frame.point(elbow_id)
            wrist = frame.point(wrist_id)
            if wrist.visible:
                up = wrist.y < (shoulder.y if was_up else head_y)
                arms.append((shoulder.x, "wrist", up))
            elif elbow.visible:
                limit = shoulder.y if was_up else shoulder.y - shoulder_width * ELBOW_MARGIN
                arms.append((shoulder.x, "elbow", elbow.y < limit))
            else:
                arms.append((shoulder.x, "none", False))

        arms.sort()   # 화면 왼쪽 팔부터
        text = "  ".join(
            f"{side} {part} {'UP' if up else '--'}" for side, (_, part, up) in zip("LR", arms)
        )
        state = "ARMS_UP" if all(up for _, _, up in arms) else None
        return Result(state=state, detail=f"ARMS: {text}")
