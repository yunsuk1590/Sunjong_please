#!/bin/bash
# 처음 한 번 더블클릭: 파이썬 3.11 을 찾아 setup_env.py 를 실행한다.
cd "$(dirname "$0")" || exit 1

PY=""
for candidate in python3.11 \
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 \
    /opt/homebrew/bin/python3.11 \
    /usr/local/bin/python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo
    echo "[안내] 파이썬 3.11 을 찾지 못했습니다."
    echo "  https://www.python.org/downloads/release/python-3119/ 에서"
    echo "  \"macOS 64-bit universal2 installer\" 를 받아 설치한 뒤, 이 파일을 다시 더블클릭하세요."
else
    "$PY" setup_env.py
fi

echo
read -r -p "Enter 를 누르면 창이 닫힙니다..."
