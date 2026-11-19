// car_ultrasonic.ino
// 초음파 센서로 앞이 막히면 멈추는 차 코드 (sunbell/arduino 브랜치)
//
// 맨 위의 CAR_MODE 숫자 하나로 두 콘텐츠의 차를 나눕니다.
//  1 = 콘텐츠 1 (타임어택): F 를 받으면 정해진 시간만 앞으로 가고 스스로 멈춥니다.
//      가다가 앞이 막히면 멈추고, 막혀 있는 동안 오는 F 는 무시합니다.
//  2 = 콘텐츠 2 (장애물 제어): 켜지고 몇 초 뒤 스스로 느리게 갑니다.
//      앞이 막히면 멈추고, 앞이 열리면 다시 갑니다.
//      정지 버튼(A2 와 GND 사이)을 누르면 정지 고정, 한 번 더 누르면 몇 초 뒤 다시 갑니다.
// 두 모드 모두 S 를 받으면 바로 멈춥니다. 블루투스(HC-06)와 USB 선, 두 곳에서 같은 글자를 받습니다.
//
// 키트 예제 코드는 옮기지 않고 새로 썼습니다. 배선(모터 단자, 블루투스 핀, 초음파 핀)만 키트 자료에서 확인했습니다.
// 자세한 기록: 같은 폴더의 README.md

#include <AFMotor.h>          // Adafruit Motor Shield library V1 (L293D 모터 쉴드)
#include <SoftwareSerial.h>   // HC-06 블루투스용

// ===== 이 차가 어느 콘텐츠용인지 (보드에 올리기 전에 꼭 확인!) =====
const uint8_t CAR_MODE = 1;   // 1 = 콘텐츠 1 (타임어택), 2 = 콘텐츠 2 (장애물 제어)

// ===== 글자 약속 (2026-11-08 sunbell 결정, car_backup 과 같음) =====
const char LETTER_FORWARD = 'F';  // 콘텐츠 1: 앞으로 / 콘텐츠 2: 스스로 가기 (다시) 시작
const char LETTER_STOP    = 'S';  // 멈춤
// 그 밖의 글자, 줄바꿈(\r, \n)은 무시합니다.

// ===== 바꿀 수 있는 값: 콘텐츠 1 =====
const uint8_t       MODE1_SPEED   = 255;   // 모터 속도(0~255). 2026-11-11 sunbell 결정(AA 건전지에서 200은 출발 못 함)
const unsigned long DRIVE_TIME_MS = 1000;  // 【임시】 F 하나에 앞으로 가는 시간(ms)
const bool RESTART_TIMER_ON_F     = true;  // 【임시】 가는 도중 F 가 또 오면 true = 시간을 다시 잼, false = 무시

// ===== 바꿀 수 있는 값: 콘텐츠 2 =====
const unsigned long MODE2_START_DELAY_MS = 3000;  // 켜지거나 리셋한 뒤 스스로 출발하기까지(ms). 2026-11-17 sunbell 결정: 3초
const uint8_t       MODE2_KICK_SPEED     = 255;   // 출발하는 순간만 세게 밀 때의 속도
const unsigned long MODE2_KICK_MS        = 200;   // 【임시】 세게 미는 시간(ms). 2026-11-17 sunbell 결정: 출발만 255, 그다음 낮춤
const uint8_t       MODE2_SLOW_SPEED     = 200;   // 【임시】 느리게 갈 때의 속도. 200부터 시작해 바닥 시험으로 낮춰 가며 찾음

// ===== 바꿀 수 있는 값: 초음파 =====
const uint8_t       STOP_CM            = 20;     // 【임시】 앞이 이 거리(cm) 안이면 「막힘」. 15~20 에서 시작, 바닥 시험으로 정함
const uint8_t       RESUME_MARGIN_CM   = 10;     // 막힌 뒤에는 STOP_CM + 이 값(cm)보다 멀어져야 「열림」(멈췄다 섰다 떨림 방지)
const unsigned long SONAR_INTERVAL_MS  = 60;     // 거리를 재는 간격(ms)
const unsigned long ECHO_TIMEOUT_US    = 25000;  // 소리가 이 시간(us) 안에 안 돌아오면 「못 잼」 (기본값은 1초라 차가 굳음)
const uint8_t       CONFIRM_COUNT      = 2;      // 막힘/열림이 연속 몇 번 나와야 인정할지 (한 번 틀리게 잰 것에 속지 않기)
const unsigned long PRINT_DISTANCE_EVERY_MS = 500;  // USB 로 거리를 보여 주는 간격(ms), 0 = 끔

