# 맥 개발 환경 세팅 안내 (yunsuk1590의 Claude용)

> **이 문서는?** yunsuk1590의 **맥북**에서 **아두이노(차 코드)**와 **MediaPipe(몸 동작 코드)**를 개발할 수 있게 환경을 맞추는 순서입니다. **yunsuk1590의 Claude가 이 문서를 읽고, yunsuk1590에게 물어 가며 처음부터 끝까지 진행**할 수 있게 썼습니다.
> - **누가 읽나요?** yunsuk1590의 Claude가 주로 읽습니다. yunsuk1590과 팀장 sunbell도 읽습니다.
> - **작성**: 2026-11-23, sunbell(Claude 도움).
> - **이 문서는 어디에 있나요?** `sunbell/team` 브랜치의 `docs/mac-dev-setup.md`입니다. 레포를 받기 전에는 깃허브 주소로 읽습니다: <https://github.com/yunsuk1590/Sunjong_please/blob/sunbell/team/docs/mac-dev-setup.md>
> - **맥에서는 아직 아무도 이 프로그램들을 돌려 본 적이 없습니다.** 윈도우(sunbell 노트북)에서만 확인했습니다. 그래서 이 문서의 맥 쪽 내용 가운데 「짐작」이라고 쓴 곳은 해 보고 결과를 알려 주세요.
> - **공개 레포입니다.** 이메일, IP 주소, 블루투스 모듈 주소, 실명은 레포에 적지 않습니다.
> - 처음 보는 말은 맨 아래 「9 · 낱말 풀이」에 있습니다.

**yunsuk1590이 자기 Claude에게 붙여 넣을 말 (예)**

```
https://github.com/yunsuk1590/Sunjong_please/blob/sunbell/team/docs/mac-dev-setup.md 를 처음부터 끝까지 읽고,
그 문서의 「0 · Claude에게 먼저」를 지키면서 내 맥에 개발 환경을 맞춰 줘. 설치하기 전에는 꼭 나에게 물어봐.
```

## 0 · Claude에게 먼저 (꼭 지킬 것)

1. **이 문서를 끝까지 읽은 뒤** 시작합니다. 시작할 때 「무엇을 할지」를 세 줄로 yunsuk1590에게 보여 주고 확인을 받습니다.
2. **묻는 방법은 [아두이노 담당 작업 안내](arduino-brief.md)의 「yunsuk1590에게 질문하며 진행하기」를 그대로 따릅니다.** 한 번에 1~3개만, 쉬운 말로, 선택지와 추천을 붙여 묻습니다.
3. **설치, 다운로드, 계정 설정은 하기 전에 yunsuk1590의 허락을 받습니다.** 무엇을 어디서 받는지(이름, 주소, 크기)를 먼저 보여 줍니다. 「2 · 점검」의 명령은 읽기만 하므로 묻지 않고 해도 됩니다.
4. **비밀번호와 토큰은 Claude가 입력하지 않습니다.** 맥 관리자 비밀번호, 깃허브 토큰은 yunsuk1590이 직접 넣습니다.
5. **브랜치 규칙**
   - yunsuk1590이 고치는 곳은 **`yunsuk1590/arduino`(차 코드)**와 **`yunsuk1590/motion`(몸 동작 코드)** 두 브랜치뿐입니다(2026-11-23 sunbell 결정).
   - `main`과 `sunbell/…` 브랜치는 **읽기만** 합니다(`git fetch`, `git show`). 그 브랜치로 push하거나 합치지 않습니다.
   - 커밋과 push는 커밋 메시지를 보여 주고 yunsuk1590의 허락을 받은 뒤에 합니다.
6. **바꾸지 않는 것**: 부품 버전(`motion/requirements.txt`, 특히 mediapipe를 1.0.1로 올리지 않음), 맥 보안 설정(Gatekeeper, SIP 끄기), 키트 교육 자료를 레포에 올리기. 바꿔야 할 것 같으면 「sunbell과 정할 것」으로 yunsuk1590에게 알립니다.
7. **해 봐야 아는 것은 짐작하지 않습니다.** 카메라 화면, 차의 움직임, 포트 목록은 yunsuk1590에게 보거나 해 보고 알려 달라고 합니다.
8. **끝날 때** 「7 · 끝났다고 볼 때」의 표를 채우고, sunbell에게 보낼 보고를 yunsuk1590에게 줍니다.

