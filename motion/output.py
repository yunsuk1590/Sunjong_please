"""몸 동작 결과를 글자 하나로 밖에 보낸다(11/11 학과 발표회 시연용).

흐름: 떨림 방지를 거친 결과(STABLE) → 동작이 켜지는 순간을 찾음 → 글자 하나를 COM 포트로 보냄

- 포트를 적지 않으면(--port 없음) 아무 데도 보내지 않고 화면과 터미널에만 표시한다(가짜 보내기).
- 블루투스 포트는 여는 데 몇 초 걸릴 수 있어서, 따로 도는 작업 줄에서 열고 보낸다. 그래서 화면이 멈추지 않는다.
- 포트는 시작할 때 한 번 열어 계속 열어 둔다. 끊기면 몇 초마다 다시 연다. 프로그램은 꺼지지 않는다.
- 포트가 열려 있지 않을 때 나온 글자는 쌓아 두지 않고 **버린다**.
  쌓아 두면 연결되는 순간 아무도 팔을 들지 않았는데 차가 출발할 수 있기 때문이다.
- "포트가 열림"은 글자가 차까지 도착했다는 뜻이 아니다. 도착 확인은 docs/plan-motion-recognition.md 의 시험표를 본다.
"""

import threading
from importlib.util import find_spec

RETRY_SECONDS = 3.0    # 포트가 안 열리거나 끊기면 이만큼 기다렸다가 다시 연다
WATCH_SECONDS = 0.5    # 보낼 글자가 없을 때 이만큼마다 포트가 살아 있는지 본다
WRITE_TIMEOUT = 2.0    # 글자 하나를 보내는 데 이보다 오래 걸리면 끊긴 것으로 본다
CLOSE_WAIT = 3.0       # 끌 때 작업 줄을 이만큼만 기다린다. 포트가 응답하지 않아도 프로그램은 꺼진다


class LetterTrigger:
    """STABLE 결과를 보고 글자를 보낼 순간을 찾는다.

    state 가 꺼짐에서 켜짐으로 바뀌는 순간에 on_letter 를, 켜짐에서 꺼짐으로 바뀌는 순간에 off_letter 를 고른다.
    off_letter 가 빈칸이면 꺼질 때는 아무것도 보내지 않는다.

    떨림 방지가 상태를 끄면 다음에 켜질 때 다시 글자를 고른다. 그래서 아래 두 경우에도 글자가 나간다.
    - 프로그램을 켤 때 이미 팔을 들고 있었던 경우
    - 팔을 든 채로 사람을 lost 초(0.5초)보다 오래 놓쳤다가 다시 잡은 경우
    """

    def __init__(self, state, on_letter, off_letter=""):
        self.state = state
        self.on_letter = on_letter
        self.off_letter = off_letter
        self.active = False

    def update(self, stable):
        """stable: {동작 이름: 인정된 상태 또는 None}. 지금 보낼 글자를 돌려준다. 없으면 빈칸."""
        active = self.state in stable.values()
        letter = ""
        if active and not self.active:
            letter = self.on_letter
        elif self.active and not active:
            letter = self.off_letter
        self.active = active
        return letter


class FakeLink:
    """가짜 보내기. 포트를 쓸 수 없을 때 화면과 터미널에만 표시한다."""

    def __init__(self, note):
        self.note = note
        self.sent_count = 0
        self.dropped = 0

    def status_text(self):
        return f"OUTPUT {self.note}"

    def send(self, letter):
        self.sent_count += 1
        print(f"[가짜 보내기] {letter}")
        return True

    def close(self, final_letter=""):
        if final_letter:
            print(f"[가짜 보내기] {final_letter} (끌 때)")


def open_serial(port, baud):
    """포트를 연다. COM5 같은 포트와 시험용 가상 포트(loop://)를 같은 방법으로 열 수 있다."""
    import serial   # pyserial 이 없어도 프로그램이 켜지도록 여기서 부른다. 설치 여부는 make_link 가 먼저 본다

    # flush() 는 쓰지 않는다. 윈도우에서 끝없이 기다릴 수 있고, write_timeout 을 주면 write() 가 끝까지 확인한다
    return serial.serial_for_url(port, baudrate=baud, timeout=0, write_timeout=WRITE_TIMEOUT)