// ===== 바꿀 수 있는 값: 정지 버튼 (콘텐츠 2만. 2026-11-17 sunbell 결정: 버튼 하나 달기) =====
const unsigned long BUTTON_DEBOUNCE_MS      = 50;    // 버튼이 떨리는 짧은 시간 무시(ms)
const unsigned long BUTTON_RESTART_DELAY_MS = 3000;  // 【임시】 버튼으로 다시 시작할 때 출발까지 기다리는 시간(ms). 손 뗄 시간

const long USB_BAUD = 9600;  // USB 통신 속도 (2026-11-08 sunbell 결정)
const long BT_BAUD  = 9600;  // 블루투스 통신 속도 (2026-11-08 sunbell 결정)

// ===== 배선 (키트 자료 기준. 블루투스·모터는 2026-11-11, 초음파는 2026-11-17 차에서 확인) =====
const uint8_t BT_RX_PIN = A5;  // 아두이노가 받는 핀
const uint8_t BT_TX_PIN = A4;  // 아두이노가 보내는 핀
const uint8_t TRIG_PIN  = A0;  // 초음파: 소리를 내보내라고 시키는 핀
const uint8_t ECHO_PIN  = A1;  // 초음파: 되돌아온 소리를 알려 주는 핀
const uint8_t BUTTON_PIN = A2; // 정지 버튼: 한쪽 다리는 A2, 다른 쪽 다리는 GND (콘텐츠 2만 씀. 차에 달고 확인 필요)

// 바퀴가 거꾸로 돌면 그 바퀴의 값만 FORWARD <-> BACKWARD 로 바꿉니다.
const uint8_t LEFT_FORWARD_DIR  = FORWARD;
const uint8_t RIGHT_FORWARD_DIR = FORWARD;

const unsigned long US_PER_CM = 58;  // 소리가 1 cm 를 갔다 오는 데 걸리는 시간(us). 거리(cm) = 걸린 시간 / 58

AF_DCMotor leftWheel(1);   // 왼쪽 바퀴 = 쉴드 M1
AF_DCMotor rightWheel(4);  // 오른쪽 바퀴 = 쉴드 M4
SoftwareSerial bluetooth(BT_RX_PIN, BT_TX_PIN);

// ===== 지금 상태 =====
bool autoRun = false;                 // 가고 싶은 상태 (막히지만 않으면 감)
bool blocked = false;                 // 앞이 막혔는지 (초음파)
bool moving = false;                  // 바퀴가 실제로 돌고 있는지
bool kicking = false;                 // 콘텐츠 2: 출발하는 순간의 센 힘을 쓰는 중인지
bool startDone = false;               // 콘텐츠 2: 켜진 뒤 자동 출발을 이미 했는지 (F 나 S 가 먼저 와도 true)
unsigned long driveStartedAt = 0;     // 콘텐츠 1: 마지막으로 가는 시간을 잰 때(millis)
unsigned long movingSince = 0;        // 바퀴가 돌기 시작한 때(millis)
unsigned long lastSonarAt = 0;        // 마지막으로 거리를 잰 때(millis)
unsigned long lastPrintAt = 0;        // 마지막으로 거리를 보여 준 때(millis)
unsigned long lastEchoUs = 0;         // 마지막으로 잰 값(us). 0 = 못 잼
uint8_t confirmCount = 0;             // 막힘/열림이 연속으로 나온 횟수
bool restartPending = false;          // 콘텐츠 2: 버튼으로 다시 시작하려고 기다리는 중인지
unsigned long restartAt = 0;          // 기다리다 출발할 때(millis)
bool buttonRawLow = false;            // 버튼 핀이 지금 LOW(눌림)로 읽히는지
bool buttonPressed = false;           // 떨림을 거른 뒤 「눌림」으로 인정한 상태
unsigned long buttonChangedAt = 0;    // 버튼 핀 값이 마지막으로 바뀐 때(millis)

