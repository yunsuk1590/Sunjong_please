"""처음 한 번 하는 준비: 가상환경 만들기 → 부품 설치 → 모델 받기 → 설치 확인.

보통은 setup.bat(윈도우) / setup.command(맥)을 더블클릭하면 이 파일이 실행된다.
윈도우와 맥이 이 파일 하나로 같은 순서를 밟는다.
여러 번 실행해도 괜찮다. 이미 된 단계는 건너뛴다.
"""

import platform
import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
REQUIRED_PYTHON = (3, 11)
PYTHON_URL = "https://www.python.org/downloads/release/python-3119/"


def venv_python():
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def stop(message):
    print()
    print(f"[중단] {message}")
    sys.exit(1)


def check_computer():
    if sys.version_info[:2] != REQUIRED_PYTHON:
        stop(
            f"파이썬 {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} 이 필요합니다(지금 {platform.python_version()}).\n"
            f"  {PYTHON_URL} 에서 3.11.9 를 설치한 뒤 다시 실행하세요."
        )
    if platform.system() == "Darwin":
        if platform.machine() != "arm64":
            stop(
                "이 맥은 인텔 칩이거나, 파이썬이 인텔용으로 실행되고 있습니다.\n"
                "  지금 쓰는 MediaPipe 는 Apple 칩(M1 이후) 맥에서만 설치됩니다. sunbell 에게 알려 주세요."
            )
        major = int(platform.mac_ver()[0].split(".")[0] or 0)
        if major < 13:
            stop(
                f"macOS {platform.mac_ver()[0]} 입니다. macOS 13(Ventura) 이상이 필요합니다.\n"
                "  sunbell 에게 알려 주세요(부품 버전을 조정해야 합니다)."
            )


def run(step, command):
    print(f"\n{step}")
    result = subprocess.run([str(c) for c in command], cwd=HERE)
    if result.returncode != 0:
        stop(f"위 단계에서 문제가 생겼습니다. 화면의 영어 메시지를 캡처해서 sunbell 에게 보내 주세요.")


def main():
    sys.stdout.reconfigure(line_buffering=True)  # 아래 단계 출력과 순서가 섞이지 않게
    print(f"[준비] 파이썬 {platform.python_version()} · {platform.system()} {platform.machine()}")
    check_computer()

    if venv_python().exists():
        print("\n[1/4] 가상환경: 이미 있음")
        same_version = subprocess.run(
            [str(venv_python()), "-c", f"import sys; sys.exit(sys.version_info[:2] != {REQUIRED_PYTHON})"]
        )
        if same_version.returncode != 0:
            stop(f"이미 있는 가상환경이 다른 파이썬 버전으로 만들어졌습니다.\n  {VENV} 폴더를 지운 뒤 다시 실행하세요.")
    else:
        print("\n[1/4] 가상환경 만드는 중...")
        venv.create(VENV, with_pip=True)

    run("[2/4] 부품 설치 중... (처음에는 몇 분 걸릴 수 있습니다)",
        [venv_python(), "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"])
    run("[3/4] 모델 받는 중...", [venv_python(), "download_models.py"])
    run("[4/4] 설치 확인 중...", [venv_python(), __file__, "--check"])
    print("\n[완료] 준비가 끝났습니다. 이제 run 파일을 더블클릭해서 실행하세요.")


def check_install():
    """가상환경 안에서 실행된다. MediaPipe 가 모델을 불러와 한 장을 처리할 수 있는지 본다."""
    import cv2
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions, vision

    options = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(HERE / "models" / "pose_landmarker_lite.task")),
        running_mode=vision.RunningMode.VIDEO,
    )
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        blank = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((480, 640, 3), np.uint8))
        landmarker.detect_for_video(blank, 0)
    print(f"  mediapipe {mp.__version__} / opencv {cv2.__version__} / numpy {np.__version__}")
    print(f"  mediapipe {mp.__version__} / PoseLandmarker OK")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_install()
    else:
        main()
