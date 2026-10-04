"""설정값을 한곳에 모은 파일.

기본값은 아래 DEFAULTS 에 있다. 실행할 때 명령 뒤에 붙여서 바꿀 수도 있다.
  예)  run.bat --model full
       run.bat --backend dshow
       run.command --camera 1
"""

import argparse
import platform

DEFAULTS = {
    "camera": 0,          # 카메라 번호. 노트북 내장 카메라는 보통 0
    "res": "640x480",     # 카메라에 요청할 해상도(가로x세로). 카메라가 다른 값을 줄 수도 있다
    "fps": 30,            # 카메라에 요청할 초당 장수
    "backend": "auto",    # 카메라 여는 방식. auto = 윈도우는 msmf(안 열리면 dshow), 맥은 avfoundation
    "fourcc": "MJPG",     # dshow 로 열 때 요청할 영상 형식. 카메라가 지원하지 않으면 무시된다
    "mirror": True,       # 화면을 거울처럼 좌우 반전해서 보여 준다
    "model": "full",      # 몸 인식 모델. full = 보통, lite = 가벼움(빠르지만 가만히 있어도 점이 떨림)
                          # 2026-10-04 sunbell 확정: full 이 떨림이 거의 없고 초당 장수도 충분(LOOP 28.9)
    "num_poses": 1,       # 한 번에 찾을 최대 사람 수. 1보다 크면 MediaPipe 의 떨림 줄이기가 꺼진다
    "lean_enter": 22.0,   # 몸 기울이기: 어깨가 이 각도(도) 이상 기울면 LEAN 켜짐
                          # 10/4 sunbell 확정: 12도에서는 한 팔을 끝까지 펴면 그쪽 어깨가 올라가 반대쪽 LEAN 이 켜졌다.
                          # 15·20·25도를 시험했고 25도는 빡빡해서 22도. 자세한 내용은 docs/gesture-rules.md
    "lean_exit": 7.0,     # 몸 기울이기: 켜진 뒤 이 각도 아래로 돌아오면 꺼짐
}

MODEL_CHOICES = ["lite", "full"]   # heavy 는 계획에서 뺐다(느리고, setup 이 받지 않음)

BACKEND_CHOICES = ["auto", "dshow", "msmf", "avfoundation", "any"]


def auto_backends():
    """auto 일 때 차례로 시도할 카메라 여는 방식.

    윈도우는 msmf 를 먼저 쓴다. 2026-10-04 sunbell 노트북 3분 반 시험: 초당 장수는 둘 다 약 30장,
    여는 데 msmf 1.3초·dshow 3.5초. dshow 는 켠 직후 몇 초가 느렸다. msmf 로 안 열리는 카메라를 위해
    dshow 를 다음으로 둔다. (dshow 는 수정본이 쓰던 방식)
    """
    system = platform.system()
    if system == "Windows":
        return ["msmf", "dshow"]
    if system == "Darwin":
        return ["avfoundation"]
    return ["any"]


def parse_resolution(text):
    try:
        width, height = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"해상도는 640x480 처럼 적어 주세요: {text}")
    return width, height


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="몸 동작 인식 확인 프로그램")
    parser.add_argument("--camera", type=int, default=DEFAULTS["camera"], help="카메라 번호")
    parser.add_argument("--res", type=parse_resolution, default=DEFAULTS["res"], help="해상도, 예: 640x480")
    parser.add_argument("--fps", type=int, default=DEFAULTS["fps"], help="요청할 초당 장수")
    parser.add_argument("--backend", choices=BACKEND_CHOICES, default=DEFAULTS["backend"], help="카메라 여는 방식")
    parser.add_argument("--fourcc", default=DEFAULTS["fourcc"], help="윈도우에서 요청할 영상 형식(빈칸이면 요청 안 함)")
    parser.add_argument("--no-mirror", dest="mirror", action="store_false", help="좌우 반전하지 않기")
    parser.add_argument("--model", choices=MODEL_CHOICES, default=DEFAULTS["model"], help="몸 인식 모델")
    parser.add_argument("--num-poses", type=int, default=DEFAULTS["num_poses"], help="한 번에 찾을 최대 사람 수")
    parser.add_argument("--lean-enter", type=float, default=DEFAULTS["lean_enter"], help="기울이기 켜짐 각도(도)")
    parser.add_argument("--lean-exit", type=float, default=DEFAULTS["lean_exit"], help="기울이기 꺼짐 각도(도)")
    parser.set_defaults(mirror=DEFAULTS["mirror"])
    args = parser.parse_args(argv)
    # 시도할 방식 목록. 직접 고르면 그 방식 하나만 쓴다
    args.backends = auto_backends() if args.backend == "auto" else [args.backend]
    return args
