"""동작 규칙의 공통 모양.

동작 하나 = 파일 하나. 각 동작은 Gesture 를 이어받아 check() 하나만 만들면 된다.
check() 는 사진 한 장(Frame)을 보고 "어느 상태인지"(예: "LEAN_LEFT", 아니면 None)를 돌려준다.

- 좌표는 픽셀로 바꿔서 쓴다. MediaPipe 의 x, y 는 가로·세로 비율이라 그대로 각도를 재면
  화면 모양(4:3, 16:9)에 따라 값이 달라지기 때문이다.
- 왼쪽·오른쪽은 "화면에서 보이는 쪽"으로 정한다. 화면은 거울처럼 보여 주므로
  화면 왼쪽이 곧 체험자 본인의 왼쪽이다. (MediaPipe 의 LEFT/RIGHT 이름은 거울 화면에서 뒤바뀐다)
- history 에는 최근 약 2초의 Frame 이 들어 있다. 제자리 달리기 같은 반복 동작은 이것을 보면 된다.
"""

from dataclasses import dataclass, field

from mediapipe.tasks.python.vision import PoseLandmark

VISIBLE = 0.5   # 이보다 잘 안 보이는 점은 판정에 쓰지 않는다


@dataclass
class Point:
    x: float          # 픽셀
    y: float          # 픽셀 (아래로 갈수록 커진다)
    visible: bool     # 잘 보이고, 화면 안에 있는가


@dataclass
class Frame:
    """판정에 쓰는 사진 한 장의 정보. 사람이 없으면 person 이 None."""
    time: float
    person: object
    width: int
    height: int

    def point(self, landmark):
        """관절 하나를 픽셀 좌표로. landmark 예: PoseLandmark.NOSE"""
        p = self.person.landmarks[landmark]
        inside = 0.0 <= p.x <= 1.0 and 0.0 <= p.y <= 1.0
        seen = p.visibility is None or p.visibility >= VISIBLE
        return Point(p.x * self.width, p.y * self.height, inside and seen)

    def shoulders(self):
        """두 어깨를 (화면 왼쪽, 화면 오른쪽) 순서로."""
        a, b = self.point(PoseLandmark.LEFT_SHOULDER), self.point(PoseLandmark.RIGHT_SHOULDER)
        return (a, b) if a.x <= b.x else (b, a)


@dataclass
class Result:
    state: object = None                  # 동작 상태 이름(예: "ARMS_UP"), 해당 없으면 None
    detail: str = ""                      # 화면에 보여 줄 설명 한 줄(영어)
    amount: object = None                 # 동작의 "정도"(예: 기울기 각도). 없으면 None
    extra: dict = field(default_factory=dict)


class Gesture:
    name = "GESTURE"     # 동작 이름(목록·화면에 쓰임)
    states = ()          # 나올 수 있는 상태 이름들

    def check(self, frame, history, previous):
        """frame: 지금 사진, history: 최근 약 2초의 Frame 들, previous: 이 동작의 직전 상태.

        previous 를 쓰면 "켜질 때 기준"과 "꺼질 때 기준"을 다르게 둘 수 있다(경계에서 깜빡임 방지).
        """
        raise NotImplementedError
