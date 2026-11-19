// car_race.ino
// 협동 레이싱용 차 코드: 컨트롤러처럼 W/A/S/D 로 조종합니다 (sunbell/arduino 브랜치)
//
// 글자 약속 (2026-11-19 sunbell 결정: 화이트보드의 W/S = 앞/뒤, A/D = 왼/오)
//   W 앞으로, S 뒤로, A 왼쪽, D 오른쪽, X 모두 멈춤(제안, 아직 정하지 않음)
// 노트북이 동작이 켜져 있는 동안 글자를 0.1~0.2초마다 계속 보내고, 차는 글자가 INPUT_TIMEOUT_MS 안에
// 안 오면 그 입력을 끕니다. 그래서 연결이 끊겨도 차가 스스로 멈춥니다.
// 앞뒤(W/S)와 좌우(A/D)를 따로 기억해서 합칩니다: W+A = 왼쪽으로 휘며 앞으로, A만 = 제자리 돌기.
// 앞으로 갈 때만 초음파로 벽 앞에서 막고, 뒤로 가기와 돌기는 허용합니다(벽에서 빠져나올 수 있게).
// 블루투스(HC-06)와 USB 선, 두 곳에서 같은 글자를 받습니다.
//
// 키트 예제 코드는 옮기지 않고 새로 썼습니다. 배선(모터 단자, 블루투스·초음파 핀)만 키트 자료에서 확인했습니다.
// 자세한 기록: 같은 폴더의 README.md (시험 뒤 작성)

#include <AFMotor.h>          // Adafruit Motor Shield library V1 (L293D 모터 쉴드)
#include <SoftwareSerial.h>   // HC-06 블루투스용

// ===== 글자 약속 =====
const char LETTER_FORWARD  = 'W';
const char LETTER_BACKWARD = 'S';
const char LETTER_LEFT     = 'A';
const char LETTER_RIGHT    = 'D';
const char LETTER_STOP     = 'X';  // 【임시】 멈춤 글자. 예전의 S=멈춤과 뜻이 달라진 것에 주의
// 그 밖의 글자, 줄바꿈(\r, \n)은 무시합니다.

// ===== 바꿀 수 있는 값 (모두 【임시】, 바닥 시험으로 정함) =====
const unsigned long INPUT_TIMEOUT_MS = 300;  // 글자가 이 시간 안에 다시 안 오면 그 입력을 끔
const uint8_t DRIVE_SPEED       = 255;       // 앞/뒤로만 갈 때 (2026-11-11 sunbell 결정: AA 건전지에서 200은 출발 못 함)
const uint8_t CURVE_INNER_SPEED = 150;       // 휘며 갈 때 안쪽 바퀴 속도 (바깥쪽 바퀴는 DRIVE_SPEED). 2026-11-19 시험: 120 은 너무 좁게, 190 은 거의 직진이라 그 사이로
const uint8_t SPIN_SPEED        = 190;       // 제자리 돌기 속도. 255 로 0.8초 누르면 약 270도 돌아 너무 빨랐음(2026-11-19 시험)
const uint8_t RIGHT_SCALE_PERCENT = 94;      // 오른쪽 바퀴 값에 곱하는 비율(%). 직진이 살짝 왼쪽으로 휘어서 오른쪽을 약하게(2026-11-19 시험). 100 = 보정 없음
const uint8_t KICK_SPEED        = 255;       // 멈춘 데서 출발하는 순간만 세게 밀 때의 속도
const unsigned long KICK_MS     = 150;       // 세게 미는 시간(ms)

// ===== 바꿀 수 있는 값: 초음파 (car_ultrasonic 과 같음) =====
const uint8_t       STOP_CM           = 20;     // 앞이 이 거리(cm) 안이면 「막힘」
const uint8_t       RESUME_MARGIN_CM  = 10;     // 막힌 뒤에는 STOP_CM + 이 값보다 멀어져야 「열림」
const unsigned long SONAR_INTERVAL_MS = 60;     // 거리를 재는 간격(ms)
const unsigned long ECHO_TIMEOUT_US   = 25000;  // 소리가 이 시간 안에 안 돌아오면 「못 잼」(앞이 비었다고 봄)
const uint8_t       CONFIRM_COUNT     = 2;      // 막힘/열림이 연속 몇 번 나와야 인정할지

