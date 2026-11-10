// car.ino — 글자 하나를 받아 차를 움직인다 (11/11 발표회용)
//
// 입력: HC-06 블루투스(SoftwareSerial)와 USB 시리얼, 둘 다 9600 bps.
//       어느 쪽으로 들어온 글자든 똑같이 처리한다.
// 동작: 'F' = 정해진 시간만 앞으로 가고 스스로 멈춤, 'S' = 바로 멈춤.
//       모르는 글자와 줄바꿈(\r, \n)은 무시한다.
//
// 필요한 라이브러리: Adafruit Motor Shield library (V1, AFMotor). V2 아님.
// 약속과 시험 결과는 arduino/README.md 참고.

#include <AFMotor.h>
#include <SoftwareSerial.h>

// ───────── 명령표: 글자 약속이 바뀌면 여기만 고친다 ─────────
const char CMD_FORWARD = 'F';  // 앞으로
const char CMD_STOP    = 'S';  // 멈춤

// ───────── 조정값 ─────────
const uint8_t       DRIVE_SPEED = 255;    // 모터 세기 0~255 (11/11 sunbell 결정)
const unsigned long FORWARD_MS  = 1000;   // F 한 번에 앞으로 가는 시간, ms (시작값, 차 시험 보고 조정)
// 가는 도중 F가 또 오면: true = 그때부터 시간을 다시 잰다, false = 무시한다
const bool          RESTART_TIMER_ON_REPEAT = true;

// ───────── 배선 ─────────
const uint8_t  LEFT_MOTOR_PORT  = 1;      // 쉴드 M1 = 왼쪽 바퀴
const uint8_t  RIGHT_MOTOR_PORT = 4;      // 쉴드 M4 = 오른쪽 바퀴
// 바퀴가 반대로 돌면 그 바퀴만 FORWARD ↔ BACKWARD 로 바꾼다.
const uint8_t  LEFT_FORWARD_DIR  = FORWARD;
const uint8_t  RIGHT_FORWARD_DIR = FORWARD;

const uint8_t  BT_RX_PIN = A5;            // 아두이노가 받는 핀 (HC-06 TXD 와 연결)
const uint8_t  BT_TX_PIN = A4;            // 아두이노가 보내는 핀 (HC-06 RXD 와 연결)
const long     BAUD      = 9600;          // 블루투스와 USB 모두

AF_DCMotor leftMotor(LEFT_MOTOR_PORT);
AF_DCMotor rightMotor(RIGHT_MOTOR_PORT);
SoftwareSerial bluetooth(BT_RX_PIN, BT_TX_PIN);

bool          moving = false;             // 지금 앞으로 가는 중인가
unsigned long moveStartedAt = 0;          // 가기 시작한 시각 (millis)

void stopCar() {
  leftMotor.run(RELEASE);
  rightMotor.run(RELEASE);
  moving = false;
}

void goForward() {
  leftMotor.setSpeed(DRIVE_SPEED);
  rightMotor.setSpeed(DRIVE_SPEED);
  leftMotor.run(LEFT_FORWARD_DIR);
  rightMotor.run(RIGHT_FORWARD_DIR);
  moving = true;
}

// 글자 → 동작. 글자를 해석하는 곳은 여기 하나뿐이다.
void handleCommand(char c, const char *from) {
  if (c == '\r' || c == '\n') return;     // 시리얼 모니터가 붙이는 줄바꿈

  if (c == CMD_FORWARD) {
    if (!moving || RESTART_TIMER_ON_REPEAT) {
      moveStartedAt = millis();
    }
    if (!moving) goForward();
    Serial.print(from);
    Serial.println(F(": F -> 앞으로"));
  } else if (c == CMD_STOP) {
    stopCar();
    Serial.print(from);
    Serial.println(F(": S -> 멈춤"));
  } else {
    Serial.print(from);
    Serial.print(F(": 모르는 글자 무시 (코드 "));
    Serial.print((int)(unsigned char)c);
    Serial.println(F(")"));
  }
}

void setup() {
  stopCar();                              // 켜지면 멈춘 상태로 시작
  Serial.begin(BAUD);
  bluetooth.begin(BAUD);
  Serial.println(F("car 준비됨. F = 앞으로, S = 멈춤"));
}

void loop() {
  while (bluetooth.available() > 0) {
    handleCommand((char)bluetooth.read(), "BT");
  }
  while (Serial.available() > 0) {
    handleCommand((char)Serial.read(), "USB");
  }

  // 스스로 멈추기: delay() 없이 millis()로 재서, 가는 도중에도 S를 바로 받는다.
  if (moving && millis() - moveStartedAt >= FORWARD_MS) {
    stopCar();
    Serial.println(F("시간 끝 -> 멈춤"));
  }
}