## 1 · 한눈에 보기: 다 맞추면 이렇게 됩니다

| 항목 | 맞춘 모습 | 팀 기준(확인한 곳) |
|---|---|---|
| 맥 | Apple 칩(M1 이후), macOS 13 이상 | 인텔 맥이나 macOS 12 이하에는 지금 몸 동작 부품이 설치되지 않습니다 |
| git | 설치됨, 깃허브에 push할 수 있음 | push 비밀번호 자리에는 토큰(Personal access token)을 넣습니다 |
| 파이썬 | **3.11**(권장 3.11.9, python.org의 macOS universal2 설치 프로그램) | 3.12 이상은 안 됩니다. sunbell 노트북은 3.11.6으로 확인 |
| Arduino IDE | **2.3.10**(Apple Silicon용) | sunbell이 쓰는 판(차 코드 README 「3」) |
| 보드 설정 | Arduino AVR Boards **1.8.8**, 보드 「Arduino Uno」(`arduino:avr:uno`) | 같음 |
| 모터 라이브러리 | **Adafruit Motor Shield library 1.0.1**(V1, 코드에서는 `AFMotor`). 「V2」가 아닌 것 | 같음. 레포에는 넣지 않음 |
| 레포 폴더 | 레포 하나에 폴더 둘: **`Sunjong_arduino`**(`yunsuk1590/arduino`), **`Sunjong_motion`**(`yunsuk1590/motion`) | sunbell 노트북도 브랜치마다 폴더를 나눠 씁니다(git worktree) |
| 몸 동작 프로그램 | `Sunjong_motion/motion`에서 `setup.command` 성공, `run.command`로 카메라 화면과 동작 인식 | 맥에서는 처음입니다 |
| 차 코드 | `car_race`가 맥에서 컴파일되고, 차에 올라감 | sunbell 노트북에서 7,370바이트(22%) |

- 두 폴더로 나누는 이유: 한 폴더에서 브랜치를 바꾸면 `motion/.venv`(설치한 부품) 같은 파일이 남거나 섞여서 헷갈립니다. 폴더를 나누면 각자 그대로 둘 수 있습니다(Claude 제안).

## 2 · 점검 (읽기만 하는 명령, 묻지 않고 해도 됨)

맥의 「터미널」 앱에서 하나씩 실행하고, 결과를 표로 정리해 yunsuk1590에게 보여 줍니다.

| 무엇을 보나 | 명령 | 좋은 결과 |
|---|---|---|
| macOS 판 | `sw_vers` | `ProductVersion` 13 이상 |
| 칩 | `uname -m` | `arm64` |
| git | `git --version` | 판 번호가 나옴. 안 나오고 설치 창이 뜨면 「3-1」 |
| 파이썬 3.11 | `python3.11 --version` | `Python 3.11.x` |
| Homebrew(있으면) | `brew --version` | 없어도 됩니다 |
| Arduino IDE | `ls /Applications | grep -i arduino` | `Arduino IDE.app` |
| 아두이노 명령 도구 | `ls "/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/"` | `arduino-cli`가 보임(IDE에 들어 있음, 경로는 짐작) |
| 포트 | `ls /dev/cu.*` | 차 보드를 꽂으면 `cu.usbserial-…` 또는 `cu.wchusbserial-…`이 생김 |
| 이미 받아 둔 레포 | `ls ~ ~/Desktop ~/Documents 2>/dev/null | grep -i sunjong` | 있으면 어디인지 yunsuk1590에게 확인 |

- 이미 받아 둔 레포가 있으면 그 폴더에서 `git status`와 `git branch -a`를 보고, **올리지 않은 변경이 있는지** yunsuk1590에게 알립니다. 있으면 무엇인지 묻고, 지우거나 덮어쓰지 않습니다.

## 3 · 설치 (하나씩, 허락을 받고)

「2」에서 없는 것만 설치합니다.

### 3-1 · git
- 터미널에서 `xcode-select --install`을 실행하면 맥이 개발 도구(git 포함) 설치 창을 띄웁니다. 창의 「설치」는 yunsuk1590이 누릅니다.
- 처음 커밋하기 전에 커밋에 남을 이름을 정합니다. 값은 yunsuk1590에게 받아서 넣고, 레포 문서에는 적지 않습니다.
  ```
  git config --global user.name "깃허브 아이디"
  git config --global user.email "깃허브에 등록한 이메일"
  ```
  이미 설정되어 있으면(`git config --global user.name`으로 확인) 바꾸지 않습니다.

