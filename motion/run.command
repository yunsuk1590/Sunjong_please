#!/bin/bash
# 더블클릭해서 실행. 설정을 바꾸려면 터미널에서 ./run.command --res 1280x720 처럼 붙인다.
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
    echo "[안내] 아직 준비가 안 됐습니다. 먼저 setup.command 를 더블클릭하세요."
else
    .venv/bin/python run.py "$@"
fi

echo
read -r -p "Enter 를 누르면 창이 닫힙니다..."