class SerialLink:
    """COM 포트 담당. 따로 도는 작업 줄이 포트를 열고 글자를 보낸다."""

    def __init__(self, port, baud, open_port=open_serial, retry_seconds=RETRY_SECONDS):
        self.port = port
        self.baud = baud
        self.open_port = open_port
        self.retry_seconds = retry_seconds
        self.state = "connecting"    # connecting / OPEN / ERROR
        self.sent_count = 0
        self.dropped = 0
        self._last_error = None
        self._lock = threading.Lock()
        self._pending = ""           # 보낼 글자 1개. 쌓지 않는다. 새 글자가 오면 옛 글자를 덮어쓴다
        self._final = ""             # 끌 때 마지막으로 보낼 글자
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="serial", daemon=True)
        self._thread.start()

    def status_text(self):
        if self.state == "OPEN":
            return f"OUTPUT {self.port} OPEN"
        if self.state == "ERROR":
            return f"OUTPUT {self.port} ERROR - retrying"
        return f"OUTPUT {self.port} connecting..."

    def send(self, letter):
        """포트가 열려 있으면 작업 줄에 넘기고 True, 아니면 글자를 버리고 False."""
        if self.state != "OPEN":
            self._drop(letter, "포트가 열려 있지 않습니다")
            return False
        with self._lock:
            self._pending = letter
        self._wake.set()
        return True

    def close(self, final_letter=""):
        self._final = final_letter
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=CLOSE_WAIT)
        if self._thread.is_alive():
            print(f"[보내기] {self.port} 포트가 응답하지 않아 기다리지 않고 끕니다.")

    def _drop(self, letter, reason):
        with self._lock:
            self.dropped += 1
        print(f"[보내기] {letter} 를 보내지 못하고 버렸습니다: {reason}")

    def _run(self):
        port = None
        while not self._stop.is_set():
            if port is None:
                port = self._open()
                if port is None:
                    self._stop.wait(self.retry_seconds)
                continue
            self._wake.wait(WATCH_SECONDS)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                self._send_or_watch(port)
            except OSError as e:
                self._lost(port, e)
                port = None
        if port is not None:
            self._finish(port)

    def _open(self):
        try:
            port = self.open_port(self.port, self.baud)
        except (OSError, ValueError) as e:
            self.state = "ERROR"
            self._report_error(f"{self.port} 포트를 열지 못했습니다. {self.retry_seconds:.0f}초마다 다시 시도합니다: {e}")
            return None
        with self._lock:
            self._pending = ""    # 끊기기 전에 받은 글자를 연결된 뒤에 보내지 않는다
        self._last_error = None
        self.state = "OPEN"
        print(f"[보내기] {self.port} 포트를 열었습니다(통신 속도 {self.baud}).")
        return port

    def _send_or_watch(self, port):
        with self._lock:
            letter, self._pending = self._pending, ""
        if not letter:
            # 보낼 글자가 없으면 포트가 살아 있는지 본다. 보드가 보낸 글자는 쓰지 않으니 읽어서 버린다
            waiting = port.in_waiting
            if waiting:
                port.read(waiting)
            return
        try:
            port.write(letter.encode("ascii"))
        except OSError:
            self._drop(letter, "보내는 도중에 연결이 끊겼습니다")
            raise
        self.sent_count += 1
        print(f"[보내기] {letter} 보냄 → {self.port}")

    def _lost(self, port, error):
        self.state = "ERROR"
        self._report_error(f"{self.port} 연결이 끊겼습니다. 다시 연결을 시도합니다: {error}")
        self._close_port(port)

    def _finish(self, port):
        """끌 때 마지막 글자를 보내고 포트를 닫는다."""
        if self._final:
            try:
                port.write(self._final.encode("ascii"))
                self.sent_count += 1
                print(f"[보내기] {self._final} 보냄 → {self.port} (끌 때)")
            except OSError as e:
                print(f"[보내기] 끌 때 {self._final} 를 보내지 못했습니다: {e}")
        self._close_port(port)

    @staticmethod
    def _close_port(port):
        try:
            port.close()
        except OSError:
            pass

    def _report_error(self, message):
        """같은 오류를 몇 초마다 되풀이해서 찍지 않는다."""
        if message != self._last_error:
            print(f"[보내기] {message}")
            self._last_error = message


class LetterOutput:
    """run.py 가 부르는 창구. 글자를 보낼 순간을 찾아 보내고, 화면에 보여 줄 한 줄을 만든다."""

    def __init__(self, link, trigger, quit_letter=""):
        self.link = link
        self.trigger = trigger
        self.quit_letter = quit_letter
        self._last = None    # (화면에 보여 줄 말, 시각)

    def update(self, stable, now):
        letter = self.trigger.update(stable)
        if letter:
            sent = self.link.send(letter)
            self._last = (letter if sent else f"{letter} dropped", now)

    def status_text(self, now):
        text = f"{self.link.status_text()}  sent {self.link.sent_count}  dropped {self.link.dropped}"
        if self._last is not None:
            what, when = self._last
            text += f"  last {what} {now - when:.1f}s ago"
        return text

    def close(self):
        self.link.close(self.quit_letter)
        print(f"[보내기] 보낸 글자 {self.link.sent_count}번, 못 보내고 버린 글자 {self.link.dropped}번")


def make_link(args):
    if not args.port:
        print("[보내기] 포트를 적지 않아서 글자를 보내지 않고 화면과 터미널에만 표시합니다. (보내려면 예: run.bat --port COM5)")
        return FakeLink("no port (fake)")
    if find_spec("serial") is None:
        print("[보내기] pyserial 이 설치되어 있지 않아서 글자를 보내지 못합니다. setup 을 다시 실행해 주세요.")
        return FakeLink("no pyserial (fake)")
    print(f"[보내기] {args.port} 포트를 여는 중입니다. 블루투스는 몇 초 걸릴 수 있습니다...")
    return SerialLink(args.port, args.baud)


def make_output(args):
    trigger = LetterTrigger(args.send_on, args.letter_on, args.letter_off)
    return LetterOutput(make_link(args), trigger, args.letter_quit)
