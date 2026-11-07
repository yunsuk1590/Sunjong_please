"""글자 보내기 자동 시험. 카메라와 차가 없어도 된다.

motion 폴더에서 실행한다.
  윈도우: .venv\\Scripts\\python.exe -m unittest test_output -v
  맥:     .venv/bin/python -m unittest test_output -v
"""

import contextlib
import importlib
import importlib.util
import io
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import config
import output
from stabilizer import make_stabilizer

STEP = 1 / 30   # 카메라 사진 한 장 간격(초)


class Stream:
    """실제 떨림 방지를 거쳐 글자를 고르는 흐름. 시간은 가짜로 흐른다."""

    def __init__(self, off_letter=""):
        self.stabilizer = make_stabilizer(config.parse_args([]))
        self.trigger = output.LetterTrigger("ARMS_UP", "F", off_letter)
        self.now = 0.0
        self.letters = []

    def run(self, seconds, arms_up=False, person=True, lean=None):
        for _ in range(round(seconds / STEP)):
            raw = {
                "ARMS_UP": SimpleNamespace(state="ARMS_UP" if arms_up else None),
                "LEAN": SimpleNamespace(state=lean),
            }
            stable = self.stabilizer.update(raw, person, self.now)
            letter = self.trigger.update(stable)
            if letter:
                self.letters.append(letter)
            self.now += STEP


class WhenToSend(unittest.TestCase):
    def test_arms_up_sends_one_letter_even_if_held(self):
        s = Stream()
        s.run(1.0)
        s.run(5.0, arms_up=True)
        self.assertEqual(s.letters, ["F"])

    def test_flicker_while_arms_up_still_sends_one_letter(self):
        s = Stream()
        s.run(1.0, arms_up=True)
        for _ in range(10):
            s.run(0.1, arms_up=False)    # 꺼짐 대기 0.35초보다 짧게 튐
            s.run(0.5, arms_up=True)
        self.assertEqual(s.letters, ["F"])

    def test_short_blip_sends_nothing(self):
        s = Stream()
        s.run(1.0)
        s.run(0.1, arms_up=True)         # 켜짐 대기 0.25초보다 짧게 튐
        s.run(1.0)
        self.assertEqual(s.letters, [])

    def test_lower_then_raise_sends_again(self):
        s = Stream()
        s.run(1.0, arms_up=True)
        s.run(1.0)
        s.run(1.0, arms_up=True)
        self.assertEqual(s.letters, ["F", "F"])

    def test_other_gesture_sends_nothing(self):
        s = Stream()
        s.run(2.0, lean="LEAN_LEFT")
        self.assertEqual(s.letters, [])

    def test_exception_arms_already_up_at_start(self):
        """예외 1: 프로그램을 켤 때 이미 팔을 들고 있으면 글자가 나간다."""
        s = Stream()
        s.run(1.0, arms_up=True)
        self.assertEqual(s.letters, ["F"])

    def test_exception_person_lost_long_sends_again(self):
        """예외 2: 팔을 든 채 사람을 0.5초 넘게 놓쳤다가 다시 잡으면 글자가 한 번 더 나간다."""
        s = Stream()
        s.run(1.0, arms_up=True)
        s.run(0.7, person=False)
        s.run(1.0, arms_up=True)
        self.assertEqual(s.letters, ["F", "F"])

    def test_person_lost_briefly_does_not_send_again(self):
        s = Stream()
        s.run(1.0, arms_up=True)
        s.run(0.3, person=False)
        s.run(1.0, arms_up=True)
        self.assertEqual(s.letters, ["F"])

    def test_off_letter_is_empty_by_default_and_can_be_set(self):
        s = Stream()
        s.run(1.0, arms_up=True)
        s.run(1.0)
        self.assertEqual(s.letters, ["F"])
        s = Stream(off_letter="S")
        s.run(1.0, arms_up=True)
        s.run(1.0)
        self.assertEqual(s.letters, ["F", "S"])


