"""노트북 두 대 사이의 길(UDP)이 열려 있는지 보는 작은 시험 도구(11/19 협동 레이싱).

P2 노트북이 P1 노트북에게 글자를 보내고, P1이 받았다고 답하는지 확인한다.
차와 블루투스는 쓰지 않는다. 몸 인식 프로그램에도 붙지 않은 따로 도는 도구이고,
파이썬 기본 부품(socket)만 쓰므로 pip 설치가 필요 없다.

쓰는 법 (motion 폴더에서, 윈도우 예시)
  1) P1 노트북(받는 쪽):   .venv\\Scripts\\python.exe net_check.py listen
     → 화면에 「이 노트북의 주소」가 나온다. 이 숫자를 P2 에서 쓴다.
     → 처음 켤 때 윈도우가 「네트워크 접근을 허용할까요?」라고 물으면 허용한다.
  2) P2 노트북(보내는 쪽): .venv\\Scripts\\python.exe net_check.py send 192.168.0.12
     (끝의 숫자는 1)에서 나온 P1 의 주소로 바꾼다)
  3) P2 에서 10초 동안 0.15초마다 글자 A 를 보내고, 끝나면 결과를 보여 준다. P1 에서는 Ctrl+C 로 끄면 받은 결과가 나온다.

결과 읽는 법
  보낸 것 = 받은 응답이면 길이 열려 있다. 응답이 0이면 막혀 있다.
  차는 글자가 약 0.3초 안에 다시 오지 않으면 그 입력을 끈다(아두이노 세션 설계).
  그래서 「0.3초 넘게 끊긴 횟수」가 0에 가까워야 하고, 응답 시간(왕복)이 0.15초보다 훨씬 짧아야 한다.
"""

import argparse
import select
import socket
import sys
import threading
import time
from collections import deque

DEFAULT_PORT = 5005
ALLOWED = "WASDX"          # 협동 레이싱에서 쓰는 글자. 이 밖의 것은 버린다
DEFAULT_INTERVAL = 0.15    # 글자를 보내는 간격(초). 프로그램의 --repeat-seconds 기본값과 같다
GAP_LIMIT = 0.3            # 차가 글자를 이보다 오래 못 받으면 그 입력을 끈다
PRINT_GAP = 0.5            # 같은 글자를 이보다 오래 쉬었다 받으면 새로 누른 것으로 보고 한 줄 찍는다


