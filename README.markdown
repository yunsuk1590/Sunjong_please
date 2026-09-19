# 가상 게임 컨트롤러 (Virtual Game Controller)

이 프로젝트는 Python과 OpenCV, MediaPipe를 활용하여 손동작 인식 기반의 가상 게임 컨트롤러를 구현합니다. 사용자는 카메라 앞에서 손동작을 통해 게임의 키보드 입력을 제어할 수 있습니다.

## 주요 기능

* 손동작을 통한 키보드 방향키 제어 (상하좌우 + 점프)
* 마우스 제어 모드 지원
* 사용자 설정 가능한 키 매핑
* 직관적인 다크 모드 UI

## 필요 라이브러리

* `opencv-python` - 이미지 처리 및 화면 출력
* `mediapipe` - 손 인식 및 추적
* `numpy` - 배열 처리 및 마우스 위치 계산
* `pynput` - 키보드 및 마우스 입력 제어
* `PyQt5` - 그래픽 사용자 인터페이스
* `pywin32` - 윈도우 시스템 제어
* `pydirectinput` - 게임 호환 키보드 입력

## 설치 방법

1. 저장소를 클론합니다.
   ```bash
   git clone https://github.com/vividhyeok/Vgc-Controler.git
   ```

2. 필요한 라이브러리를 설치합니다.
   ```bash
   pip install -r requirement.txt
   ```

3. Main.py를 실행합니다.
   ```bash
   python Main.py
   ```

## VirtualGameController 활용 방법

`VirtualGameController` 클래스는 손동작 인식과 키보드/마우스 제어 기능을 담당합니다. 이 클래스를 독립적으로 활용하는 방법은 다음과 같습니다:

```python
from VirtualGameController import VirtualGameController

# 컨트롤러 객체 생성
controller = VirtualGameController()

# 제스처-키 매핑 설정
controller.set_gesture_mapping('jump', 'space')  # 점프 제스처에 스페이스바 매핑
controller.set_gesture_mapping('up', 'w')        # 위로 이동 제스처에 'w' 키 매핑

# 프레임 처리 (True: 컨트롤러 활성화)
frame, quit_flag = controller.process_frame(True)

# 사용 완료 후 정리
controller.release_all_keys()
controller.close()
```

### 주요 메서드

* `set_gesture_mapping(gesture, key)` - 특정 제스처에 키를 매핑합니다.
* `process_frame(active=False)` - 카메라 프레임을 처리하고, 활성화 상태면 인식된 제스처에 따라 키를 입력합니다.
* `release_all_keys()` - 모든 키 입력을 해제합니다.
* `close()` - 컨트롤러를 종료하고 자원을 정리합니다.

## PyQt 애플리케이션과의 연결

Main.py의 `GameControllerGUI` 클래스는 VirtualGameController를 활용하여 사용자 친화적인 인터페이스를 제공합니다:

1. **초기화 과정**:
   ```python
   # VirtualGameController 객체 생성
   self.controller = VirtualGameController()
   
   # 타이머 설정으로 주기적인 프레임 처리
   self.timer = QTimer()
   self.timer.timeout.connect(self.update_frame)
   self.timer.start(30)  # 30ms 마다 업데이트
   ```

2. **프레임 처리**:
   ```python
   def update_frame(self):
       # 컨트롤러 활성화 여부를 전달하여 프레임 처리
       frame, quit_flag = self.controller.process_frame(self.controller_active)
       
       # 프레임을 PyQt 화면에 표시
       # ...
   ```

3. **키 매핑 설정**:
   ```python
   def update_mapping(self, gesture):
       # 사용자가 선택한 키를 컨트롤러에 매핑
       self.controller.set_gesture_mapping(gesture, key_value)
       
       # UI 업데이트
       self.update_key_mapping_display()
   ```

## 사용 방법

1. 프로그램 실행 후 카메라에 손이 보이도록 합니다.
2. 메뉴의 '설정 > 키 매핑 설정'에서 각 제스처에 매핑할 키를 설정합니다.
3. '시작' 버튼을 클릭하여 컨트롤러를 활성화합니다.
4. 제어하려는 게임 창을 클릭하여 포커스를 설정합니다.
5. 다음 손동작으로 게임을 제어합니다:
   - 검지 손가락 펴기: 위로 이동 (↑)
   - 검지와 중지 손가락 펴기: 아래로 이동 (↓)
   - 엄지 손가락 펴기: 왼쪽으로 이동 (←)
   - 새끼 손가락 펴기: 오른쪽으로 이동 (→)
   - 두 손가락 모으기: 점프 (Space)
   - 이 부분 잘못됐음 추후 고치겠음.
6. '정지' 버튼을 클릭하여 컨트롤러를 비활성화합니다.

## 주요 특징

- **마우스/키보드 모드 전환**: 내장 영역을 통해 마우스 또는 키보드 모드로 전환 가능
- **컴팩트 모드**: 컨트롤러 활성화 시 화면 크기가 자동으로 작아져 게임 화면을 가리지 않음
- **다크 모드 UI**: 눈의 피로를 줄이는 현대적인 다크 테마 인터페이스
- **항상 위에 표시**: 게임 창과 함께 표시되도록 항상 위에 표시 옵션 제공

## 확장 가능성

- 새로운 제스처 추가
- 조합 키 설정 기능
- 게임별 프로필 저장 및 불러오기
- 사용자 정의 제스처 학습 기능

---

이 프로젝트는 Gokul9404의 Virtual-Game-Controller를 기반으로 확장한 버전입니다.