class FakePort:
    """가짜 포트. 일부러 끊어 볼 수 있다."""

    def __init__(self):
        self.written = []
        self.closed = False
        self.broken = False

    @property
    def in_waiting(self):
        if self.broken:
            raise OSError("가짜 끊김")
        return 0

    def read(self, size):
        return b""

    def write(self, data):
        if self.broken:
            raise OSError("가짜 끊김")
        self.written.append(data)
        return len(data)

    def close(self):
        self.closed = True


def wait_until(condition, seconds=3.0):
    limit = time.monotonic() + seconds
    while time.monotonic() < limit:
        if condition():
            return True
        time.sleep(0.005)
    return condition()


class Quiet(unittest.TestCase):
    """터미널 안내 글을 시험 결과와 섞지 않는다."""

    def setUp(self):
        patcher = mock.patch("sys.stdout", io.StringIO())
        patcher.start()
        self.addCleanup(patcher.stop)


class SerialLinkTest(Quiet):
    def make_link(self, opener):
        link = output.SerialLink("TEST", 9600, open_port=opener, retry_seconds=0.01)
        self.addCleanup(link.close)
        return link

    def test_sends_letter_when_open(self):
        port = FakePort()
        link = self.make_link(lambda p, b: port)
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        self.assertTrue(link.send("F"))
        self.assertTrue(wait_until(lambda: port.written == [b"F"]))
        self.assertEqual(link.sent_count, 1)

    def test_letter_before_open_is_dropped_and_never_sent_later(self):
        """고칠 점 1: 포트가 열리기 전의 글자는 버린다. 연결된 뒤에 갑자기 나가면 안 된다."""
        allow_open = threading.Event()
        port = FakePort()

        def slow_open(p, b):
            allow_open.wait(3)
            return port

        link = self.make_link(slow_open)
        self.assertEqual(link.state, "connecting")
        self.assertFalse(link.send("F"))
        self.assertEqual(link.dropped, 1)
        allow_open.set()
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        time.sleep(0.05)
        self.assertEqual(port.written, [])

    def test_open_failure_keeps_retrying_without_crash(self):
        """고칠 점 3: 포트가 안 열려도 꺼지지 않고 다시 시도한다."""
        port = FakePort()
        tries = []

        def flaky_open(p, b):
            tries.append(1)
            if len(tries) < 3:
                raise OSError("가짜: 포트 없음")
            return port

        link = self.make_link(flaky_open)
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        self.assertEqual(len(tries), 3)

    def test_write_failure_drops_letter_and_reconnects(self):
        """고칠 점 1·3: 보내다 끊기면 그 글자는 버리고, 다시 연결한다. 다시 연결돼도 그 글자는 안 나간다."""
        first, second = FakePort(), FakePort()
        ports = [first, second]
        link = self.make_link(lambda p, b: ports.pop(0))
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        first.broken = True
        link.send("F")
        self.assertTrue(wait_until(lambda: link.dropped == 1))
        self.assertTrue(wait_until(lambda: not ports and link.state == "OPEN"))
        self.assertTrue(first.closed)
        time.sleep(0.05)
        self.assertEqual(second.written, [])
        link.send("F")
        self.assertTrue(wait_until(lambda: second.written == [b"F"]))

    def test_idle_disconnect_is_noticed(self):
        """고칠 점 3: 보낼 글자가 없어도 끊긴 것을 알아채고 다시 연결한다."""
        first, second = FakePort(), FakePort()
        ports = [first, second]
        with mock.patch.object(output, "WATCH_SECONDS", 0.01):
            link = self.make_link(lambda p, b: ports.pop(0))
            self.assertTrue(wait_until(lambda: link.state == "OPEN"))
            first.broken = True
            self.assertTrue(wait_until(lambda: not ports and first.closed))

    def test_close_sends_final_letter_then_closes_port(self):
        port = FakePort()
        link = output.SerialLink("TEST", 9600, open_port=lambda p, b: port, retry_seconds=0.01)
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        link.close("S")
        self.assertEqual(port.written, [b"S"])
        self.assertTrue(port.closed)

    def test_close_does_not_wait_forever_for_stuck_port(self):
        """블루투스 포트가 오래 안 열려도 프로그램은 꺼진다."""
        release = threading.Event()
        port = FakePort()

        def stuck_open(p, b):
            release.wait(10)
            return port

        link = output.SerialLink("TEST", 9600, open_port=stuck_open, retry_seconds=0.01)
        started = time.monotonic()
        with mock.patch.object(output, "CLOSE_WAIT", 0.05):
            link.close("S")
        self.assertLess(time.monotonic() - started, 1.0)
        release.set()              # 작업 줄을 끝낸다. 늦게 열린 포트는 닫혀야 한다
        link._thread.join(1.0)
        self.assertTrue(port.closed)