### 3-2 · 파이썬 3.11.9
- <https://www.python.org/downloads/release/python-3119/> 의 「macOS 64-bit universal2 installer」를 받아 설치합니다. yunsuk1590이 설치 창을 진행합니다.
- 설치 뒤 `python3.11 --version`으로 확인합니다.
- Homebrew가 이미 있으면 `brew install python@3.11`도 됩니다(`setup.command`가 찾습니다). 둘 중 하나만 합니다.
- 인증서 설치(`Install Certificates.command`)는 하지 않아도 됩니다(몸 동작 인계 문서).

### 3-3 · Arduino IDE 2.3.10
- 공식 사이트 <https://www.arduino.cc/en/software> 에서 **2.3.10**의 Apple Silicon용을 받습니다. 최신판이 2.3.10보다 높으면, 높은 판을 써도 되는지 yunsuk1590에게 묻고 판 번호를 기록합니다(sunbell과 판이 달라도 보통 컴파일 결과는 같습니다, 짐작).
- 설치 뒤 IDE를 한 번 엽니다. 그다음 보드와 라이브러리를 깝니다. IDE 안에서 해도 되고, 아래 명령으로 해도 됩니다.
  ```
  CLI="/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli"
  "$CLI" core update-index
  "$CLI" core install arduino:avr@1.8.8
  "$CLI" lib install "Adafruit Motor Shield library@1.0.1"
  ```
  - `CLI` 경로가 없으면 IDE 안에서 합니다: 보드 관리자 → 「Arduino AVR Boards」 1.8.8, 라이브러리 관리자 → 「Adafruit Motor Shield library」 1.0.1(「V2」가 아닌 것).
- **USB 드라이버는 먼저 설치하지 않습니다.** 맥은 이 보드의 USB 칩(CH340)을 따로 설치하지 않아도 알아보는 경우가 많습니다. 차 보드를 꽂고 `ls /dev/cu.*`에 새 이름이 안 생길 때만 sunbell에게 알립니다.

## 4 · 레포와 브랜치 (폴더 둘)

같은 레포를 폴더 두 개로 씁니다. 폴더를 둘 곳(예: `~/Projects`)은 yunsuk1590에게 묻습니다. 이미 받아 둔 레포가 있으면 새로 받지 않고 그 폴더를 `Sunjong_arduino` 자리로 씁니다(「2」에서 확인).

```
cd ~/Projects
git clone https://github.com/yunsuk1590/Sunjong_please.git Sunjong_arduino
cd Sunjong_arduino
git switch yunsuk1590/arduino
git fetch origin
git worktree add -b yunsuk1590/motion ../Sunjong_motion origin/sunbell/motion
```

- 각 줄: 폴더로 가기 → 레포를 `Sunjong_arduino`라는 이름으로 받기 → 그 폴더로 들어가기 → 자기 차 코드 브랜치로 가기(깃허브에 이미 있음, 11/11 `fdc6850`) → 최신 정보 받기 → 몸 동작 브랜치 `yunsuk1590/motion`을 `sunbell/motion`의 마지막 커밋에서 새로 만들어 `Sunjong_motion` 폴더에 꺼내기
- `yunsuk1590/motion`을 깃허브에도 만들려면 push가 필요합니다. **허락을 받고** `Sunjong_motion` 폴더에서 `git push -u origin yunsuk1590/motion`을 합니다. 토큰은 yunsuk1590이 넣습니다.
- 팀 문서는 브랜치를 바꾸지 않고 읽습니다: `git show origin/sunbell/team:docs/arduino-brief.md`

## 5 · 아두이노 쪽 확인 (`Sunjong_arduino`)

**5-1 · 컴파일만 해 보기** (차가 없어도 됨)
- 터미널을 새로 열었다면 「3-3」의 `CLI="…"` 줄을 먼저 다시 실행합니다(`$CLI`는 그 터미널 창에서만 기억됩니다).
- 협동 레이싱 차 코드 `car_race`는 `sunbell/arduino` 브랜치에 있습니다. 자기 브랜치에 아직 없으므로, 먼저 **레포 밖의 임시 폴더**로 꺼내 컴파일해 봅니다(레포는 바꾸지 않음).
  ```
  mkdir -p /tmp/car_race
  git show origin/sunbell/arduino:arduino/car_race/car_race.ino > /tmp/car_race/car_race.ino
  "$CLI" compile --fqbn arduino:avr:uno /tmp/car_race
  ```
