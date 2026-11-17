"""카메라 담당.

따로 도는 작업 줄(스레드)이 카메라에서 계속 사진을 받아, **가장 최근 사진 1장만** 들고 있는다.
처리하는 쪽이 조금 늦어도 카메라에 쌓인 옛날 사진을 차례로 처리하지 않으므로 지연이 쌓이지 않는다.
(윈도우에서는 OpenCV 의 '쌓아 둘 사진 수' 설정이 효과가 없을 가능성이 커서 이렇게 한다.)

카메라를 여는 일은 처음 부른 쪽(메인 작업 줄)에서 한다. 맥은 카메라 권한 요청을
메인 작업 줄에서만 할 수 있기 때문이다.
"""

import threading
import time
from collections import deque

import cv2

BACKENDS = {
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "avfoundation": cv2.CAP_AVFOUNDATION,
    "any": cv2.CAP_ANY,
}


def fourcc_text(value):
    """카메라가 알려 준 영상 형식 숫자를 'MJPG' 같은 글자로 바꾼다. 알 수 없으면 '?'."""
    code = int(value)
    text = "".join(chr((code >> 8 * i) & 0xFF) for i in range(4))
    return text if text.isascii() and text.isalnum() else "?"


class CameraError(RuntimeError):
    pass


class Camera:
    def __init__(self, index, width, height, fps, backend, fourcc=""):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = backend
        self.fourcc = fourcc
        self.info = {}          # 카메라가 실제로 준 값: width, height, fourcc, backend, open_seconds
        self.error = None       # 도중에 영상이 끊기면 사유를 적는다
        self.total_frames = 0
        self._cap = None
        self._thread = None
        self._running = False
        self._cond = threading.Condition()
        self._frame = None
        self._time = 0.0
        self._seq = 0           # 사진 번호. 같은 사진을 두 번 처리하지 않으려고 쓴다
        self._arrivals = deque()

    def open(self):
        started = time.perf_counter()
        cap = cv2.VideoCapture(self.index, BACKENDS[self.backend])
        if not cap.isOpened():
            raise CameraError(f"카메라 {self.index}번을 열지 못했습니다 ({self.backend}).")
        if self.fourcc and self.backend in ("dshow", "msmf"):
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)

        ok, frame = cap.read()
        if not ok:
            cap.release()
            raise CameraError(f"카메라 {self.index}번이 열렸지만 영상이 오지 않습니다.")
        now = time.perf_counter()
        height, width = frame.shape[:2]
        self.info = {
            "width": width,
            "height": height,
            "fourcc": fourcc_text(cap.get(cv2.CAP_PROP_FOURCC)),
            "backend": self.backend.upper(),
            "open_seconds": now - started,
        }
        self._cap = cap
        self._running = True
        self._publish(frame, now)
        self._thread = threading.Thread(target=self._read_loop, name="camera", daemon=True)
        self._thread.start()
        return self.info

    def _read_loop(self):
        failures = 0
        while self._running:
            ok, frame = self._cap.read()
            now = time.perf_counter()
            if not ok:
                failures += 1
                if failures >= 30:
                    with self._cond:
                        self.error = "카메라에서 영상이 더 이상 오지 않습니다."
                        self._cond.notify_all()
                    return
                time.sleep(0.01)
                continue
            failures = 0
            self._publish(frame, now)

    def _publish(self, frame, captured_at):
        with self._cond:
            self._frame = frame
            self._time = captured_at
            self._seq += 1
            self.total_frames += 1
            self._arrivals.append(captured_at)
            self._cond.notify_all()

    def latest(self, after_seq, timeout=1.0):
        """after_seq 보다 새 사진이 오면 (사진, 찍힌 시각, 사진 번호)를 돌려준다. 시간 안에 안 오면 None."""
        with self._cond:
            self._cond.wait_for(
                lambda: self._seq > after_seq or self.error is not None or not self._running,
                timeout,
            )
            if self._seq <= after_seq:
                return None
            return self._frame, self._time, self._seq

    def camera_fps(self):
        """최근 1초 동안 카메라에서 받은 사진 수."""
        now = time.perf_counter()
        with self._cond:
            while self._arrivals and now - self._arrivals[0] > 1.0:
                self._arrivals.popleft()
            return len(self._arrivals)

    def close(self):
        self._running = False
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
