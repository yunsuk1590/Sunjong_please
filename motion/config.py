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
    "up_angle": 50.0,     # 팔 들림: 어깨→손목 선이 수평에서 이 각도(도) 이상 위를 향해야 켜짐(높이 조건에 더해)
    "up_keep_angle": 30.0,  # 팔 들림: 이미 켜진 뒤에는 이 각도 이상이면 유지. 11/17 sunbell: 수평에서 살짝 올린 팔이 UP 으로 뜸 → 시작값, 웹캠으로 맞춤
    # 떨림 방지(초). 결과가 이 시간 동안 이어져야 바뀐다. 기다리는 만큼 반응이 늦어진다
    # 11/5 sunbell 확정("더 안정적으로"): 굼뜨지 않았고, 바뀐 횟수가 RAW 22·24번 → STABLE 6·6번.
    # 부스 리허설 때 다시 확인한다. 처음 시작값은 0.15/0.25, 0.10/0.15 였다
    "arms_on": 0.25,      # 팔 동작(두 팔·왼팔·오른팔·T자): 켜지려면 이만큼 유지. 11/17부터 네 동작이 함께 씀
    "arms_off": 0.35,     # 팔 동작: 꺼지려면 이만큼 사라짐
    "lean_on": 0.20,      # 기울이기: 켜지려면 이만큼 유지
    "lean_off": 0.25,     # 기울이기: 꺼지려면 이만큼 사라짐
    "lost": 0.5,          # 사람이 이만큼 안 보이면 모든 동작을 끈다(더 짧게 안 보이면 그대로 둠). 11/5 sunbell 확정
    "grace": 0.1,         # 짧은 끊김 봐주기: 바뀌려고 기다리는 동안 이보다 짧게 끊기면 기다린 시간을 이어 감(약 3장)
                          # 11/17 sunbell: 0.1초로 만들고 웹캠으로 시험해서 확인. 0 이면 11/17 전 방식(끊기면 처음부터)
    # 글자 보내기(11/11 발표회 시연용). 11/8 sunbell 확정. 자세한 내용은 docs/decisions.md
    "port": "",           # 글자를 보낼 포트(예: COM5). 빈칸이면 보내지 않고 화면과 터미널에만 표시한다
    "baud": 9600,         # 통신 속도. HC-06 과 아두이노 쪽 약속이 9600
    "send_on": "ARMS_UP", # 이 동작이 켜지는 순간 letter_on 을 보낸다
    "letter_on": "F",     # 앞으로
    "letter_off": "",     # 동작이 꺼지는 순간 보낼 글자. 빈칸이면 보내지 않는다(차가 스스로 멈춘다)
    "letter_quit": None,  # 프로그램을 끌 때 한 번 보낸다. 안 적으면 11/11 방식(역할 없음)은 S(멈춤), 역할(P1/P2)은 X(11/19)
                          # 11/19 협동 레이싱에서 S 는 「뒤로」라서 역할을 고르면 S 를 끌 때 보내지 않는다
    # 협동 레이싱(11/19 sunbell 결정). 노트북 한 대에 사람 한 명이 한 역할을 맡는다
    "role": "",           # P1 = 두 팔 들기 W(앞), T자 S(뒤) / P2 = 왼팔 A(왼쪽), 오른팔 D(오른쪽). 빈칸이면 11/11 방식
    "letters": "",        # 동작별 글자를 직접 정함. 예: ARMS_UP=W,T_POSE=S. 적으면 역할의 글자 표 대신 쓴다
    "send_mode": "",      # once = 동작이 켜지는 순간 한 번(리듬게임용, 11/11 방식) / repeat = 켜져 있는 동안 반복(컨트롤러식)
                          # 빈칸이면 역할이나 글자 표를 적었을 때 repeat, 아니면 once
    "repeat_seconds": 0.15,   # repeat 일 때 같은 글자를 이 간격(초)마다 다시 보냄. 차는 약 0.3초 글자가 없으면 입력을 끈다(아두이노 세션 설계)
}

# 역할별 글자 표: 동작 상태 이름 → 글자. 11/19 총괄 제안을 sunbell 이 승인(대문자인지는 아두이노 세션과 확인할 것)
ROLE_LETTERS = {
    "P1": {"ARMS_UP": "W", "T_POSE": "S"},
    "P2": {"LEFT_UP": "A", "RIGHT_UP": "D"},
}
ROLE_CHOICES = ["P1", "P2"]
SEND_MODE_CHOICES = ["once", "repeat"]

MODEL_CHOICES = ["lite", "full"]   # heavy 는 계획에서 뺐다(느리고, setup 이 받지 않음)