- 「프로그램 저장 공간 … 7,370바이트(22%)」 근처가 나오면 sunbell과 같은 환경입니다(11/23 `1070e15` 기준. 코드가 바뀌면 숫자도 바뀝니다).
- `car_race`를 자기 브랜치의 `arduino/car_race/`로 복사해 이어서 고칠지는 [아두이노 담당 작업 안내](arduino-brief.md) 「어디서 고치나」를 따르고, 하기 전에 yunsuk1590에게 확인합니다.

**5-2 · 차에 올리기** (차가 옆에 있고 yunsuk1590이 허락할 때만)
- 차 보드를 USB로 꽂고 `ls /dev/cu.*`로 새로 생긴 이름을 찾습니다.
  ```
  "$CLI" compile --fqbn arduino:avr:uno -u -p /dev/cu.여기에찾은이름 /tmp/car_race
  "$CLI" monitor -p /dev/cu.여기에찾은이름 -c baudrate=9600
  ```
- 모니터에 「car_race 시작: 멈춤 상태. …」가 나오면 성공입니다. 모니터는 Ctrl+C로 닫습니다(포트는 한 번에 한 프로그램만 씁니다).
- 이 차에 지금 무엇이 올라가 있는지, 바꿔 올려도 되는지 먼저 yunsuk1590에게 묻습니다. 차마다 올라간 코드는 차 코드 README 「9」에 있습니다.

**5-3 · 맥용 시험 스크립트**
- sunbell 쪽 시험 스크립트 `send_keys.ps1`은 윈도우 PowerShell용이라 맥에서는 못 씁니다. **맥용은 yunsuk1590의 Claude가 만들기로 했습니다**(11/19 sunbell 결정). 하는 일은 같습니다: 글자를 0.15초마다 반복해 보내고, 차의 로그를 시간과 함께 보여 줌.
- 파이썬 + `pyserial`로 만들면, 「6」에서 만든 `Sunjong_motion/motion/.venv`에 `pyserial` 3.5가 이미 들어 있어서 따로 설치하지 않아도 됩니다(Claude 제안). 만들기 전에 어떻게 만들지 yunsuk1590에게 보여 주고 확인을 받습니다.
- 맥에서 HC-06 블루투스 포트가 잡히는지는 아직 아무도 시험하지 않았습니다. 짝을 맺으면 `/dev/cu.`로 시작하는 이름이 생길 것으로 짐작합니다.

## 6 · 몸 동작 쪽 확인 (`Sunjong_motion`)

1. `Sunjong_motion/motion` 폴더에서 설치합니다. Finder에서 `setup.command`를 더블클릭하거나, 터미널에서:
   ```
   cd ~/Projects/Sunjong_motion/motion
   ./setup.command
   ```
   - 끝에 아래가 나오면 팀과 같은 환경입니다.
     ```
       mediapipe 1.0.0 / opencv 5.0.0 / numpy 2.4.6
       mediapipe 1.0.0 / PoseLandmarker OK
     [완료] 준비가 끝났습니다. 이제 run 파일을 더블클릭해서 실행하세요.
     ```
   - 「확인되지 않은 개발자」 경고가 뜨면 파일을 Control-클릭 → 열기. 보안 설정은 끄지 않습니다.
2. 자동 시험(카메라와 차 없이):
   ```
   .venv/bin/python -m unittest test_output test_gestures
   ```
3. 실행: `./run.command` (또는 `run.command` 더블클릭)
   - 「터미널이 카메라에 접근하려고 합니다」가 뜨면 yunsuk1590이 **허용**합니다. 허용한 뒤 영상이 안 나오면 껐다가 다시 켭니다.
   - 화면 위 `CAMERA`, `LOOP` 숫자(초당 장수)와 두 팔 들기·왼팔·오른팔·T자가 `ARMS_UP`, `LEFT_UP`, `RIGHT_UP`, `T_POSE`로 나오는지 yunsuk1590에게 봐 달라고 합니다. 끄기는 창에서 `q`.
   - 끌 때 터미널에 찍히는 요약(LOOP 평균, CAMERA 평균, 처리 지연)을 받아 둡니다. **맥에서 처음 돌린 결과라 sunbell에게 꼭 보냅니다**(팀 안건 「개발 6 · 팀원 컴퓨터」).