class LetterOutputTest(Quiet):
    def test_no_port_is_fake_and_shows_on_screen(self):
        args = config.parse_args([])
        out = output.make_output(args)
        self.assertIsInstance(out.link, output.FakeLink)
        out.update({"ARMS_UP": "ARMS_UP", "LEAN": None}, 10.0)
        text = out.status_text(11.5)
        self.assertIn("no port", text)
        self.assertIn("sent 1", text)
        self.assertIn("last F 1.5s ago", text)
        out.close()
        self.assertIn("[가짜 보내기] F", sys.stdout.getvalue())
        self.assertIn("[가짜 보내기] S", sys.stdout.getvalue())

    def test_dropped_letter_is_shown_on_screen(self):
        link = mock.Mock()
        link.status_text.return_value = "OUTPUT TEST"
        link.sent_count, link.dropped = 0, 1
        link.send.return_value = False
        out = output.LetterOutput(link, output.LetterTrigger("ARMS_UP", "F"))
        out.update({"ARMS_UP": "ARMS_UP"}, 1.0)
        self.assertIn("last F dropped", out.status_text(2.0))

    def test_runs_without_pyserial(self):
        """고칠 점 2: pyserial 이 없는 컴퓨터에서도 불러올 수 있고, 포트를 적어도 꺼지지 않는다."""
        with mock.patch.dict(sys.modules, {"serial": None}):
            reloaded = importlib.reload(output)
            link = reloaded.make_link(config.parse_args(["--port", "COM5"]))
            self.assertIsInstance(link, reloaded.FakeLink)
            self.assertIn("no pyserial", link.status_text())
        importlib.reload(output)


class ConfigTest(Quiet):
    def test_defaults_match_decisions(self):
        args = config.parse_args([])
        self.assertEqual(
            (args.port, args.baud, args.send_on, args.letter_on, args.letter_off, args.letter_quit),
            ("", 9600, "ARMS_UP", "F", "", "S"),
        )

    def test_letter_must_be_one_character(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            config.parse_args(["--letter-on", "FF"])


@unittest.skipIf(importlib.util.find_spec("serial") is None, "pyserial 이 없어 가상 포트 시험을 건너뜀")
class VirtualPortTest(Quiet):
    """시험 3단계: 보낸 글자가 되돌아오는 가상 포트(loop://)에서 실제 pyserial 로 보내 본다."""

    def test_letter_comes_back_from_loop_port(self):
        opened = []

        def open_and_keep(port, baud):
            opened.append(output.open_serial(port, baud))
            return opened[-1]

        # 작업 줄이 돌아온 글자를 읽어서 버리지 않도록, 살아 있는지 보는 간격을 길게 둔다
        with mock.patch.object(output, "WATCH_SECONDS", 30):
            link = output.SerialLink("loop://", 9600, open_port=open_and_keep, retry_seconds=0.01)
            self.addCleanup(link.close)
            self.assertTrue(wait_until(lambda: link.state == "OPEN"))
            self.assertTrue(link.send("F"))
            self.assertTrue(wait_until(lambda: link.sent_count == 1))
            self.assertEqual(opened[0].read(1), b"F")


if __name__ == "__main__":
    unittest.main()
