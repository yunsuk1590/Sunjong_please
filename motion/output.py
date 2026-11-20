"""몸 동작 결과를 글자 하나로 밖에 보낸다(11/11 학과 발표회 시연용, 11/19 협동 레이싱용으로 넓힘).

흐름: 떨림 방지를 거친 결과(STABLE) → 동작에 맞는 글자를 고름 → 글자 하나를 COM 포트로 보냄
- once(11/11 방식, 리듬게임용): 동작이 켜지는 순간 한 번만 보낸다.
- repeat(컨트롤러식, 협동 레이싱): 동작이 켜져 있는 동안 같은 글자를 짧은 간격마다 다시 보낸다.
  팔을 내리면 그 축의 멈춤 글자(앞뒤 X, 좌우 Z)를 연달아 보내서 차가 바로 서게 한다(11/20 sunbell 결정).
  멈춤 글자를 잃어도 차는 약 0.3초 글자가 없으면 그 입력을 스스로 끈다.

- 포트를 적지 않으면(--port 없음) 아무 데도 보내지 않고 화면과 터미널에만 표시한다(가짜 보내기).
- 블루투스 포트는 여는 데 몇 초 걸릴 수 있어서, 따로 도는 작업 줄에서 열고 보낸다. 그래서 화면이 멈추지 않는다.
- 포트는 시작할 때 한 번 열어 계속 열어 둔다. 끊기면 몇 초마다 다시 연다. 프로그램은 꺼지지 않는다.
- 포트가 열려 있지 않을 때 나온 글자는 쌓아 두지 않고 **버린다**.
  쌓아 두면 연결되는 순간 아무도 팔을 들지 않았는데 차가 출발할 수 있기 때문이다.
- "포트가 열림"은 글자가 차까지 도착했다는 뜻이 아니다. 도착 확인은 docs/plan-motion-recognition.md 의 시험표를 본다.
"""

import threading
import time
from collections import namedtuple
from importlib.util import find_spec

from config import AXIS_STOP, ROLE_LETTERS
from netlink import PrintGate, UdpLink, UdpListener, parse_address   # PrintGate 는 netlink 에 있다(순환 import 를 피하려고)

RETRY_SECONDS = 3.0    # 포트가 안 열리거나 끊기면 이만큼 기다렸다가 다시 연다
WATCH_SECONDS = 0.5    # 보낼 글자가 없을 때 이만큼마다 포트가 살아 있는지 본다
WRITE_TIMEOUT = 2.0    # 글자 하나를 보내는 데 이보다 오래 걸리면 끊긴 것으로 본다
CLOSE_WAIT = 3.0       # 끌 때 작업 줄을 이만큼만 기다린다. 포트가 응답하지 않아도 프로그램은 꺼진다


