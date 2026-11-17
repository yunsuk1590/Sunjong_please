"""팔 동작 판정과 떨림 방지(짧은 끊김 봐주기) 자동 시험. 카메라가 없어도 된다.

motion 폴더에서 실행한다.
  윈도우: .venv\\Scripts\\python.exe -m unittest test_gestures -v
  맥:     .venv/bin/python -m unittest test_gestures -v

관절 위치는 손으로 만든 가짜 값이다. 실제 사람에서 숫자가 맞는지는 웹캠 시험으로 확인한다.
"""

import unittest
from types import SimpleNamespace

from mediapipe.tasks.python.vision import PoseLandmark

from gestures import Frame
from gestures.arms_up import ArmsUp
from stabilizer import GestureStabilizer

WIDTH, HEIGHT = 640, 480
STEP = 1 / 30   # 카메라 사진 한 장 간격(초)

# 화면 왼쪽 팔 기준 자세(픽셀). 어깨너비 64, 어깨 높이 240, 코 높이 200
SHOULDER = (288, 240)
POSES = {
    "up": ((280, 180), (280, 150)),      # (팔꿈치, 손목). 손목이 코보다 위
    "down": ((280, 300), (282, 360)),    # 손목이 어깨보다 한참 아래
    "out": ((240, 240), (190, 245)),     # 손목이 어깨 높이, 바깥으로 어깨너비 1.5배
    "mid": ((260, 225), (230, 205)),     # 비스듬히: 코보다 낮고, 옆으로도 덜 벌림
    "just_above": ((285, 235), (282, 230)),   # 어깨보다 조금 위, 코보다 아래(켜진 뒤 유지 확인용)
    "out_high": ((240, 225), (190, 203)),     # T자보다 어깨너비 0.6배 위, 코보다는 아래(켜진 뒤 유지 확인용)
    "diag": ((258, 222), (228, 195)),         # 손목은 코보다 위지만 비스듬함(위로 약 37도). 11/17 시험에서 UP 으로 뜬 모양
    "flat": ((245, 225), (203, 195)),         # 거의 수평(위로 약 28도). 켜진 뒤 유지 기준(30도)에도 못 미침
    "vee": ((260, 190), (232, 150)),          # V자로 위(위로 약 58도)
    "almost_flat": ((240, 232), (190, 195)),  # 손목은 코보다 위지만 거의 수평(위로 약 36도)
}


def mirror_x(x):
    return WIDTH - x


def frame(left="down", right="down", hide=(), person=True):
    """left/right: 체험자 왼팔(화면 왼쪽)·오른팔 자세 이름. hide: 안 보이게 할 관절 이름들."""
    if not person:
        return Frame(0.0, None, WIDTH, HEIGHT)
    points = [SimpleNamespace(x=0.5, y=0.9, visibility=0.0) for _ in range(33)]

    def put(landmark, xy, name):
        seen = 0.0 if name in hide else 0.99
        points[landmark] = SimpleNamespace(x=xy[0] / WIDTH, y=xy[1] / HEIGHT, visibility=seen)

    put(PoseLandmark.NOSE, (320, 200), "nose")
    # 거울 화면에서는 MediaPipe 의 RIGHT_* 가 화면 왼쪽에 온다
    elbow, wrist = POSES[left]
    put(PoseLandmark.RIGHT_SHOULDER, SHOULDER, "l_shoulder")
    put(PoseLandmark.RIGHT_ELBOW, elbow, "l_elbow")
    put(PoseLandmark.RIGHT_WRIST, wrist, "l_wrist")
    elbow, wrist = POSES[right]
    put(PoseLandmark.LEFT_SHOULDER, (mirror_x(SHOULDER[0]), SHOULDER[1]), "r_shoulder")
    put(PoseLandmark.LEFT_ELBOW, (mirror_x(elbow[0]), elbow[1]), "r_elbow")
    put(PoseLandmark.LEFT_WRIST, (mirror_x(wrist[0]), wrist[1]), "r_wrist")
    return Frame(0.0, SimpleNamespace(landmarks=points), WIDTH, HEIGHT)


def judge(previous=None, **kwargs):
    return ArmsUp().check(frame(**kwargs), [], previous).state