void setup() {
  Serial.begin(USB_BAUD);
  bluetooth.begin(BT_BAUD);

  pinMode(TRIG_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // 안 누르면 HIGH, 누르면 LOW

  releaseWheels();  // 켜지면 멈춘 상태로 시작

  Serial.print(F("car_ultrasonic 시작: 콘텐츠 "));
  Serial.print(CAR_MODE);
  Serial.println(F(" 모드, 멈춤 상태"));
  if (CAR_MODE == 1) {
    Serial.println(F("F=앞으로(정해진 시간), S=멈춤, 앞이 막히면 멈춤"));
  } else {
    Serial.print(F("켜진 뒤 "));
    Serial.print(MODE2_START_DELAY_MS);
    Serial.println(F("ms 뒤 스스로 출발. S 나 버튼=멈춤(고정), F 나 버튼 한 번 더=다시 출발"));
  }
}

void loop() {
  while (Serial.available() > 0) {
    handleLetter(Serial.read(), F("USB"));
  }
  while (bluetooth.available() > 0) {
    handleLetter(bluetooth.read(), F("BT"));
  }

  // 콘텐츠 1: 정해진 시간이 지나면 스스로 멈춤 (millis 가 한 바퀴 돌아도 빼기로 재면 맞음)
  if (CAR_MODE == 1 && autoRun && millis() - driveStartedAt >= DRIVE_TIME_MS) {
    autoRun = false;
    Serial.println(F("시간 끝"));
  }

  // 콘텐츠 2: 켜진 뒤 정해진 시간이 지나면 스스로 출발 (처음 한 번만)
  if (CAR_MODE == 2 && !startDone && millis() >= MODE2_START_DELAY_MS) {
    startDone = true;
    autoRun = true;
    Serial.println(F("시간 지남 -> 스스로 가기 시작"));
  }

  // 콘텐츠 2: 버튼으로 다시 시작하기로 한 뒤 기다리는 시간이 지나면 출발
  if (restartPending && millis() >= restartAt) {
    restartPending = false;
    autoRun = true;
    Serial.println(F("버튼 뒤 기다림 끝 -> 스스로 가기 시작"));
  }

  updateButton();
  updateSonar();
  applyMovement();
}

// 글자 -> 동작. 약속이 바뀌면 여기와 맨 위 글자 약속만 고칩니다.
void handleLetter(int letter, const __FlashStringHelper *source) {
  if (letter == '\r' || letter == '\n') {
    return;  // 시리얼 모니터가 붙이는 줄바꿈은 조용히 무시
  }

  printSource(source, letter);

  switch (letter) {
    case LETTER_FORWARD:
      pressForward();
      break;
    case LETTER_STOP:
      stopByOperator();
      Serial.println(F("S 받음 -> 멈춤"));
      break;
    default:
      Serial.println(F("모르는 글자 -> 무시"));
      break;
  }
}

// 사람이 멈추라고 한 것(S 글자, 버튼). 다시 가라고 하기 전까지 안 갑니다.
// 콘텐츠 2: 켜진 뒤 자동 출발을 기다리던 것, 버튼 뒤 출발을 기다리던 것도 취소합니다.
void stopByOperator() {
  autoRun = false;
  startDone = true;
  restartPending = false;
}

// 버튼 한 번 = 가는 중(또는 곧 갈 예정)이면 정지 고정, 멈춰 있으면 기다림 뒤 다시 출발. 콘텐츠 2만.
void updateButton() {
  if (CAR_MODE != 2) {
    return;
  }
  bool isLow = (digitalRead(BUTTON_PIN) == LOW);
  if (isLow != buttonRawLow) {
    buttonRawLow = isLow;
    buttonChangedAt = millis();
  }
  if (millis() - buttonChangedAt >= BUTTON_DEBOUNCE_MS && buttonRawLow != buttonPressed) {
    buttonPressed = buttonRawLow;
    if (buttonPressed) {
      onButtonPress();
    }
  }
}

void onButtonPress() {
  bool willRun = autoRun || !startDone || restartPending;
  if (willRun) {
    stopByOperator();
    Serial.println(F("[버튼] 눌림 -> 정지 고정"));
  } else {
    startDone = true;
    restartPending = true;
    restartAt = millis() + BUTTON_RESTART_DELAY_MS;
    Serial.print(F("[버튼] 눌림 -> "));
    Serial.print(BUTTON_RESTART_DELAY_MS);
    Serial.println(F("ms 뒤 다시 출발"));
  }
}

void pressForward() {
  if (CAR_MODE == 2) {
    startDone = true;
    restartPending = false;
    autoRun = true;
    Serial.println(F("스스로 가기 시작 (막혀 있으면 열릴 때까지 기다림)"));
    return;
  }

  // 콘텐츠 1
  if (blocked) {
    Serial.println(F("앞이 막혀 있음 -> 무시"));
    return;
  }
  if (autoRun && !RESTART_TIMER_ON_F) {
    Serial.println(F("가는 중 -> 무시"));
    return;
  }
  driveStartedAt = millis();
  if (autoRun) {
    Serial.println(F("가는 중 -> 시간 다시 잼"));
    return;
  }
  autoRun = true;
  Serial.print(F("앞으로 ("));
  Serial.print(DRIVE_TIME_MS);
  Serial.println(F("ms)"));
}

// 정해진 간격마다 거리를 재서 「막힘」 「열림」을 정합니다.
void updateSonar() {
  unsigned long now = millis();
  if (now - lastSonarAt < SONAR_INTERVAL_MS) {
    return;
  }
  lastSonarAt = now;

  lastEchoUs = readEchoUs();

  // 막힌 뒤에는 더 먼 거리까지 「가깝다」로 봐서, 경계에서 멈췄다 섰다 떨리지 않게 합니다.
  // 소리가 안 돌아온 것(못 잼)은 「앞이 비었다」로 봅니다.
  uint8_t limitCm = blocked ? (STOP_CM + RESUME_MARGIN_CM) : STOP_CM;
  bool isNear = (lastEchoUs != 0) && (lastEchoUs <= (unsigned long)limitCm * US_PER_CM);

  if (isNear == blocked) {
    confirmCount = 0;           // 지금 상태와 같으면 세던 것을 지움
  } else if (++confirmCount >= CONFIRM_COUNT) {
    confirmCount = 0;           // 연속으로 나왔으니 인정
    blocked = isNear;
    Serial.print(blocked ? F("앞이 막힘 (") : F("앞이 열림 ("));
    printDistance();
    Serial.println(F(")"));
    if (blocked && CAR_MODE == 1) {
      autoRun = false;          // 콘텐츠 1: 막히면 거기서 끝. 열려도 다시 F 를 받아야 감
    }
  }

  if (PRINT_DISTANCE_EVERY_MS > 0 && now - lastPrintAt >= PRINT_DISTANCE_EVERY_MS) {
    lastPrintAt = now;
    Serial.print(F("거리 "));
    printDistance();
    Serial.println();
  }
}

// 소리가 돌아오는 데 걸린 시간(us). 0 = 못 잼
unsigned long readEchoUs() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  return pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
}

