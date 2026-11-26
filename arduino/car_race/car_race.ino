// car_race.ino
// 협동 레이싱용 차 코드: 컨트롤러처럼 W/A/S/D 로 조종합니다 (sunbell/arduino 브랜치)
//
// 글자 약속 (2026-11-19 sunbell 결정: 화이트보드의 W/S = 앞/뒤, A/D = 왼/오)
//   W 앞으로, S 뒤로, A 왼쪽, D 오른쪽, X 앞뒤 입력만 끔, Z 좌우 입력만 끔 (2026-11-20 sunbell 결정)
//   노트북 2대로 나눠 몰 때 한 사람이 멈춰도 다른 사람의 입력은 끊기지 않게 하려고 나눴습니다. 둘 다 끄려면 X 와 Z 를 이어서 보냅니다.
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
const char LETTER_STOP_DRIVE = 'X';  // 앞뒤 입력만 끔 (2026-11-20 sunbell 결정). 예전 코드의 S=멈춤과 뜻이 다름에 주의
const char LETTER_STOP_TURN  = 'Z';  // 좌우 입력만 끔 (2026-11-20 sunbell 결정)
// 그 밖의 글자, 줄바꿈(\r, \n)은 무시합니다.

// ===== 바꿀 수 있는 값 (모두 【임시】, 바닥 시험으로 정함) =====
const unsigned long INPUT_TIMEOUT_MS = 300;  // 글자가 이 시간 안에 다시 안 오면 그 입력을 끔
const uint8_t DRIVE_SPEED       = 255;       // 앞/뒤로만 갈 때 (2026-11-11 sunbell 결정: AA 건전지에서 200은 출발 못 함)
// 휘며 갈 때(W+A, W+D)의 모양: 바깥 바퀴와 안쪽 바퀴 속도의 짝 여덟 가지. 시험 중에는 글자 1~8 로 바꿔 볼 수 있습니다(차를 다시 안 올려도 됨).
// 안쪽이 바깥보다 많이 느릴수록 좁게 돕니다. 짝 번호는 1부터 셉니다.
//  1: 바깥 255 / 안쪽 190 (넓게, 2026-11-19 시험: 거의 직진)    2: 255 / 150 (지금 값, 시험 중)
//  3: 255 / 110   4: 255 / 70   5: 200 / 95 (바깥도 약하게)   6: 255 / 0 (안쪽 바퀴를 놓음, 가장 좁게)
//  7: 255 / 35 (2026-11-23 추가: 4번과 6번 사이. 왼쪽 커브가 오른쪽보다 덜 돌아서 맞춰 보려고)
//  8: 255 / 90 (2026-11-23 추가: 3번과 4번 사이. 왼쪽 7번에 비해 오른쪽 3번이 덜 돌아서 맞춰 보려고)
//  9: 255 / 165 (2026-11-23 추가: 2번과 1번 사이. 오른쪽 커브 지름을 왼쪽 8번(약 66 cm)에 맞추려고.
//     같은 날 먼저 넣었던 255/55 는 지름 약 30 cm 로 너무 좁아 이 자리를 바꿈)
const uint8_t CURVE_COUNT = 9;
const uint8_t CURVE_OUTER[CURVE_COUNT] = {255, 255, 255, 255, 200, 255, 255, 255, 255};
const uint8_t CURVE_INNER[CURVE_COUNT] = {190, 150, 110,  70,  95,   0,  35,  90, 165};
// 켜졌을 때 쓰는 짝 번호(1~9). 왼쪽 커브(W+A)와 오른쪽 커브(W+D)를 따로 정합니다. 이 값만 바꿔서 올리면 기본값이 바뀝니다.
// 2026-11-23 sunbell 결정: 같은 번호로는 왼쪽이 덜 돌아서(왼쪽 4번 약 반 바퀴, 오른쪽 3번 약 1바퀴) 따로 정함.
// 왼쪽 7번(안쪽 35)은 3초에 약 1바퀴, 오른쪽은 3번(안쪽 110)이 한 바퀴가 못 돼서 8번(안쪽 90, 약 0.8~0.9바퀴)으로 맞춤
// 2026-11-23 저녁: 7/8번은 지름이 약 30~35 cm 로 거의 선회 수준이라(노트북 2대 시험) 넓힘.
// 6초 커브 지름(줄자, 테이프 두 개, 블루투스, 직진 보정 100/100): 왼쪽 3번(안쪽 110) 약 62 cm, 오른쪽 2번(안쪽 150) 약 63 cm. 길 폭 약 60 cm.
// (직진 보정이 오른쪽 94 → 100 으로 바뀌어 왼쪽 8번이 66 → 44 cm 로 좁아져 3번으로 바꿈. 오른쪽 9번(안쪽 165)은 65·90·115 cm 로 흔들려서 뺐음)
const uint8_t CURVE_DEFAULT_LEFT  = 3;
const uint8_t CURVE_DEFAULT_RIGHT = 2;
const uint8_t SPIN_SPEED        = 190;       // 제자리 돌기 속도. 255 로 0.8초 누르면 약 270도 돌아 너무 빨랐음(2026-11-19 시험)
const uint8_t RIGHT_SCALE_PERCENT = 100;     // 오른쪽 바퀴 값에 곱하는 비율(%). 100 = 보정 없음. (11/19 에는 직진이 살짝 왼쪽으로 휘어 94 로 줄였으나, 11/23 저녁에는 3초에 오른쪽으로 61 cm 쏠려 반대가 됨)
const uint8_t LEFT_SCALE_PERCENT  = 100;     // 왼쪽 바퀴 값에 곱하는 비율(%). 100 = 보정 없음. 2026-11-23 저녁 3초 직진 쏠림(오른쪽 + / 왼쪽 -): 오른쪽 94·왼쪽 100 → +61 cm(블루투스), 오른쪽 100·왼쪽 86 → -70 cm(USB), 오른쪽 100·왼쪽 96 → -45 cm(USB)·-40 cm(블루투스). 두 점 사이 직선으로 보면 보정 없음(100/100) 근처에서 0 이 되어 보정을 모두 뺌 — 시험으로 확인
const uint8_t KICK_SPEED        = 255;       // 멈춘 데서 출발하는 순간만 세게 밀 때의 속도
const unsigned long KICK_MS     = 150;       // 세게 미는 시간(ms)

