"""노트북 두 대를 잇는 길(UDP). 협동 레이싱에서 차에는 블루투스 모듈이 1개라서 쓴다(11/19 sunbell 결정).

P2 노트북(보내는 쪽, UdpLink)  : 포트 대신 P1 노트북의 주소로 글자를 보낸다. 받았다는 답으로 연결 상태를 본다.
P1 노트북(받는 쪽, UdpListener): P2 가 보낸 W A S D 를 받아 자기 차 포트(또는 가짜 보내기)로 넘긴다.

- 글자는 한 글자짜리 UDP 편지이다. 한두 장 잃어도 0.15초 뒤에 같은 글자가 또 온다.
- 받는 쪽은 W A S D X Z H 한 글자만 받고(답을 보냄) 나머지는 버린다. 그중 차로 넘기는 것은 H 를 뺀 W A S D X Z 이다.
  멈춤 글자는 축마다 따로다(11/20 sunbell 결정): X = 앞뒤만 끔, Z = 좌우만 끔. 그래서 P2 가 팔을 내리며 보낸 Z 는
  P1 의 앞뒤 입력을 끊지 않고 그대로 차로 넘어간다.
  차는 약 0.3초 글자가 없으면 그 입력을 스스로 끄므로, P2 가 끊겨도 차는 P2 의 입력만 알아서 끈다.
- H 는 「살아 있음」 신호이다. 팔을 안 들고 있어도 연결 상태를 보여 주려고 1초마다 보내고, 차로 넘기지 않는다.
- 화면에 나오는 글(status_text)은 OpenCV 글꼴이 한글을 못 그려서 영어와 숫자만 쓴다.
"""

import select
import socket
import threading
import time
from collections import deque

DEFAULT_PORT = 5005
FORWARDED = "WASDXZ"          # P1 이 차로 넘기는 글자. X = 앞뒤만 끔, Z = 좌우만 끔(11/20 sunbell 결정)
ACCEPTED = "WASDXZH"          # P1 이 받는(답을 보내는) 글자. 그 밖의 것은 버린다
HEARTBEAT = "H"
HEARTBEAT_SECONDS = 1.0       # P2 가 살아 있음 신호를 보내는 간격
REPLY_TIMEOUT = 1.5           # 이보다 오래 답이 없으면 NO REPLY
REPEAT_PRINT_GAP = 0.5        # 같은 글자를 반복해서 보낼 때, 이보다 오래 쉬었다 보내면 새로 누른 것으로 보고 한 줄 찍는다


class PrintGate:
    """반복해서 보내는 글자를 터미널에 매번 찍지 않게 한다. 글자마다, 처음이거나 한참 쉬었다 나올 때만 찍는다.

    두 사람(P1, P2)의 글자가 번갈아 와도 서로 때문에 줄이 계속 찍히지 않는다.
    """

    def __init__(self, gap=REPEAT_PRINT_GAP):
        self.gap = gap
        self._last = {}

    def should_print(self, key, now=None):
        now = time.monotonic() if now is None else now
        show = key not in self._last or now - self._last[key] > self.gap
        self._last[key] = now
        return show


def parse_address(text, default_port=DEFAULT_PORT):
    """「172.20.17.8」 또는 「172.20.17.8:5005」를 (주소, 포트)로. 잘못되면 ValueError."""
    host, _, port = text.strip().rpartition(":") if ":" in text else (text.strip(), "", "")
    if not host:
        raise ValueError(f"주소를 적어 주세요. 예: 192.168.0.12 또는 192.168.0.12:5005 ({text!r})")
    if port:
        if not port.isdigit() or not 0 < int(port) < 65536:
            raise ValueError(f"포트는 1~65535 사이 숫자여야 합니다: {port}")
        return host, int(port)
    return host, default_port


class UdpListener:
    """P1 노트북에서 P2 의 글자를 받는다. 작업 줄 하나가 받아서 답을 보내고, W A S D 는 forward 로 넘긴다."""

    def __init__(self, port, forward, allow_from=(), log=print, host="0.0.0.0"):
        self.forward = forward
        self.allow_from = set(allow_from)
        self.received = 0                # 받은 글자(W A S D X). 살아 있음 신호(H)는 따로 센다
        self.heartbeats = 0
        self.last_heartbeat = None
        self.ignored = 0
        self.blocked = 0
        self.last = None                 # (글자, 보낸 주소, 받은 시각)
        self._log = log
        self._gate = PrintGate()
        self._blocked_sources = set()
        self._stop = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((host, port))
        except OSError:
            self.sock.close()          # 포트가 이미 쓰이고 있을 때 소켓이 남지 않게 한다
            raise
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self._thread = threading.Thread(target=self._run, name="udp-listen", daemon=True)
        self._thread.start()

    def status_text(self):
        text = f"NET :{self.port} recv {self.received}"
        if self.last is not None:
            letter, _, when = self.last
            text += f"  last {letter} {time.perf_counter() - when:.1f}s ago"
        else:
            text += "  waiting"
        if self.last_heartbeat is not None:
            text += f"  hb {time.perf_counter() - self.last_heartbeat:.1f}s"    # P2 가 살아 있다는 신호를 마지막으로 받은 때
        if self.blocked:
            text += f"  blocked {self.blocked}"
        return text

    def close(self):
        self._stop.set()
        self._thread.join(1.0)
        self.sock.close()

    def _run(self):
        while not self._stop.is_set():
            try:
                data, address = self.sock.recvfrom(64)
            except socket.timeout:
                continue
            except ConnectionResetError:      # 윈도우에서 상대가 사라졌을 때 가끔 나온다
                continue
            except OSError:
                break
            source = address[0]
            if self.allow_from and source not in self.allow_from:
                self.blocked += 1
                if source not in self._blocked_sources:
                    self._blocked_sources.add(source)
                    self._log(f"[받기] 허락하지 않은 주소 {source} 에서 온 글자를 버렸습니다(--allow-from).")
                continue
            letter = data.decode("ascii", "ignore")
            if len(letter) != 1 or letter not in ACCEPTED:
                self.ignored += 1
                continue
            try:
                self.sock.sendto(data, address)     # 받았다는 답. 보낸 글자를 그대로 돌려준다
            except OSError:
                pass
            if letter == HEARTBEAT:
                self.heartbeats += 1
                self.last_heartbeat = time.perf_counter()
                continue
            self.received += 1
            self.last = (letter, source, time.perf_counter())
            if self._gate.should_print((source, letter)):
                self._log(f"[받음] {source} → {letter}")
            if letter in FORWARDED:
                self.forward(letter)