const long USB_BAUD = 9600;
const long BT_BAUD  = 9600;

// ===== 배선 (키트 자료 기준. 블루투스·모터는 2026-11-11, 초음파는 2026-11-17 차에서 확인) =====
const uint8_t BT_RX_PIN = A5;
const uint8_t BT_TX_PIN = A4;
const uint8_t TRIG_PIN  = A0;
const uint8_t ECHO_PIN  = A1;

// 바퀴가 거꾸로 돌면 그 바퀴의 값만 FORWARD <-> BACKWARD 로 바꿉니다.
const uint8_t LEFT_FORWARD_DIR  = FORWARD;
const uint8_t RIGHT_FORWARD_DIR = FORWARD;

const unsigned long US_PER_CM = 58;  // 소리가 1 cm 를 갔다 오는 데 걸리는 시간(us)

AF_DCMotor leftWheel(1);   // 왼쪽 바퀴 = 쉴드 M1
AF_DCMotor rightWheel(4);  // 오른쪽 바퀴 = 쉴드 M4
SoftwareSerial bluetooth(BT_RX_PIN, BT_TX_PIN);

// ===== 지금 상태 =====
int8_t driveDir = 0;               // 앞뒤 입력: +1 앞, -1 뒤, 0 없음
int8_t turnDir  = 0;               // 좌우 입력: -1 왼, +1 오른, 0 없음
unsigned long driveAt = 0;         // 앞뒤 글자를 마지막으로 받은 때(millis)
unsigned long turnAt  = 0;         // 좌우 글자를 마지막으로 받은 때(millis)
bool blocked = false;              // 앞이 막혔는지 (초음파)
uint8_t confirmCount = 0;
unsigned long lastSonarAt = 0;
unsigned long lastEchoUs = 0;
int lastLeft = 0;                  // 마지막으로 바퀴에 준 값 (-255~255, 0 = 멈춤)
int lastRight = 0;
unsigned long kickUntil = 0;       // 이 시간(millis)까지는 출발 힘을 줌

void setup() {
  Serial.begin(USB_BAUD);
  bluetooth.begin(BT_BAUD);
  pinMode(TRIG_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);
  releaseWheels();
  Serial.println(F("car_race 시작: 멈춤 상태. W 앞, S 뒤, A 왼, D 오른, X 멈춤"));
}

void loop() {
  while (Serial.available() > 0) {
    handleLetter(Serial.read(), F("USB"));
  }
  while (bluetooth.available() > 0) {
    handleLetter(bluetooth.read(), F("BT"));
  }

  // 글자가 한동안 안 오면 그 입력을 끔 (millis 가 한 바퀴 돌아도 빼기로 재면 맞음)
  unsigned long now = millis();
  if (driveDir != 0 && now - driveAt >= INPUT_TIMEOUT_MS) { driveDir = 0; }
  if (turnDir != 0 && now - turnAt >= INPUT_TIMEOUT_MS) { turnDir = 0; }

  updateSonar();
  applyWheels();
}

// 글자 -> 입력 상태. 반복해서 오는 글자는 시간만 다시 잽니다. 약속이 바뀌면 맨 위 글자 약속만 고칩니다.
void handleLetter(int letter, const __FlashStringHelper *source) {
  if (letter == '\r' || letter == '\n') {
    return;
  }
  unsigned long now = millis();
  switch (letter) {
    case LETTER_FORWARD:  driveDir = +1; driveAt = now; break;
    case LETTER_BACKWARD: driveDir = -1; driveAt = now; break;
    case LETTER_LEFT:     turnDir = -1;  turnAt = now;  break;
    case LETTER_RIGHT:    turnDir = +1;  turnAt = now;  break;
    case LETTER_STOP:
      driveDir = 0;
      turnDir = 0;
      Serial.print('['); Serial.print(source); Serial.println(F("] X : 모두 멈춤"));
      break;
    default:
      Serial.print('['); Serial.print(source); Serial.print(F("] ")); Serial.print((char)letter);
      Serial.println(F(" : 모르는 글자 -> 무시"));
      break;
  }
}