void printDistance() {
  if (lastEchoUs == 0) {
    Serial.print(F("못 잼"));
  } else {
    Serial.print(lastEchoUs / 58.0, 1);
    Serial.print(F(" cm"));
  }
}

// 「가고 싶은가」와 「막혔는가」를 합쳐 바퀴를 돌리거나 세웁니다.
void applyMovement() {
  bool shouldMove = autoRun && !blocked;
  if (shouldMove && !moving) {
    startWheels();
  } else if (!shouldMove && moving) {
    stopWheels();
  } else if (moving && kicking && millis() - movingSince >= MODE2_KICK_MS) {
    setWheelSpeed(MODE2_SLOW_SPEED);  // 콘텐츠 2: 출발 힘이 끝났으니 느린 속도로
    kicking = false;
    Serial.print(F("느린 속도로 (세기 "));
    Serial.print(MODE2_SLOW_SPEED);
    Serial.println(F(")"));
  }
}

void startWheels() {
  bool useKick = (CAR_MODE == 2);
  uint8_t speed = useKick ? MODE2_KICK_SPEED : MODE1_SPEED;
  setWheelSpeed(speed);
  leftWheel.run(LEFT_FORWARD_DIR);
  rightWheel.run(RIGHT_FORWARD_DIR);
  moving = true;
  kicking = useKick;
  movingSince = millis();
  Serial.print(F("출발 (세기 "));
  Serial.print(speed);
  Serial.println(F(")"));
}

void stopWheels() {
  releaseWheels();
  moving = false;
  kicking = false;
  Serial.println(F("멈춤"));
}

void setWheelSpeed(uint8_t speed) {
  leftWheel.setSpeed(speed);
  rightWheel.setSpeed(speed);
}

void releaseWheels() {
  leftWheel.run(RELEASE);
  rightWheel.run(RELEASE);
}

void printSource(const __FlashStringHelper *source, int letter) {
  Serial.print('[');
  Serial.print(source);
  Serial.print(F("] "));
  Serial.print((char)letter);
  Serial.print(F(" : "));
}