class LetterTrigger:
    """STABLE 결과를 보고 글자를 보낼 순간을 찾는다.

    letters: {동작 상태 이름: 글자}. 예) {"ARMS_UP": "F"} 또는 {"ARMS_UP": "W", "T_POSE": "S"}
    - 동작이 꺼짐에서 켜짐으로 바뀌는 순간(또는 다른 동작으로 바로 바뀐 순간)에 그 동작의 글자를 고른다.
    - 켜짐에서 꺼짐으로 바뀌는 순간에는 off_letter 를 고른다. off_letter 가 빈칸이면 아무것도 보내지 않는다.
    - repeat_seconds 가 0보다 크면(컨트롤러식, 11/19) 동작이 켜져 있는 동안 그 간격마다 같은 글자를 다시 고른다.
      0이면 켜지는 순간 한 번만 고른다(11/11 방식, 리듬게임용으로 남겨 둠).

    stops 를 주면(11/20 sunbell 결정) off_letter 대신 축마다 멈춤 글자를 쓴다.
    stops: {글자: 멈춤 글자}. 예) {"W": "X", "S": "X", "A": "Z", "D": "Z"} (X = 앞뒤만 끔, Z = 좌우만 끔)
    - 그 축의 동작이 꺼지는 순간 멈춤 글자를 고른다. 같은 축 안에서 바로 바뀌면(W 에서 S) 멈춤 글자를 보내지 않는다.
    - 다른 축으로 바로 바뀌면(W 에서 A) 앞 축의 멈춤 글자(X)와 새 글자(A)를 함께 고른다.
    - 멈춤 글자는 stop_repeats 번 연달아 보낸다(처음은 바로, 나머지는 repeat_seconds 간격). 글자 하나를 잃어도 서게 하려는 것이다.
      그 사이에 같은 축이 다시 켜지면 남은 멈춤 글자는 보내지 않는다(새로 켠 입력을 멈추지 않게).

    update() 는 지금 보낼 글자들을 **문자열**로 돌려준다(없으면 빈칸, 두 글자 이상일 수 있다).

    떨림 방지가 상태를 끄면 다음에 켜질 때 다시 글자를 고른다. 그래서 아래 두 경우에도 글자가 나간다.
    - 프로그램을 켤 때 이미 팔을 들고 있었던 경우
    - 팔을 든 채로 사람을 lost 초(0.5초)보다 오래 놓쳤다가 다시 잡은 경우
    """

    def __init__(self, letters, off_letter="", repeat_seconds=0.0, stops=None, stop_repeats=1):
        self.letters = dict(letters)
        self.off_letter = off_letter
        self.repeat_seconds = repeat_seconds
        self.stops = dict(stops or {})
        self.stop_repeats = max(1, stop_repeats)
        self.current = ""          # 지금 켜져 있는 동작의 글자. 없으면 빈칸
        self._next_repeat = 0.0
        self._extra_stops = []     # [(보낼 시각, 멈춤 글자)] 연달아 보낼 나머지 멈춤 글자

    def update(self, stable, now=0.0):
        """stable: {동작 이름: 인정된 상태 또는 None}. 지금 보낼 글자들을 문자열로 돌려준다. 없으면 빈칸."""
        current = next((self.letters[s] for s in stable.values() if s in self.letters), "")
        current_stop = self.stops.get(current, "") if current else ""
        out = ""
        waiting = []
        for when, stop in self._extra_stops:
            if stop == current_stop:
                continue                      # 그 축이 다시 켜졌다. 남은 멈춤 글자는 버린다
            if now >= when:
                out += stop
            else:
                waiting.append((when, stop))
        self._extra_stops = waiting
        if current != self.current:
            if self.stops:
                previous_stop = self.stops.get(self.current, "")
                if previous_stop and previous_stop != current_stop:    # 앞 축이 꺼졌다
                    out += previous_stop
                    for k in range(1, self.stop_repeats):
                        self._extra_stops.append((now + k * self.repeat_seconds, previous_stop))
                out += current
            else:
                out += current or self.off_letter
            self._next_repeat = now + self.repeat_seconds
        elif current and self.repeat_seconds > 0 and now >= self._next_repeat:
            out += current
            self._next_repeat = now + self.repeat_seconds
        self.current = current
        return out

