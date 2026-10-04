"""몸 동작 인식 확인 프로그램 — 실행 파일.

지금은 3단계: 몸 뼈대 위에 동작 판정(두 팔 들기, 몸 좌우 기울이기) 결과를 보여 준다.
화면 아래 큰 글씨 = 지금 켜진 동작(없으면 NONE), 맨 아래 막대 = 어깨 기울기.
보통은 run.bat(윈도우) / run.command(맥)을 더블클릭해서 실행한다.

화면 숫자 뜻
  CAMERA  : 카메라에서 1초에 받은 사진 수
  LOOP    : 프로그램이 1초에 처리해서 화면에 보여 준 사진 수
  LATENCY : 처리 지연. 사진을 받은 순간부터 화면에 보여 주기 직전까지 걸린 시간(1초 평균, ms)
            카메라·모니터 자체의 지연은 들어 있지 않다.
  INFER   : 그중 MediaPipe 가 몸을 찾는 데 걸린 시간(1초 평균, ms)
  PERSON  : 찾은 사람 수. 아무도 없으면 NO PERSON
끄기: q 키, Esc 키, 창 닫기(X), 터미널에서 Ctrl+C
"""

import sys
import time

import cv2

import config
from camera import Camera, CameraError
from gestures import Frame, Judge, make_gestures
from metrics import RateMeter, RecentAverage, percentile
from overlay import GRAY, GREEN, draw_label, draw_lines, draw_skeleton, draw_tilt_gauge
from pose import PoseDetector, PoseDetectorError

WINDOW = "motion"


def open_camera(args):
    width, height = args.res
    for backend in args.backends:
        print(f"[카메라] {args.camera}번을 엽니다 (방식 {backend.upper()}, {width}x{height} 요청)...")
        camera = Camera(args.camera, width, height, args.fps, backend, args.fourcc)
        try:
            info = camera.open()
        except CameraError as e:
            print(f"[카메라] {e}")
            continue
        print(
            f"[카메라] 열림: {info['width']}x{info['height']} {info['fourcc']} {info['backend']}"
            f" (여는 데 {info['open_seconds']:.1f}초)"
        )
        return camera
    print("  - 윈도우: 줌·팀즈·브라우저처럼 카메라를 쓰는 프로그램을 닫고 다시 실행해 보세요.")
    print("  - 맥: 시스템 설정 > 개인정보 보호 및 보안 > 카메라 에서 '터미널'을 허용한 뒤 다시 실행하세요.")
    print("  - 카메라가 여러 대면 --camera 1 처럼 번호를 바꿔 보세요.")
    return None


def window_closed(state):
    """창 닫기(X)를 눌렀는지. 한 번이라도 보였던 창이 안 보이게 됐을 때만 닫힌 것으로 본다."""
    visible = cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE)
    if visible >= 1:
        state["seen"] = True
        return False
    return state["seen"]


def print_summary(args, camera, loop_frames, started, latency, infer):
    elapsed = time.perf_counter() - started
    if elapsed <= 0 or loop_frames == 0:
        return
    info = camera.info
    print()
    print(f"[요약] 실행 {elapsed:.1f}초, 화면에 보여 준 사진 {loop_frames}장")
    print(f"  LOOP 평균 {loop_frames / elapsed:.1f} fps · CAMERA 평균 {camera.total_frames / elapsed:.1f} fps")
    print(
        f"  처리 지연(LATENCY) 보통 {percentile(latency.history, 0.5):.0f} ms"
        f" · 느린 쪽 5% {percentile(latency.history, 0.95):.0f} ms"
    )
    print(
        f"  몸 찾기(INFER) 보통 {percentile(infer.history, 0.5):.0f} ms"
        f" · 느린 쪽 5% {percentile(infer.history, 0.95):.0f} ms"
        f"  (모델 {args.model}, 최대 {args.num_poses}명)"
    )
    print(
        f"  카메라: {info['width']}x{info['height']} {info['fourcc']} {info['backend']},"
        f" 여는 데 {info['open_seconds']:.1f}초"
    )


def main():
    args = config.parse_args()
    print(f"[몸 인식] 모델 {args.model}, 최대 {args.num_poses}명 준비 중...")
    try:
        detector = PoseDetector(args.model, args.num_poses)
    except PoseDetectorError as e:
        print(f"[몸 인식] {e}")
        return 1
    camera = open_camera(args)
    if camera is None:
        detector.close()
        return 1

    info = camera.info
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, info["width"], info["height"])

    # 사람 자리별 판정 담당. 지금은 자리 0(첫 번째로 찾은 사람) 하나만 쓴다
    judges = {0: Judge(make_gestures(args))}
    loop_rate = RateMeter()
    latency = RecentAverage()
    infer = RecentAverage()
    window_state = {"seen": False}
    started = time.perf_counter()
    loop_frames = 0
    last_seq = 0
    print("[실행] 창이 떴습니다. 끌 때는 창에서 q 를 누르거나 창을 닫으세요.")
    try:
        while True:
            got = camera.latest(last_seq, timeout=1.0)
            if camera.error:
                print(f"[카메라] {camera.error}")
                break
            if got is not None:
                frame, captured_at, last_seq = got
                # 거울처럼 뒤집은 화면에서 몸을 찾는다. 그래야 화면의 왼쪽이 체험자의 왼쪽이 된다
                view = cv2.flip(frame, 1) if args.mirror else frame.copy()

                infer_started = time.perf_counter()
                people = detector.detect(view, captured_at)
                infer_done = time.perf_counter()
                for person in people:
                    draw_skeleton(view, person.landmarks)

                height, width = view.shape[:2]
                results = judges[0].update(Frame(captured_at, people[0] if people else None, width, height))
                active = [r.state for r in results.values() if r.state]
                lean = results["LEAN"]
                draw_tilt_gauge(view, lean.amount, args.lean_enter, args.lean_exit, active=lean.state is not None)
                draw_label(view, " + ".join(active) if active else "NONE", GREEN if active else GRAY)

                now = time.perf_counter()
                latency.add(now, (now - captured_at) * 1000)
                infer.add(now, (infer_done - infer_started) * 1000)
                loop_rate.tick(now)
                loop_frames += 1
                lines = [
                    f"CAMERA {camera.camera_fps()} fps   LOOP {loop_rate.rate(now)} fps"
                    f"   LATENCY {latency.average(now):.0f} ms",
                    f"INFER {infer.average(now):.0f} ms   MODEL {args.model}   "
                    + (f"PERSON {len(people)}" if people else "NO PERSON"),
                    f"{info['width']}x{info['height']} {info['fourcc']} {info['backend']}",
                    *(r.detail for r in results.values()),
                    "q: quit",
                ]
                draw_lines(view, lines)
                cv2.imshow(WINDOW, view)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27) or window_closed(window_state):
                break
    except KeyboardInterrupt:
        print("\n[종료] Ctrl+C")
    finally:
        camera.close()
        detector.close()
        cv2.destroyAllWindows()
        print_summary(args, camera, loop_frames, started, latency, infer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