- 자세한 설정과 화면 읽는 법은 `motion/README.md`, 개발할 때 알아 둘 것은 `docs/handover.md`(둘 다 `yunsuk1590/motion` 폴더 안에 있음)에 있습니다.

## 7 · 끝났다고 볼 때

아래 표를 채워 yunsuk1590에게 보여 주고, 같은 내용을 sunbell에게 보낼 보고로 만듭니다.

| 항목 | 결과 |
|---|---|
| macOS 판 / 칩 | |
| git, 파이썬(판 번호), Arduino IDE(판 번호) | |
| AVR 보드 1.8.8, Adafruit Motor Shield library 1.0.1 | |
| 폴더 두 개와 브랜치(`yunsuk1590/arduino`, `yunsuk1590/motion`), push 됐는지 | |
| `car_race` 컴파일 크기(바이트, %) | |
| 차에 올렸는지, 모니터 첫 줄 | (했으면) |
| `setup.command` 마지막 두 줄 | |
| 자동 시험 결과(몇 개 통과) | |
| `run.command` 요약(LOOP 평균, CAMERA 평균, 처리 지연), 네 동작이 잡혔는지 | |
| 막힌 것, sunbell과 정할 것 | |

## 8 · 막히면

| 증상 | 해 볼 것 |
|---|---|
| `setup.command`가 「파이썬 3.11을 찾지 못했습니다」 | 「3-2」. 3.12 이상만 깔려 있으면 3.11을 따로 깝니다(함께 있어도 됩니다) |
| 부품 설치 중 mediapipe가 안 깔림 | 인텔 맥이나 macOS 12 이하인지 「2」를 다시 봅니다. 그렇다면 sunbell에게 알립니다 |
| 몸 인식을 시작하자마자 꺼짐 | mediapipe가 1.0.1이 아닌지 봅니다(1.0.1은 맥에서 바로 꺼짐). `setup.command`를 다시 실행하면 1.0.0으로 맞춰집니다 |
| 카메라 화면이 안 나옴 | 시스템 설정 → 개인정보 보호 및 보안 → 카메라에서 「터미널」을 허용. 카메라를 쓰는 다른 앱을 닫음 |
| 차 보드를 꽂아도 `/dev/cu.`에 새 이름이 없음 | 다른 USB 선(충전 전용 선이 아닌 것)으로 바꿔 봅니다. 그래도 없으면 sunbell에게 알립니다. 드라이버를 마음대로 깔지 않습니다 |
| 업로드 중 「포트를 열 수 없다」 | 시리얼 모니터나 시험 스크립트가 그 포트를 쓰고 있는지 봅니다 |
| push에서 비밀번호를 물음 | 깃허브 비밀번호가 아니라 토큰을 넣습니다. 만드는 법: <https://docs.github.com/ko/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>. 토큰은 yunsuk1590이 직접 넣습니다 |

## 9 · 낱말 풀이

| 말 | 뜻 |
|---|---|
| 터미널 | 맥에서 글자 명령을 쳐서 프로그램을 실행하는 앱 |
| 브랜치 | 같은 레포 안에서 따로 고치는 줄기. yunsuk1590은 `yunsuk1590/arduino`, `yunsuk1590/motion`에서 일합니다 |
| worktree | 한 레포의 브랜치를 서로 다른 폴더에 따로 꺼내 쓰는 git 기능 |
| `arduino-cli` | Arduino IDE 안에 들어 있는 명령 도구. 터미널에서 컴파일하고 올릴 때 씁니다 |
| 컴파일 | 아두이노 코드를 보드가 알아듣는 형태로 바꾸는 것 |
| 가상환경(`.venv`) | 몸 동작 프로그램 전용 부품 설치 공간 |
| `/dev/cu.…` | 맥에서 보드나 블루투스 모듈과 글자를 주고받는 통로(윈도우의 `COM` 번호) |
| 토큰 | 깃허브에 push할 때 비밀번호 대신 쓰는 열쇠 글자 |