class FakeLink:
    """가짜 보내기. 포트를 쓸 수 없을 때 화면과 터미널에만 표시한다."""

    def __init__(self, note):
        self.note = note
        self.sent_count = 0
        self.dropped = 0
        self.slowest_write_ms = 0.0
        self._gate = PrintGate()

    def status_text(self):
        return f"OUTPUT {self.note}"

    def send(self, letter):
        self.sent_count += 1
        if self._gate.should_print(letter):
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
        self.slowest_write_ms = 0.0   # 글자 하나를 포트에 쓰는 데 가장 오래 걸린 시간(ms). 블루투스가 느린지 볼 때 쓴다
        self._last_error = None
        self._send_gate = PrintGate()
        self._drop_gate = PrintGate(gap=2.0)
        self._lock = threading.Lock()
        self._pending = {}           # 보낼 글자. 글자 종류마다 하나씩만 남기고 쌓지 않는다(같은 글자가 또 오면 합쳐진다)
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
            self._pending[letter] = True
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
        if self._drop_gate.should_print(f"{letter}{reason}"):   # 반복해서 보낼 때 같은 줄이 계속 나오지 않게 한다
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
            self._pending.clear()    # 끊기기 전에 받은 글자를 연결된 뒤에 보내지 않는다
        self._last_error = None
        self.state = "OPEN"
        print(f"[보내기] {self.port} 포트를 열었습니다(통신 속도 {self.baud}).")
        return port

    def _send_or_watch(self, port):
        with self._lock:
            letters = list(self._pending)    # 들어온 순서대로. 종류마다 하나씩이라 많아야 몇 글자이다
            self._pending.clear()
        if not letters:
            # 보낼 글자가 없으면 포트가 살아 있는지 본다. 보드가 보낸 글자는 쓰지 않으니 읽어서 버린다
            waiting = port.in_waiting
            if waiting:
                port.read(waiting)
            return
        started = time.perf_counter()
        try:
            port.write("".join(letters).encode("ascii"))
        except OSError:
            for letter in letters:
                self._drop(letter, "보내는 도중에 연결이 끊겼습니다")
            raise
        self.slowest_write_ms = max(self.slowest_write_ms, (time.perf_counter() - started) * 1000)
        self.sent_count += len(letters)
        for letter in letters:
            if self._send_gate.should_print(letter):
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
                self.sent_count += len(self._final)
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

    def __init__(self, link, trigger, quit_letter="", mode_text="", net=None):
        self.link = link
        self.trigger = trigger
        self.quit_letter = quit_letter
        self.mode_text = mode_text   # 화면에 보여 줄 역할·방식(예: "P1 repeat")
        self.net = net               # P1 노트북에서 P2 의 글자를 받는 UdpListener. 없으면 None
        self._last = None    # (화면에 보여 줄 말, 시각)

    def update(self, stable, now):
        for letter in self.trigger.update(stable, now):    # 한꺼번에 두 글자 이상 나올 수 있다(예: 멈춤 글자 + 새 글자)
            sent = self.link.send(letter)
            self._last = (letter if sent else f"{letter} dropped", now)

    def status_text(self, now):
        text = f"{self.link.status_text()}  sent {self.link.sent_count}  dropped {self.link.dropped}"
        if self.mode_text:
            text += f"  [{self.mode_text}]"
        if self._last is not None:
            what, when = self._last
            text += f"  last {what} {now - when:.1f}s ago"
        return text

    def net_status_text(self):
        """P1 노트북에서 P2 글자를 받는 상태 한 줄. 받는 쪽이 아니면 빈칸."""
        return self.net.status_text() if self.net is not None else ""

    def close(self):
        if self.net is not None:
            self.net.close()      # 받기를 먼저 멈춰서, 끄는 중에 P2 글자가 차 포트로 넘어가지 않게 한다
        self.link.close(self.quit_letter)
        print(f"[보내기] 보낸 글자 {self.link.sent_count}번, 못 보내고 버린 글자 {self.link.dropped}번")
        if self.link.slowest_write_ms:
            print(f"[보내기] 글자 하나를 포트에 쓰는 데 가장 오래 걸린 시간 {self.link.slowest_write_ms:.1f} ms")
        if self.net is not None:
            print(f"[받기] P2 쪽에서 받은 글자 {self.net.received}번, 버린 것 {self.net.ignored}번, 허락하지 않은 주소 {self.net.blocked}번")


def make_link(args):
    if args.send_to:
        try:
            host, port = parse_address(args.send_to)
            link = UdpLink(host, port)
        except (ValueError, OSError) as error:
            print(f"[보내기] 주소 {args.send_to} 를 쓸 수 없어서 글자를 보내지 않고 화면과 터미널에만 표시합니다: {error}")
            return FakeLink("bad address (fake)")
        print(f"[보내기] {host}:{port} 로 UDP 글자를 보냅니다(P1 노트북에서 --listen 이 켜져 있어야 합니다).")
        return link
    if not args.port:
        print("[보내기] 포트를 적지 않아서 글자를 보내지 않고 화면과 터미널에만 표시합니다. (보내려면 예: run.bat --port COM5)")
        return FakeLink("no port (fake)")
    if find_spec("serial") is None:
        print("[보내기] pyserial 이 설치되어 있지 않아서 글자를 보내지 못합니다. setup 을 다시 실행해 주세요.")
        return FakeLink("no pyserial (fake)")
    print(f"[보내기] {args.port} 포트를 여는 중입니다. 블루투스는 몇 초 걸릴 수 있습니다...")
    return SerialLink(args.port, args.baud)