// 정해진 간격마다 거리를 재서 「막힘」 「열림」을 정합니다.
void updateSonar() {
  unsigned long now = millis();
  if (now - lastSonarAt < SONAR_INTERVAL_MS) {
    return;
  }
  lastSonarAt = now;

  lastEchoUs = readEchoUs();

  uint8_t limitCm = blocked ? (STOP_CM + RESUME_MARGIN_CM) : STOP_CM;
  bool isNear = (lastEchoUs != 0) && (lastEchoUs <= (unsigned long)limitCm * US_PER_CM);

  if (isNear == blocked) {
    confirmCount = 0;
  } else if (++confirmCount >= CONFIRM_COUNT) {
    confirmCount = 0;
    blocked = isNear;
    Serial.print(blocked ? F("앞이 막힘 (") : F("앞이 열림 ("));
    if (lastEchoUs == 0) { Serial.print(F("못 잼")); } else { Serial.print(lastEchoUs / 58.0, 1); Serial.print(F(" cm")); }
    Serial.println(F(")"));
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

// 앞뒤 입력과 좌우 입력을 합쳐 왼쪽·오른쪽 바퀴 값(-255~255)을 정합니다.
void applyWheels() {
  int8_t drive = driveDir;
  int8_t turn = turnDir;
  if (drive > 0 && blocked) {
    drive = 0;  // 앞이 막혀 있으면 앞으로는 안 감 (뒤로 가기와 돌기는 허용)
  }

  int left = 0;
  int right = 0;
  if (drive != 0 && turn == 0) {                     // 곧게 앞/뒤
    left = right = drive * DRIVE_SPEED;
  } else if (drive != 0) {                           // 휘며 앞/뒤: 가려는 쪽 안쪽 바퀴를 느리게
    int outer = drive * DRIVE_SPEED;
    int inner = drive * CURVE_INNER_SPEED;
    if (turn < 0) { left = inner; right = outer; } else { left = outer; right = inner; }
  } else if (turn != 0) {                            // 제자리 돌기
    if (turn < 0) { left = -SPIN_SPEED; right = SPIN_SPEED; } else { left = SPIN_SPEED; right = -SPIN_SPEED; }
  }

  // 멈춘 데서 출발하는 순간만 세게 밀기 (느린 값에서 바퀴가 안 도는 것을 막음)
  unsigned long now = millis();
  if (lastLeft == 0 && lastRight == 0 && (left != 0 || right != 0)) {
    kickUntil = now + KICK_MS;
  }
  if (now < kickUntil) {
    if (left != 0) { left = (left > 0) ? KICK_SPEED : -KICK_SPEED; }
    if (right != 0) { right = (right > 0) ? KICK_SPEED : -KICK_SPEED; }
  }

  // 두 바퀴 힘이 달라 한쪽으로 휘는 것을 줄이려고 오른쪽 바퀴 값을 비율만큼 줄임 (값이 작아도 0 은 안 됨)
  if (right != 0) {
    int scaled = (int)((long)right * RIGHT_SCALE_PERCENT / 100);
    right = (scaled == 0) ? ((right > 0) ? 1 : -1) : scaled;
  }

  if (left != lastLeft || right != lastRight) {
    setWheel(leftWheel, left, LEFT_FORWARD_DIR);
    setWheel(rightWheel, right, RIGHT_FORWARD_DIR);
    lastLeft = left;
    lastRight = right;
    Serial.print(F("바퀴 왼 ")); Serial.print(left);
    Serial.print(F(" 오 ")); Serial.println(right);
  }
}

// 값이 0 이면 바퀴를 놓고, 양수면 앞, 음수면 뒤로 돌립니다.
void setWheel(AF_DCMotor &wheel, int value, uint8_t forwardDir) {
  if (value == 0) {
    wheel.run(RELEASE);
    return;
  }
  uint8_t backwardDir = (forwardDir == FORWARD) ? BACKWARD : FORWARD;
  wheel.setSpeed(value > 0 ? value : -value);
  wheel.run(value > 0 ? forwardDir : backwardDir);
}

void releaseWheels() {
  leftWheel.run(RELEASE);
  rightWheel.run(RELEASE);
}
