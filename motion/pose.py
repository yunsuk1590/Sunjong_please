"""MediaPipe 로 몸 관절 33개 점(랜드마크)을 찾는다.

- MediaPipe 의 몸 인식 기능 PoseLandmarker 를 영상 모드(VIDEO)로 쓴다.
  영상 모드는 앞 사진의 결과를 이어 써서(추적) 한 장씩 따로 찾는 것보다 덜 흔들린다.
- 결과는 처음부터 "사람 목록"으로 돌려준다. 지금은 한 명(num_poses=1)이지만,
  나중에 여러 명이 필요해져도 이 모양은 그대로 둘 수 있다.
- 점의 x, y 는 화면 가로·세로에 대한 비율(0~1)이다. 픽셀로 쓰려면 화면 크기를 곱한다.
"""

from dataclasses import dataclass

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from download_models import model_path

# 이 값보다 확신이 낮으면 사람으로 보지 않는다(구글 기본값)
CONFIDENCE = 0.5


@dataclass
class Person:
    landmarks: list   # 33개 점. 각 점: x, y(화면 비율 0~1), z, visibility(보이는 정도), presence
    world: list       # 같은 33개 점을 미터 단위 3차원 좌표로 (나중에 쓸 수 있음)


class PoseDetectorError(RuntimeError):
    pass


class PoseDetector:
    def __init__(self, model="lite", num_poses=1):
        path = model_path(model)
        if not path.exists():
            raise PoseDetectorError(f"모델 파일이 없습니다: {path.name}. setup 파일을 다시 실행하세요.")
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=CONFIDENCE,
            min_pose_presence_confidence=CONFIDENCE,
            min_tracking_confidence=CONFIDENCE,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)
        self._last_timestamp = -1

    def detect(self, bgr_image, captured_at):
        """사진 한 장에서 사람들을 찾는다. captured_at 은 사진을 찍은 시각(초)."""
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        # 영상 모드는 시각(ms)이 매번 커져야 한다. 같은 값이 나오면 1ms 더한다
        timestamp = max(int(captured_at * 1000), self._last_timestamp + 1)
        self._last_timestamp = timestamp
        result = self._landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
        return [Person(lms, world) for lms, world in zip(result.pose_landmarks, result.pose_world_landmarks)]

    def close(self):
        self._landmarker.close()