def local_addresses():
    """이 노트북의 주소 후보. 와이파이에 연결된 주소가 맨 앞에 온다."""
    found = []
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))    # UDP 는 연결해도 실제로 보내지 않는다. 어느 쪽 길로 나갈지만 알아낸다
        found.append(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            if address not in found and not address.startswith("127."):
                found.append(address)
    except OSError:
        pass
    return found


def make_listener(port, host="0.0.0.0"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    return sock


class SourceStats:
    """보낸 노트북(주소) 하나에서 받은 글자의 기록."""

    def __init__(self):
        self.count = 0
        self.last_time = None
        self.last_letter = ""
        self.max_gap = 0.0
        self.total_gap = 0.0
        self.over_limit = 0

    def add(self, letter, now):
        gap = None if self.last_time is None else now - self.last_time
        if gap is not None:
            self.total_gap += gap
            self.max_gap = max(self.max_gap, gap)
            if gap > GAP_LIMIT:
                self.over_limit += 1
        show = self.last_time is None or letter != self.last_letter or gap > PRINT_GAP
        self.count += 1
        self.last_time, self.last_letter = now, letter
        return show

    @property
    def average_gap(self):
        return self.total_gap / (self.count - 1) if self.count > 1 else 0.0


def listen_loop(sock, stop, log=print, now=time.monotonic):
    """받아서 답하는 쪽. stop 이 켜지면 끝나고 ({주소: SourceStats}, 버린 개수)를 돌려준다."""
    sock.settimeout(0.2)
    stats = {}
    ignored = 0
    try:
        while not stop.is_set():
            try:
                data, address = sock.recvfrom(64)
            except socket.timeout:
                continue
            except ConnectionResetError:    # 윈도우에서 상대가 사라졌을 때 가끔 나온다. 무시한다
                continue
            except OSError:
                break
            letter = data.decode("ascii", "ignore")
            if len(letter) != 1 or letter not in ALLOWED:
                ignored += 1
                continue
            source = stats.setdefault(address[0], SourceStats())
            if source.add(letter, now()):
                log(f"[받음] {address[0]} → {letter}")
            try:
                sock.sendto(data, address)    # 받았다는 답. 보낸 글자를 그대로 돌려준다
            except OSError:
                pass
    except KeyboardInterrupt:    # Ctrl+C 로 끄면 지금까지 받은 결과를 보여 준다
        pass
    return stats, ignored


def print_listen_summary(stats, ignored, log=print):
    log()
    log("[받은 결과]")
    if not stats:
        log("  아무것도 못 받았습니다. 길이 막혔거나 주소·포트가 다를 수 있습니다.")
    for address, s in stats.items():
        log(f"  {address}: 글자 {s.count}번 받음, 평균 간격 {s.average_gap * 1000:.0f} ms, "
            f"가장 긴 간격 {s.max_gap * 1000:.0f} ms, 0.3초 넘게 끊긴 횟수 {s.over_limit}번")
    if ignored:
        log(f"  W A S D X 가 아니거나 한 글자가 아니어서 버린 것 {ignored}번")


def send_test(host, port, seconds, interval, letter, log=print, now=time.monotonic):
    """보내는 쪽. 결과 {sent, answered, refused, errors, rtt_avg_ms, rtt_max_ms}를 돌려준다."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = answered = refused = errors = 0
    rtts = []
    pending = deque()      # 보낸 시각. 답이 오면 앞에서부터 짝을 지어 왕복 시간을 잰다(대략의 값)
    reported = False
    start = now()
    next_send = start
    end = start + seconds
    deadline = end + 0.5    # 마지막 글자의 답을 조금 더 기다린다
    while now() < deadline:
        if now() >= next_send and now() < end:
            try:
                sock.sendto(letter.encode("ascii"), (host, port))
                sent += 1
                pending.append(now())
            except OSError as error:
                errors += 1
                if not reported:
                    log(f"[보내기 실패] {error}")
                    reported = True
            next_send += interval
        target = next_send if next_send < end else deadline    # 다음 글자 때까지, 다 보냈으면 마지막 답을 기다릴 때까지
        ready, _, _ = select.select([sock], [], [], max(0.0, min(target, deadline) - now()))
        if ready:
            try:
                sock.recvfrom(64)
            except ConnectionResetError:    # 상대가 이 포트를 열고 있지 않다는 신호가 돌아온 것
                refused += 1
                continue
            except OSError:
                continue
            if pending:
                rtts.append((now() - pending.popleft()) * 1000)
                answered += 1
        while pending and now() - pending[0] > 1.0:    # 1초 넘게 답이 없으면 잃은 것으로 본다
            pending.popleft()
    sock.close()
    return {
        "sent": sent, "answered": answered, "refused": refused, "errors": errors,
        "rtt_avg_ms": sum(rtts) / len(rtts) if rtts else 0.0, "rtt_max_ms": max(rtts) if rtts else 0.0,
    }


def print_send_summary(result, log=print):
    log()
    log("[보낸 결과]")
    log(f"  글자 {result['sent']}번 보냄, 답 {result['answered']}번 받음")
    if result["answered"]:
        log(f"  왕복 시간 평균 {result['rtt_avg_ms']:.0f} ms, 가장 긴 것 {result['rtt_max_ms']:.0f} ms (대략의 값)")
    lost = result["sent"] - result["answered"]
    if result["sent"] and result["answered"] == result["sent"]:
        log("  → 길이 열려 있습니다. 보낸 글자에 모두 답이 왔습니다.")
    elif result["answered"]:
        log(f"  → 길은 열려 있지만 {lost}번은 답이 안 왔습니다(잃었거나 늦음). 와이파이 상태를 봐 주세요.")
    else:
        log("  → 답이 하나도 안 왔습니다. 아래를 확인해 보세요.")
        log("     1) P1 노트북에서 listen 이 켜져 있나요?  2) 주소가 P1 노트북의 것이 맞나요?")
        log("     3) 두 노트북이 같은 와이파이인가요?  4) 윈도우 방화벽이 허용되어 있나요(listen 을 켤 때 뜬 창)?")
        log("     5) 학교·공공 와이파이가 기기끼리의 통신을 막고 있을 수 있습니다.")
    if result["refused"]:
        log(f"  상대 노트북이 이 포트를 열고 있지 않다는 신호가 {result['refused']}번 돌아왔습니다.")
    if result["errors"]:
        log(f"  보내지 못한 것 {result['errors']}번")


def main(argv=None):
    parser = argparse.ArgumentParser(description="노트북 두 대 사이의 길(UDP) 시험 도구. 차와 블루투스는 쓰지 않습니다.")
    sub = parser.add_subparsers(dest="mode", required=True)
    listen = sub.add_parser("listen", help="P1 노트북에서 켠다. 받아서 답한다")
    listen.add_argument("--port", type=int, default=DEFAULT_PORT)
    send = sub.add_parser("send", help="P2 노트북에서 켠다. P1 의 주소를 적는다")
    send.add_argument("host", help="P1 노트북의 주소. 예: 192.168.0.12")
    send.add_argument("--port", type=int, default=DEFAULT_PORT)
    send.add_argument("--seconds", type=float, default=10.0, help="보내는 시간(초)")
    send.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="글자를 보내는 간격(초)")
    send.add_argument("--letter", default="A", choices=list(ALLOWED), help="보낼 글자")
    args = parser.parse_args(argv)

    if args.mode == "listen":
        try:
            sock = make_listener(args.port)
        except OSError as error:
            print(f"[오류] 포트 {args.port} 를 열지 못했습니다: {error}")
            print("       같은 도구가 이미 켜져 있거나 다른 프로그램이 쓰고 있을 수 있습니다.")
            return 1
        addresses = local_addresses()
        print(f"[받는 쪽] 포트 {args.port} 에서 기다립니다.")
        if addresses:
            print("[이 노트북의 주소] " + ", ".join(addresses) + "   ← 와이파이에 연결된 주소를 P2 에서 씁니다.")
        print("처음 켤 때 윈도우가 네트워크 접근을 물으면 「허용」을 누르세요. 끌 때는 Ctrl+C 입니다.")
        stats, ignored = listen_loop(sock, threading.Event())
        sock.close()
        print_listen_summary(stats, ignored)
        return 0

    print(f"[보내는 쪽] {args.host}:{args.port} 로 {args.letter} 를 {args.interval:.2f}초마다 {args.seconds:.0f}초 동안 보냅니다...")
    try:
        result = send_test(args.host, args.port, args.seconds, args.interval, args.letter)
    except KeyboardInterrupt:
        print("\n[중단] Ctrl+C")
        return 1
    print_send_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
