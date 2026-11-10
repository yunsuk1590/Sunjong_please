// car_backup.ino
// 11/11 학과 발표회용 예비 차 코드 (sunbell/arduino 브랜치)
//
// 노트북이 보낸 글자 하나를 받아 차를 앞으로 보내거나 멈춥니다.
// - 블루투스(HC-06)와 USB 선, 두 곳에서 같은 글자를 받습니다.
// - F 를 받으면 정해진 시간만 앞으로 가고 스스로 멈춥니다.
// - 가는 도중에도 S 를 받으면 바로 멈춥니다(delay 대신 millis 로 시간을 잼).
//
// 키트 예제 코드는 옮기지 않고 새로 썼습니다. 배선(모터 단자, 블루투스 핀)만 키트 자료에서 확인했습니다.
// 자세한 기록: 같은 폴더의 README.md

#include <AFMotor.h>          // Adafruit Motor Shield library V1 (L293D 모터 쉴드)
#include <SoftwareSerial.h>   // HC-06 블루투스용

// ===== 글자 약속 (2026-11-08 sunbell 결정) =====
const char LETTER_FORWARD = 'F';  // 앞으로 (대문자)
const char LETTER_STOP    = 'S';  // 멈춤 (대문자)
// 그 밖의 글자, 줄바꿈(\r, \n)은 무시합니다.

// ===== 바꿀 수 있는 값 =====
const uint8_t       DRIVE_SPEED   = 255;   // 모터 속도(0~255). 2026-11-11 sunbell 결정: 바닥에서 200은 출발하지 못함(AA 건전지)
const unsigned long DRIVE_TIME_MS = 1000;  // 【임시】 F 하나에 앞으로 가는 시간(ms). sunbell과 yunsuk1590이 정함
const bool RESTART_TIMER_ON_F     = true;  // 【임시】 가는 도중 F 가 또 오면 true = 시간을 다시 잼, false = 무시. sunbell과 yunsuk1590이 정함

const long USB_BAUD = 9600;  // USB 통신 속도 (2026-11-08 sunbell 결정)
const long BT_BAUD  = 9600;  // 블루투스 통신 속도 (2026-11-08 sunbell 결정)

// ===== 배선 (키트 자료 기준, 조립한 차에서 확인) =====
const uint8_t BT_RX_PIN = A5;  // 아두이노가 받는 핀
const uint8_t BT_TX_PIN = A4;  // 아두이노가 보내는 핀

// 바퀴가 거꾸로 돌면 그 바퀴의 값만 FORWARD <-> BACKWARD 로 바꿉니다.
const uint8_t LEFT_FORWARD_DIR  = FORWARD;
const uint8_t RIGHT_FORWARD_DIR = FORWARD;

AF_DCMotor leftWheel(1);   // 왼쪽 바퀴 = 쉴드 M1
AF_DCMotor rightWheel(4);  // 오른쪽 바퀴 = 쉴드 M4
SoftwareSerial bluetooth(BT_RX_PIN, BT_TX_PIN);

// ===== 지금 상태 =====
bool driving = false;              // 앞으로 가는 중인지
unsigned long driveStartedAt = 0;  // 마지막으로 출발 시간을 잰 때(millis)

void setup() {
  Serial.begin(USB_BAUD);
  bluetooth.begin(BT_BAUD);

  leftWheel.setSpeed(DRIVE_SPEED);
  rightWheel.setSpeed(DRIVE_SPEED);
  releaseWheels();  // 켜지면 멈춘 상태로 시작

  Serial.println(F("car_backup 시작: 멈춤 상태. F=앞으로, S=멈춤"));
}

void loop() {
  while (Serial.available() > 0) {
    handleLetter(Serial.read(), F("USB"));
  }
  while (bluetooth.available() > 0) {
    handleLetter(bluetooth.read(), F("BT"));
  }

  // 정해진 시간이 지나면 스스로 멈춤 (millis 가 한 바퀴 돌아도 빼기로 재면 맞음)
  if (driving && millis() - driveStartedAt >= DRIVE_TIME_MS) {
    stopCar(F("시간 끝"));
  }
}

// 글자 -> 동작. 약속이 바뀌면 여기와 맨 위 글자 약속만 고칩니다.
void handleLetter(int letter, const __FlashStringHelper *source) {
  if (letter == '\r' || letter == '\n') {
    return;  // 시리얼 모니터가 붙이는 줄바꿈은 조용히 무시
  }

  printSource(source, letter);

  switch (letter) {
    case LETTER_FORWARD:
      goForward();
      break;
    case LETTER_STOP:
      stopCar(F("S 받음"));
      break;
    default:
      Serial.println(F("모르는 글자 -> 무시"));
      break;
  }
}

void goForward() {
  if (driving && !RESTART_TIMER_ON_F) {
    Serial.println(F("가는 중 -> 무시"));
    return;
  }

  driveStartedAt = millis();
  if (driving) {
    Serial.println(F("가는 중 -> 시간 다시 잼"));
    return;
  }

  leftWheel.run(LEFT_FORWARD_DIR);
  rightWheel.run(RIGHT_FORWARD_DIR);
  driving = true;
  Serial.print(F("앞으로 ("));
  Serial.print(DRIVE_TIME_MS);
  Serial.println(F("ms)"));
}

void stopCar(const __FlashStringHelper *reason) {
  releaseWheels();
  driving = false;
  Serial.print(reason);
  Serial.println(F(" -> 멈춤"));
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
