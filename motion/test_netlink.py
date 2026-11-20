"""노트북 두 대를 잇는 길(netlink.py)의 자동 시험. 같은 노트북 안(127.0.0.1)에서 돌리므로 와이파이가 없어도 된다.

motion 폴더에서 실행한다.
  윈도우: .venv\\Scripts\\python.exe -m unittest test_netlink -v
  맥:     .venv/bin/python -m unittest test_netlink -v

와이파이를 사이에 둔 실제 시험은 자동으로 할 수 없다. 두 노트북에서 직접 한다(motion/README.md 「노트북 2대로 하기」).
"""

import contextlib
import io
import socket
import time
import unittest
from unittest import mock

import config
import netlink
import output


def quiet(*_):
    pass


def wait_until(condition, seconds=3.0):
    limit = time.monotonic() + seconds
    while time.monotonic() < limit:
        if condition():
            return True
        time.sleep(0.005)
    return condition()


class Collector:
    def __init__(self):
        self.letters = []

    def __call__(self, letter):
        self.letters.append(letter)
        return True


class Quiet(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("sys.stdout", io.StringIO())
        patcher.start()
        self.addCleanup(patcher.stop)


class ParseAddress(unittest.TestCase):
    def test_host_and_optional_port(self):
        self.assertEqual(netlink.parse_address("172.20.17.8"), ("172.20.17.8", 5005))
        self.assertEqual(netlink.parse_address("172.20.17.8:6000"), ("172.20.17.8", 6000))

    def test_bad_addresses_are_refused(self):
        for bad in ("", ":5005", "172.20.17.8:abc", "172.20.17.8:0", "172.20.17.8:70000"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                netlink.parse_address(bad)


class ListenerTest(Quiet):
    def make(self, **kwargs):
        forward = Collector()
        listener = netlink.UdpListener(0, forward, log=quiet, host="127.0.0.1", **kwargs)
        self.addCleanup(listener.close)
        return listener, forward

    def raw(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        self.addCleanup(sock.close)
        return sock

    def test_driving_and_stop_letters_are_forwarded_but_not_the_heartbeat(self):
        """11/20: 멈춤 글자는 축마다 따로라서(X 앞뒤, Z 좌우) P2 의 Z 도 차로 넘어간다. 살아 있음 신호(H)만 안 넘긴다."""
        listener, forward = self.make()
        sock = self.raw()
        for letter in b"WASDXZH":
            sock.sendto(bytes([letter]), ("127.0.0.1", listener.port))
        self.assertTrue(wait_until(lambda: listener.received == 6 and listener.heartbeats == 1))
        self.assertEqual(forward.letters, ["W", "A", "S", "D", "X", "Z"])
        self.assertIn("hb ", listener.status_text())

    def test_every_accepted_letter_is_answered_and_the_rest_are_not(self):
        listener, _ = self.make()
        sock = self.raw()
        for good in (b"W", b"X", b"H"):
            sock.sendto(good, ("127.0.0.1", listener.port))
            self.assertEqual(sock.recvfrom(64)[0], good)
        for bad in (b"w", b"F", b"AB", b"", b"\r"):                # 소문자, 다른 글자, 두 글자, 빈 것, 줄바꿈
            sock.sendto(bad, ("127.0.0.1", listener.port))
        with self.assertRaises(socket.timeout):
            sock.recvfrom(64)
        self.assertTrue(wait_until(lambda: listener.ignored == 5))

    def test_unlisted_sources_are_blocked_with_allow_from(self):
        listener, forward = self.make(allow_from=["10.9.9.9"])
        sock = self.raw()
        sock.sendto(b"W", ("127.0.0.1", listener.port))
        with self.assertRaises(socket.timeout):
            sock.recvfrom(64)                                       # 답도 없다
        self.assertTrue(wait_until(lambda: listener.blocked == 1))
        self.assertEqual(forward.letters, [])
        self.assertIn("blocked 1", listener.status_text())

    def test_listed_source_is_accepted(self):
        listener, forward = self.make(allow_from=["127.0.0.1"])
        sock = self.raw()
        sock.sendto(b"D", ("127.0.0.1", listener.port))
        self.assertTrue(wait_until(lambda: forward.letters == ["D"]))

    def test_status_text_is_ascii_for_the_screen(self):
        listener, _ = self.make()
        self.assertIn("waiting", listener.status_text())
        sock = self.raw()
        sock.sendto(b"A", ("127.0.0.1", listener.port))
        self.assertTrue(wait_until(lambda: listener.last is not None))
        text = listener.status_text()
        self.assertIn("recv 1", text)
        self.assertIn("last A", text)
        self.assertTrue(text.isascii())


class LinkTest(Quiet):
    def pair(self, **listener_kwargs):
        forward = Collector()
        listener = netlink.UdpListener(0, forward, log=quiet, host="127.0.0.1", **listener_kwargs)
        self.addCleanup(listener.close)
        with mock.patch.object(netlink, "HEARTBEAT_SECONDS", 0.05):
            link = netlink.UdpLink("127.0.0.1", listener.port, log=quiet)
        self.addCleanup(link.close)
        return link, listener, forward

    def test_letters_reach_the_listener_and_the_status_turns_ok(self):
        link, listener, forward = self.pair()
        for _ in range(5):
            self.assertTrue(link.send("A"))
        self.assertTrue(wait_until(lambda: forward.letters.count("A") == 5))
        self.assertTrue(wait_until(lambda: link.state == "OK"))
        self.assertIn("OK", link.status_text())
        self.assertTrue(link.status_text().isascii())
        self.assertEqual(link.sent_count, 5)
        self.assertEqual(link.dropped, 0)

    def test_heartbeat_keeps_the_status_ok_without_forwarding_anything(self):
        link, listener, forward = self.pair()
        self.assertTrue(wait_until(lambda: link.state == "OK"))
        time.sleep(0.2)
        self.assertEqual(forward.letters, [])                       # 살아 있음 신호는 차로 안 넘어간다
        self.assertEqual(link.sent_count, 0)                        # 센 글자에도 안 들어간다

    def test_no_listener_turns_the_status_to_no_reply(self):
        free = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()
        with mock.patch.object(netlink, "HEARTBEAT_SECONDS", 0.05), mock.patch.object(netlink, "REPLY_TIMEOUT", 0.3):
            link = netlink.UdpLink("127.0.0.1", port, log=quiet)
            self.addCleanup(link.close)
            self.assertTrue(wait_until(lambda: link.state == "NO REPLY"))
        self.assertIn("NO REPLY", link.status_text())

    def test_closing_letters_are_sent_one_by_one_and_forwarded(self):
        """끌 때 글자가 여럿이어도(예: XZ) 한 글자씩 따로 가서 받는 쪽이 받는다. 멈춤 글자라 차로 넘어간다."""
        link, listener, forward = self.pair()
        link.close("XZ")
        self.assertTrue(wait_until(lambda: forward.letters == ["X", "Z"]))
        self.assertEqual(listener.ignored, 0)

    def test_a_send_failure_is_dropped_and_reported_once(self):
        messages = []
        listener = netlink.UdpListener(0, Collector(), log=quiet, host="127.0.0.1")
        self.addCleanup(listener.close)
        link = netlink.UdpLink("127.0.0.1", listener.port, log=messages.append)
        self.addCleanup(link.close)
        link._target = ("999.999.999.999", 1)       # 잘못된 주소로 보내면 OSError 가 난다(길이 없는 것과 같은 모양)
        self.assertFalse(link.send("A"))
        self.assertFalse(link.send("A"))
        self.assertEqual(link.dropped, 2)
        self.assertEqual(len([m for m in messages if "보내지 못했습니다" in m]), 1)

    def test_unknown_host_raises_so_the_caller_can_fall_back(self):
        with self.assertRaises(OSError):
            netlink.UdpLink("호스트.없음.invalid", 5005, log=quiet)


class PrintGateTest(unittest.TestCase):
    def test_two_players_letters_do_not_make_each_other_print(self):
        """P1 의 W 와 P2 의 A 가 번갈아 와도 줄이 계속 찍히지 않는다."""
        gate = netlink.PrintGate(gap=0.5)
        shown = []
        for i in range(10):
            shown.append(gate.should_print("W", i * 0.15))
            shown.append(gate.should_print("A", i * 0.15 + 0.07))
        self.assertEqual(shown, [True, True] + [False] * 18)


class WiringTest(Quiet):
    def test_p2_with_send_to_repeats_and_stops_the_left_right_axis_only(self):
        """11/20: P2 는 팔을 내리거나 끌 때 좌우만 끄는 Z 를 보낸다. P1 의 앞뒤 입력은 안 끊는다."""
        args = config.parse_args(["--role", "P2", "--send-to", "172.20.17.8"])
        plan = output.resolve_letters(args)
        self.assertEqual((plan.mode, plan.quit_letter), ("repeat", "Z"))
        self.assertEqual(plan.letters, {"LEFT_UP": "A", "RIGHT_UP": "D"})
        self.assertEqual(plan.stops, {"A": "Z", "D": "Z"})
        asked = config.parse_args(["--role", "P2", "--send-to", "172.20.17.8", "--letter-quit", ""])
        self.assertEqual(output.resolve_letters(asked).quit_letter, "")

    def test_port_and_send_to_cannot_be_combined(self):
        for bad in (["--port", "COM11", "--send-to", "172.20.17.8"], ["--send-to", "172.20.17.8", "--listen"]):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                config.parse_args(bad)

    def test_listen_and_allow_from_options(self):
        args = config.parse_args(["--role", "P1", "--listen", "--allow-from", "172.20.17.129, 10.0.0.5"])
        self.assertEqual((args.listen, args.allow_from), (5005, ["172.20.17.129", "10.0.0.5"]))
        self.assertIsNone(config.parse_args([]).listen)
        self.assertEqual(config.parse_args(["--listen", "6000"]).listen, 6000)

    def test_p2_make_output_uses_a_udp_link(self):
        out = output.make_output(config.parse_args(["--role", "P2", "--send-to", "127.0.0.1:5999"]))
        try:
            self.assertIsInstance(out.link, netlink.UdpLink)
            self.assertIn("UDP 127.0.0.1:5999", out.status_text(1.0))
            self.assertEqual(out.net_status_text(), "")
        finally:
            out.close()

    def test_bad_address_falls_back_to_a_fake_link(self):
        out = output.make_output(config.parse_args(["--role", "P2", "--send-to", "호스트.없음.invalid"]))
        self.assertIsInstance(out.link, output.FakeLink)
        self.assertIn("bad address", out.link.status_text())

    def test_p1_forwards_what_p2_sends_to_its_own_link(self):
        """P1 노트북: --listen 으로 받은 W A S D 가 자기 차 포트(여기서는 가짜 보내기)로 넘어간다. 자기 글자와 섞여도 서로 안 지운다."""
        out = output.make_output(config.parse_args(["--role", "P1", "--listen", "0"]))
        try:
            self.assertIsNotNone(out.net)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.addCleanup(sock.close)
            sock.sendto(b"A", ("127.0.0.1", out.net.port))
            self.assertTrue(wait_until(lambda: out.link.sent_count == 1))
            out.update({"ARMS": "ARMS_UP"}, 1.0)                    # P1 자기 글자 W
            self.assertEqual(out.link.sent_count, 2)
            self.assertIn("NET :", out.net_status_text())
        finally:
            out.close()

    def test_listen_port_in_use_does_not_crash(self):
        first = output.make_output(config.parse_args(["--role", "P1", "--listen", "0"]))
        try:
            busy = first.net.port
            second = output.make_output(config.parse_args(["--role", "P1", "--listen", str(busy)]))
            try:
                self.assertIsNone(second.net)
                self.assertIn("열지 못했습니다", __import__("sys").stdout.getvalue())
            finally:
                second.close()
        finally:
            first.close()


if __name__ == "__main__":
    unittest.main()