BACKEND_CHOICES = ["auto", "dshow", "msmf", "avfoundation", "any"]

STATE_CHOICES = ["ARMS_UP", "LEFT_UP", "RIGHT_UP", "T_POSE", "LEAN_LEFT", "LEAN_RIGHT"]   # gestures/ 의 states. 새 동작을 쓰려면 여기에도 추가한다
SEND_ON_CHOICES = STATE_CHOICES   # gestures/ 의 states. 새 동작을 쓰려면 여기에도 추가한다


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


def parse_letter(text):
    """보낼 글자. 영어·숫자 같은 아스키 글자 하나이거나, 보내지 않으려면 빈칸."""
    if text == "" or (len(text) == 1 and text.isascii()):
        return text
    raise argparse.ArgumentTypeError(f"글자는 F 처럼 하나만 적어 주세요: {text}")


def parse_letters(text):
    """동작별 글자 표. 예: ARMS_UP=W,T_POSE=S. 빈칸이면 빈 표."""
    letters = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        state, _, letter = item.partition("=")
        state = state.strip().upper()
        if state not in STATE_CHOICES or len(letter) != 1 or not letter.isascii():
            raise argparse.ArgumentTypeError(
                f"ARMS_UP=W,T_POSE=S 처럼 적어 주세요(동작 {', '.join(STATE_CHOICES)} / 글자는 하나): {item}")
        letters[state] = letter
    return letters


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
    parser.add_argument("--up-angle", type=float, default=DEFAULTS["up_angle"], help="팔 들림 켜짐 각도(수평에서 위로, 도)")
    parser.add_argument("--up-keep-angle", type=float, default=DEFAULTS["up_keep_angle"], help="팔 들림 유지 각도(도)")
    for name, text in (("arms_on", "팔 동작 켜짐"), ("arms_off", "팔 동작 꺼짐"),
                       ("lean_on", "기울이기 켜짐"), ("lean_off", "기울이기 꺼짐"), ("lost", "사람 없음 처리"),
                       ("grace", "짧은 끊김 봐주기")):
        parser.add_argument("--" + name.replace("_", "-"), type=float, default=DEFAULTS[name],
                            help=f"떨림 방지: {text} 시간(초)")
    parser.add_argument("--compare-grace", action="store_true",
                        help="시험용: 같은 결과를 끊김 봐주기 끔으로도 걸러서, 끝날 때 바뀐 횟수를 나란히 보여 줌")
    parser.add_argument("--port", default=DEFAULTS["port"], help="글자를 보낼 포트, 예: COM5. 없으면 화면에만 표시")
    parser.add_argument("--baud", type=int, default=DEFAULTS["baud"], help="통신 속도")
    parser.add_argument("--send-on", choices=SEND_ON_CHOICES, default=DEFAULTS["send_on"],
                        help="이 동작이 켜지는 순간 글자를 보냄")
    for name, text in (("letter_on", "동작이 켜지는 순간"), ("letter_off", "동작이 꺼지는 순간"),
                       ("letter_quit", "프로그램을 끌 때")):
        parser.add_argument("--" + name.replace("_", "-"), type=parse_letter, default=DEFAULTS[name],
                            help=f"{text} 보낼 글자. 빈칸이면 보내지 않음")
    parser.add_argument("--role", choices=ROLE_CHOICES, default=DEFAULTS["role"] or None,
                        help="협동 레이싱 역할. P1 = 두 팔 W·T자 S / P2 = 왼팔 A·오른팔 D. 적으면 켜져 있는 동안 반복해서 보냄")
    parser.add_argument("--letters", type=parse_letters, default=parse_letters(DEFAULTS["letters"]),
                        help="동작별 글자를 직접 정함. 예: ARMS_UP=W,T_POSE=S (적으면 역할의 글자 표 대신 씀)")
    parser.add_argument("--send-mode", choices=SEND_MODE_CHOICES, default=DEFAULTS["send_mode"] or None,
                        help="once = 켜지는 순간 한 번 / repeat = 켜져 있는 동안 반복. 안 적으면 역할이나 글자 표가 있을 때 repeat")
    parser.add_argument("--repeat-seconds", type=float, default=DEFAULTS["repeat_seconds"],
                        help="repeat 일 때 같은 글자를 다시 보내는 간격(초)")
    parser.set_defaults(mirror=DEFAULTS["mirror"])
    args = parser.parse_args(argv)
    if args.repeat_seconds <= 0:
        parser.error("--repeat-seconds 는 0보다 커야 합니다")
    # 시도할 방식 목록. 직접 고르면 그 방식 하나만 쓴다
    args.backends = auto_backends() if args.backend == "auto" else [args.backend]
    return args