// ===== 바꿀 수 있는 값: 초음파 (car_ultrasonic 과 같음) =====
// 앞이 막히면 앞으로 안 가는 기능을 켜고 끕니다. false 면 거리는 재서 로그(「앞이 막힘」)만 남기고 차는 막지 않습니다.
// 2026-11-23 sunbell 결정: 커브 시험 중에는 벽이 아닌 물건에도 걸려 시험이 끊겨서 잠시 끔(false). 커브를 정한 뒤 초음파 바닥 시험을 하려고 같은 날 true 로 되돌림.
// 2026-11-26 sunbell 결정: 「앞 막힘 기능은 꺼 두는 걸로」 — 이음제에서는 끔(false). 거리는 계속 재서 로그로 남김.
const bool          FORWARD_BLOCK_ENABLED = false;
const uint8_t       STOP_CM          = 20;     // 앞이 이 거리(cm) 안이면 「막힘」
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
uint8_t curveLeft  = CURVE_DEFAULT_LEFT - 1;    // 왼쪽 커브(W+A)에 쓰는 짝 (0부터 셈)
uint8_t curveRight = CURVE_DEFAULT_RIGHT - 1;   // 오른쪽 커브(W+D)에 쓰는 짝 (0부터 셈)
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
  Serial.println(F("car_race 시작: 멈춤 상태. W 앞, S 뒤, A 왼, D 오른, X 앞뒤 끔, Z 좌우 끔"));
  Serial.println(FORWARD_BLOCK_ENABLED ? F("앞 막힘 기능: 켜짐 (앞이 막히면 앞으로 안 감)")
                                       : F("앞 막힘 기능: 꺼짐 (거리만 재서 로그로 남김)"));
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
    case LETTER_STOP_DRIVE:
      driveDir = 0;
      Serial.print('['); Serial.print(source); Serial.println(F("] X : 앞뒤 끔"));
      break;
    case LETTER_STOP_TURN:
      turnDir = 0;
      Serial.print('['); Serial.print(source); Serial.println(F("] Z : 좌우 끔"));
      break;
    default:
      if (letter >= '1' && letter < '1' + CURVE_COUNT) {   // 시험용: 커브 모양 바꾸기 (왼쪽·오른쪽 둘 다 이 번호로 바뀜)
        curveLeft = curveRight = letter - '1';
        Serial.print('['); Serial.print(source); Serial.print(F("] 커브 ")); Serial.print((char)letter);
        Serial.print(F(": 바깥 ")); Serial.print(CURVE_OUTER[curveLeft]);
        Serial.print(F(" / 안쪽 ")); Serial.println(CURVE_INNER[curveLeft]);
        break;
      }
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
  // 이미 막힌 상태에서 「못 잼」이 나오면 열림으로 보지 않고 막힌 채로 둡니다.
  // 2026-11-23 시험: 물건이 비스듬하거나 아주 가까우면 소리가 안 돌아와 「못 잼」이 나오는데, 그걸 「열림」으로 봐서 차가 다시 앞으로 가 물건에 닿음.
  // 막힌 뒤에는 S 로 뒤로 빠지거나 A/D 로 돌아서 거리가 잡히면 열립니다.
  if (blocked && lastEchoUs == 0) {
    isNear = true;
  }

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
  if (FORWARD_BLOCK_ENABLED && drive > 0 && blocked) {
    drive = 0;  // 앞이 막혀 있으면 앞으로는 안 감 (뒤로 가기와 돌기는 허용)
  }

  int left = 0;
  int right = 0;
  if (drive != 0 && turn == 0) {                     // 곧게 앞/뒤
    left = right = drive * DRIVE_SPEED;
  } else if (drive != 0) {                           // 휘며 앞/뒤: 가려는 쪽 안쪽 바퀴를 느리게
    uint8_t idx = (turn < 0) ? curveLeft : curveRight;   // 왼쪽 커브와 오른쪽 커브는 짝 번호를 따로 씀
    int outer = drive * CURVE_OUTER[idx];
    int inner = drive * CURVE_INNER[idx];
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
  if (left != 0) {
    int scaled = (int)((long)left * LEFT_SCALE_PERCENT / 100);
    left = (scaled == 0) ? ((left > 0) ? 1 : -1) : scaled;
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
