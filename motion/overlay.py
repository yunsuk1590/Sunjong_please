"""화면 위에 글씨를 그린다.

OpenCV 기본 글꼴은 한글을 쓰지 못해서 화면 글씨는 영어로 쓴다.
글씨 뒤에 반투명 검은 상자를 깔아서 밝은 배경에서도 읽기 쉽게 한다.
"""

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE = (255, 255, 255)


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