class FourArmStates(unittest.TestCase):
    def test_both_up(self):
        self.assertEqual(judge(left="up", right="up"), "ARMS_UP")

    def test_left_arm_is_the_screen_left_arm(self):
        self.assertEqual(judge(left="up", right="down"), "LEFT_UP")

    def test_right_up(self):
        self.assertEqual(judge(left="down", right="up"), "RIGHT_UP")

    def test_t_pose(self):
        self.assertEqual(judge(left="out", right="out"), "T_POSE")

    def test_nothing_when_arms_down(self):
        self.assertIsNone(judge())

    def test_mixed_poses_turn_nothing_on(self):
        for left, right in (("up", "out"), ("out", "down"), ("up", "mid"), ("mid", "mid"), ("out", "mid")):
            with self.subTest(left=left, right=right):
                self.assertIsNone(judge(left=left, right=right))

    def test_no_person_or_no_shoulders(self):
        self.assertIsNone(judge(person=False))
        self.assertIsNone(judge(left="up", right="up", hide=("l_shoulder",)))

    def test_elbow_used_when_wrist_not_seen(self):
        self.assertEqual(judge(left="up", right="down", hide=("l_wrist",)), "LEFT_UP")
        self.assertEqual(judge(left="out", right="out", hide=("l_wrist", "r_wrist")), "T_POSE")

    def test_arm_unknown_when_wrist_and_elbow_not_seen(self):
        self.assertIsNone(judge(left="up", right="down", hide=("r_wrist", "r_elbow")))

    def test_up_stays_on_until_below_shoulder(self):
        self.assertIsNone(judge(left="just_above", right="just_above"))
        self.assertEqual(judge("ARMS_UP", left="just_above", right="just_above"), "ARMS_UP")
        self.assertEqual(judge("ARMS_UP", left="just_above", right="down"), "LEFT_UP")

    def test_slightly_raised_from_horizontal_is_not_up(self):
        """11/17 sunbell 시험: 거의 수평인 팔을 살짝 올렸더니 RIGHT_UP 이 뜸."""
        for pose in ("diag", "almost_flat"):
            with self.subTest(pose=pose):
                self.assertIsNone(judge(left="down", right=pose))
                self.assertIsNone(judge(left=pose, right=pose))   # 두 팔 들기에도 같은 조건

    def test_v_shape_still_counts_as_up(self):
        self.assertEqual(judge(left="vee", right="vee"), "ARMS_UP")
        self.assertEqual(judge(left="down", right="vee"), "RIGHT_UP")

    def test_angle_has_a_lower_bar_once_on(self):
        self.assertIsNone(judge(left="diag", right="down"))
        self.assertEqual(judge("LEFT_UP", left="diag", right="down"), "LEFT_UP")
        # 유지 기준(30도)도 못 넘으면 꺼진다
        self.assertIsNone(judge("LEFT_UP", left="flat", right="down"))

    def test_angle_settings_can_be_changed(self):
        strict = ArmsUp(up_angle=70.0, up_keep_angle=60.0).check(frame(left="vee", right="down"), [], None).state
        loose = ArmsUp(up_angle=20.0, up_keep_angle=10.0).check(frame(left="diag", right="down"), [], None).state
        self.assertIsNone(strict)
        self.assertEqual(loose, "LEFT_UP")

    def test_t_pose_stays_on_a_little_higher(self):
        self.assertIsNone(judge(left="out_high", right="out_high"))
        self.assertEqual(judge("T_POSE", left="out_high", right="out_high"), "T_POSE")


def run(stabilizer, pattern, start=0.0):
    """pattern: [(상태, 장 수), ...]. 사진마다 STABLE 결과를 모아 돌려준다."""
    now, stable = start, []
    for state, count in pattern:
        for _ in range(count):
            stable.append(stabilizer.update(state, now))
            now += STEP
    return stable


def first_on(stable, state="ARMS_UP"):
    return stable.index(state) if state in stable else None


class ShortGapGrace(unittest.TestCase):
    """11/17 sunbell: 0.1초(약 3장)까지 끊김을 봐주기로 함. 켜짐 0.25초, 꺼짐 0.35초."""

    def make(self, grace):
        return GestureStabilizer(0.25, 0.35, grace)

    def test_one_missed_frame_does_not_restart_the_wait(self):
        pattern = [("ARMS_UP", 5), (None, 1), ("ARMS_UP", 20)]
        with_grace = first_on(run(self.make(0.1), pattern))
        without = first_on(run(self.make(0.0), pattern))
        self.assertEqual(with_grace, 8)    # 0.25초 = 8장째(0부터 셈). 끊긴 한 장도 기다린 시간에 들어감
        self.assertEqual(without, 6 + 8)   # 끊긴 뒤 처음부터 다시 8장

    def test_long_gap_still_restarts(self):
        pattern = [("ARMS_UP", 5), (None, 4), ("ARMS_UP", 20)]   # 4장 = 0.13초 > 0.1초
        self.assertEqual(first_on(run(self.make(0.1), pattern)), 9 + 8)

    def test_short_blips_never_turn_on(self):
        pattern = [("ARMS_UP", 2), (None, 10)] * 5
        self.assertIsNone(first_on(run(self.make(0.1), pattern)))

    def test_short_gap_while_turning_off(self):
        s = self.make(0.1)
        run(s, [("ARMS_UP", 20)])
        stable = run(s, [(None, 6), ("ARMS_UP", 1), (None, 20)], start=1.0)
        self.assertEqual(stable.index(None), 11)   # 꺼짐 0.35초 = 11장째. 튄 한 장이 기다림을 끊지 않음

    def test_other_state_blip_does_not_steal_the_wait(self):
        pattern = [("ARMS_UP", 5), ("LEFT_UP", 2), ("ARMS_UP", 20)]
        stable = run(self.make(0.1), pattern)
        self.assertNotIn("LEFT_UP", stable)
        self.assertEqual(first_on(stable), 8)

    def test_zero_grace_is_the_old_behaviour(self):
        s = self.make(0.0)
        self.assertEqual(first_on(run(s, [("ARMS_UP", 20)])), 8)
        s = self.make(0.0)
        self.assertIsNone(first_on(run(s, [("ARMS_UP", 7), (None, 1)] * 4)))


if __name__ == "__main__":
    unittest.main()