LetterPlan = namedtuple("LetterPlan", "letters mode quit_letter shown off_letter stops")


def resolve_letters(args):
    """어떤 동작이 어떤 글자를 보낼지 정한다. 돌려주는 값 LetterPlan:
    letters {동작: 글자}, mode once/repeat, quit_letter 끌 때 글자, shown 화면 표시, off_letter 꺼질 때 한 글자, stops {글자: 멈춤 글자}.

    우선순위: --letters(직접 적은 표) > --role(역할 표) > 11/11 방식(--send-on 동작 하나가 --letter-on 글자 하나).
    방식은 --send-mode 를 적으면 그대로, 안 적으면 역할이나 글자 표가 있을 때 repeat, 없으면 once.

    멈춤 글자(11/20 sunbell 결정: 앞뒤용 X, 좌우용 Z): 방식이 repeat 이고 W A S D 를 쓰면, 안 적었을 때 축마다 멈춤 글자를 보낸다.
    --letter-off 를 적으면(빈칸 포함) 그 값 그대로 모든 동작에 쓰고 축마다 멈춤 글자는 쓰지 않는다.

    끌 때 글자는 --letter-quit 를 적으면 그대로, 안 적으면 쓰는 축의 멈춤 글자(P1 은 X, P2 는 Z, 둘 다 쓰면 XZ),
    W A S D 가 아닌 역할은 X, 11/11 방식은 S. (새 약속에서 S 는 「뒤로」라서 끌 때 S 를 보내면 차가 뒤로 간다.)
    """
    if args.letters:
        letters, name = args.letters, "custom"
    elif args.role:
        letters, name = ROLE_LETTERS[args.role], args.role
    else:
        letters, name = {args.send_on: args.letter_on}, ""
    mode = args.send_mode or ("repeat" if name else "once")
    axes = {l: AXIS_STOP[l] for l in letters.values() if l in AXIS_STOP}
    if args.letter_off is None:
        stops, off_letter = (axes if mode == "repeat" else {}), ""
    else:
        stops, off_letter = {}, args.letter_off
    if args.letter_quit is not None:
        quit_letter = args.letter_quit
    elif axes:
        quit_letter = "".join(sorted(set(axes.values())))
    else:
        quit_letter = "X" if name else "S"
    parts = [name, mode if name else "", "/".join(letters.values()) if name else ""]
    if stops:
        parts.append("stop " + "/".join(sorted(set(stops.values()))))
    return LetterPlan(letters, mode, quit_letter, " ".join(filter(None, parts)), off_letter, stops)

def make_listener(args, link):
    """P1 노트북이면(--listen) P2 가 보낸 W A S D 를 받아 같은 포트로 넘기는 받기를 켠다. 아니면 None."""
    if args.listen is None:
        return None
    try:
        listener = UdpListener(args.listen, link.send, args.allow_from)
    except OSError as error:
        print(f"[받기] 포트 {args.listen} 를 열지 못했습니다. 다른 프로그램이 쓰고 있을 수 있습니다: {error}")
        return None
    print(f"[받기] P2 노트북의 글자를 UDP 포트 {listener.port} 에서 받아 차로 넘깁니다. W A S D(가고 서기)와 X Z(멈춤)만 넘기고 나머지는 버립니다.")
    if args.allow_from:
        print(f"[받기] 허락한 주소: {', '.join(sorted(args.allow_from))}")
    else:
        print("[받기] 주의: 같은 와이파이의 아무 기기가 보낸 글자나 받아서 차로 넘깁니다. 학교 와이파이에서는 --allow-from 으로 P2 노트북의 주소를 적는 것이 안전합니다.")
    return listener


def make_output(args):
    plan = resolve_letters(args)
    repeat = args.repeat_seconds if plan.mode == "repeat" else 0.0
    trigger = LetterTrigger(plan.letters, plan.off_letter, repeat, plan.stops, args.stop_repeats)
    link = make_link(args)
    return LetterOutput(link, trigger, plan.quit_letter, plan.shown, make_listener(args, link))
