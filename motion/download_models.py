"""몸 인식 모델 파일을 구글 공식 저장소에서 내려받는다.

보통은 setup 파일(setup.bat / setup.command)이 자동으로 실행한다. 직접 실행하려면:
  윈도우:  .venv/Scripts/python.exe download_models.py        (lite, full 두 개)
  맥:      .venv/bin/python download_models.py heavy          (원하는 것만)

- 주소는 버전(/1/)으로 고정해 두었다. 팀원 컴퓨터에서도 똑같은 파일을 받게 하려는 것이다.
- 받은 뒤 파일 크기를 확인해서, 중간에 끊긴 파일이 남지 않게 한다.
- 받은 파일은 motion/models/ 에 저장되고 깃허브에는 올리지 않는다(.gitignore).
- 인증서는 certifi 부품의 것을 쓴다. python.org 에서 설치한 맥 파이썬은 기본 인증서 설정이 없어
  다운로드가 실패할 수 있기 때문이다.
"""

import shutil
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

MODELS_DIR = Path(__file__).resolve().parent / "models"

# 이름: (주소, 정확한 파일 크기(바이트))
MODELS = {
    "lite": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        5_777_746,
    ),
    "full": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_full/float16/1/pose_landmarker_full.task",
        9_398_198,
    ),
    "heavy": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        30_664_242,
    ),
}
DEFAULT = ["lite", "full"]


def model_path(name):
    return MODELS_DIR / f"pose_landmarker_{name}.task"


def download(name):
    url, size = MODELS[name]
    target = model_path(name)
    if target.exists() and target.stat().st_size == size:
        print(f"[모델] {name}: 이미 있음 ({size:,} 바이트)")
        return
    MODELS_DIR.mkdir(exist_ok=True)
    temp = target.with_suffix(".part")
    print(f"[모델] {name}: 내려받는 중... ({size / 1e6:.1f} MB)")
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=context) as response, open(temp, "wb") as f:
        shutil.copyfileobj(response, f)
    got = temp.stat().st_size
    if got != size:
        temp.unlink()
        raise SystemExit(f"[모델] {name}: 크기가 다릅니다 ({got:,} / {size:,} 바이트). 다시 실행해 주세요.")
    temp.replace(target)
    print(f"[모델] {name}: 완료 → {target}")


if __name__ == "__main__":
    names = sys.argv[1:] or DEFAULT
    for n in names:
        if n not in MODELS:
            raise SystemExit(f"모르는 모델 이름: {n} (가능: {', '.join(MODELS)})")
        download(n)
