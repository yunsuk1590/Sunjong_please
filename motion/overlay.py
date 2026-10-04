"""화면 위에 글씨를 그린다.

OpenCV 기본 글꼴은 한글을 쓰지 못해서 화면 글씨는 영어로 쓴다.
글씨 뒤에 반투명 검은 상자를 깔아서 밝은 배경에서도 읽기 쉽게 한다.
"""

import cv2
from mediapipe.tasks.python import vision

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE = (255, 255, 255)
GREEN = (80, 220, 80)       # 동작이 켜졌을 때
GRAY = (170, 170, 170)      # NONE
YELLOW = (0, 220, 255)      # 켜짐 기준선
BONE = (230, 230, 230)      # 뼈대 선 색 (BGR)
JOINT = (0, 200, 255)       # 관절 점 색 (주황)
CONNECTIONS = vision.PoseLandmarksConnections.POSE_LANDMARKS
VISIBLE = 0.5               # 이보다 잘 안 보이는 점(가려진 팔 등)은 그리지 않는다


def _visible(point):
    return point.visibility is None or point.visibility >= VISIBLE


def draw_skeleton(image, landmarks):
    """한 사람의 관절 점과 뼈대 선을 그린다."""
    height, width = image.shape[:2]
    pixels = [(int(p.x * width), int(p.y * height)) for p in landmarks]
    thickness = max(2, round(width / 320))
    for c in CONNECTIONS:
        if _visible(landmarks[c.start]) and _visible(landmarks[c.end]):
            cv2.line(image, pixels[c.start], pixels[c.end], BONE, thickness, cv2.LINE_AA)
    for point, xy in zip(landmarks, pixels):
        if _visible(point):
            cv2.circle(image, xy, thickness + 1, JOINT, -1, cv2.LINE_AA)
    return image


def draw_lines(image, lines, origin=(10, 10)):
    """image 왼쪽 위에 여러 줄 글씨를 그린다. 글씨 크기는 화면 가로 크기에 맞춘다."""
    height, width = image.shape[:2]
    scale = max(0.5, width / 1280)
    thickness = max(1, round(scale * 2))
    line_height = int(32 * scale)
    padding = int(8 * scale)

    sizes = [cv2.getTextSize(text, FONT, scale, thickness)[0] for text in lines]
    box_width = max((w for w, _ in sizes), default=0) + padding * 2
    box_height = line_height * len(lines) + padding * 2
    x, y = origin
    x2, y2 = min(width, x + box_width), min(height, y + box_height)

    region = image[y:y2, x:x2]
    region[:] = (region * 0.45).astype(region.dtype)

    for i, text in enumerate(lines):
        baseline_y = y + padding + line_height * (i + 1) - int(8 * scale)
        cv2.putText(image, text, (x + padding, baseline_y), FONT, scale, WHITE, thickness, cv2.LINE_AA)
    return image


def _darken(image, x1, y1, x2, y2):
    height, width = image.shape[:2]
    region = image[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
    region[:] = (region * 0.45).astype(region.dtype)


def draw_label(image, text, color):
    """판정 결과를 화면 아래쪽 가운데에 큰 글씨로 쓴다."""
    height, width = image.shape[:2]
    scale = max(1.0, width / 400)
    thickness = max(2, round(scale * 2))
    (text_width, text_height), baseline = cv2.getTextSize(text, FONT, scale, thickness)
    x = (width - text_width) // 2
    y = height - int(height * 0.14)
    pad = int(10 * scale)
    _darken(image, x - pad, y - text_height - pad, x + text_width + pad, y + baseline + pad)
    cv2.putText(image, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)
    return image


def draw_tilt_gauge(image, tilt, enter, exit, active=False, limit=30.0):
    """화면 맨 아래 기울기 막대.

    가운데가 0도이고, 체험자가 왼쪽으로 기울면 점이 화면 왼쪽으로 간다(거울 화면 기준).
    노란 선 = 켜짐 기준(enter), 회색 선 = 꺼짐 기준(exit). 점은 LEAN 이 켜져 있으면(active) 초록.
    tilt 가 None 이면 점을 그리지 않는다.
    """
    height, width = image.shape[:2]
    center = width // 2
    half = int(width * 0.4)
    y = height - int(height * 0.05)
    bar = max(4, height // 80)
    _darken(image, center - half - 30, y - bar * 3, center + half + 30, y + bar * 3)
    cv2.line(image, (center - half, y), (center + half, y), GRAY, 1, cv2.LINE_AA)

    def x_of(angle):
        angle = max(-limit, min(limit, angle))
        return int(center - angle / limit * half)   # + 는 화면 왼쪽

    for angle, color in ((exit, GRAY), (-exit, GRAY), (enter, YELLOW), (-enter, YELLOW), (0, WHITE)):
        x = x_of(angle)
        cv2.line(image, (x, y - bar * 2), (x, y + bar * 2), color, 1, cv2.LINE_AA)
    scale = max(0.4, width / 1600)
    cv2.putText(image, "L", (center - half - 22, y + 5), FONT, scale, WHITE, 1, cv2.LINE_AA)
    cv2.putText(image, "R", (center + half + 10, y + 5), FONT, scale, WHITE, 1, cv2.LINE_AA)
    if tilt is not None:
        color = GREEN if active else WHITE
        cv2.circle(image, (x_of(tilt), y), bar * 2, color, -1, cv2.LINE_AA)
    return image