class UdpLink:
    """P2 노트북에서 글자를 P1 노트북으로 보낸다. 포트 대신 주소를 쓰는 SerialLink 의 짝(같은 모양으로 쓰인다)."""

    def __init__(self, host, port, log=print):
        self.host, self.port = host, port
        self.sent_count = 0
        self.dropped = 0
        self.slowest_write_ms = 0.0
        self.state = "connecting"          # connecting / OK / NO REPLY / ERROR
        self.rtt_ms = None
        self._log = log
        self._last_error = None
        self._lock = threading.Lock()
        self._pending = deque()            # 보낸 시각. 답이 오면 앞에서부터 짝지어 왕복 시간을 잰다(대략의 값)
        self._last_ack = None
        self._started = time.monotonic()
        self._stop = threading.Event()
        # 주소를 못 찾으면 여기서 socket.gaierror(OSError) 가 난다. 부르는 쪽(make_link)이 알아서 처리한다
        self._target = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._thread = threading.Thread(target=self._run, name="udp-send", daemon=True)
        self._thread.start()

    def status_text(self):
        target = f"{self.host}:{self.port}"
        if self.state == "OK":
            rtt = f" {self.rtt_ms:.0f}ms" if self.rtt_ms is not None else ""
            return f"OUTPUT UDP {target} OK{rtt}"
        if self.state == "NO REPLY":
            return f"OUTPUT UDP {target} NO REPLY"
        if self.state == "ERROR":
            return f"OUTPUT UDP {target} ERROR"
        return f"OUTPUT UDP {target} connecting..."

    def send(self, letter):
        """P1 으로 보내고 True. 이 노트북에서 길이 없어서 못 보내면 버리고 False."""
        if self._send_raw(letter, count=True):
            return True
        self.dropped += 1
        return False

    def close(self, final_letter=""):
        for letter in final_letter:          # 끌 때 글자가 여럿이어도(예: XZ) 한 글자씩 따로 보낸다. 받는 쪽은 한 글자짜리만 받는다
            self._send_raw(letter, count=True)
        self._stop.set()
        self._thread.join(1.0)
        self.sock.close()

    def _send_raw(self, letter, count):
        started = time.perf_counter()
        try:
            self.sock.sendto(letter.encode("ascii"), self._target)
        except OSError as error:
            self.state = "ERROR"
            self._report(f"{self.host}:{self.port} 로 보내지 못했습니다: {error}")
            return False
        self.slowest_write_ms = max(self.slowest_write_ms, (time.perf_counter() - started) * 1000)
        with self._lock:
            self._pending.append(time.perf_counter())
        if count:
            self.sent_count += 1
        self._last_error = None
        return True

    def _report(self, message):
        if message != self._last_error:
            self._log(f"[보내기] {message}")
            self._last_error = message

    def _run(self):
        next_heartbeat = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_heartbeat:
                self._send_raw(HEARTBEAT, count=False)
                next_heartbeat = now + HEARTBEAT_SECONDS
            try:
                ready, _, _ = select.select([self.sock], [], [], 0.05)
                if ready:
                    self.sock.recvfrom(64)
                    self._got_reply()
            except ConnectionResetError:       # 상대가 이 포트를 열고 있지 않다는 신호
                pass
            except OSError:
                if self._stop.is_set():
                    break
            self._update_state()

    def _got_reply(self):
        with self._lock:
            if self._pending:
                self.rtt_ms = (time.perf_counter() - self._pending.popleft()) * 1000
        self._last_ack = time.monotonic()

    def _update_state(self):
        with self._lock:
            while self._pending and time.perf_counter() - self._pending[0] > 1.0:
                self._pending.popleft()        # 1초 넘게 답이 없으면 잃은 것으로 본다
        if self.state == "ERROR" and self._last_error is not None:
            return                             # 보내지 못하는 중에는 ERROR 를 유지한다
        if self._last_ack is not None and time.monotonic() - self._last_ack <= REPLY_TIMEOUT:
            self.state = "OK"
        elif time.monotonic() - self._started > REPLY_TIMEOUT:
            self.state = "NO REPLY"
