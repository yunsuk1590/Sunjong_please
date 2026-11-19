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

    def __init__(self, off_letter="", letters=None, repeat=0.0):
        self.stabilizer = make_stabilizer(config.parse_args([]))
        self.trigger = output.LetterTrigger(letters or {"ARMS_UP": "F"}, off_letter, repeat)
        self.now = 0.0
        self.letters = []
        self.times = []    # 글자가 고른 시각

    def run(self, seconds, arms_up=False, person=True, lean=None, state=None):
        """state: 팔 동작 상태를 직접 정함(예: "T_POSE"). 안 적으면 arms_up 에 따라 ARMS_UP 또는 없음."""
        arms = state or ("ARMS_UP" if arms_up else None)
        for _ in range(round(seconds / STEP)):
            raw = {
                "ARMS": SimpleNamespace(state=arms),
                "LEAN": SimpleNamespace(state=lean),
            }
            stable = self.stabilizer.update(raw, person, self.now)
            letter = self.trigger.update(stable, self.now)
            if letter:
                self.letters.append(letter)
                self.times.append(self.now)
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


class Controller(unittest.TestCase):
    """11/19 협동 레이싱: 동작이 켜져 있는 동안 같은 글자를 반복해서 보내는 컨트롤러식."""

    P1 = {"ARMS_UP": "W", "T_POSE": "S"}
    P2 = {"LEFT_UP": "A", "RIGHT_UP": "D"}

    def test_holds_repeat_the_same_letter_at_the_interval(self):
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(1.0)
        s.run(2.0, arms_up=True)
        self.assertEqual(set(s.letters), {"W"})
        gaps = [b - a for a, b in zip(s.times, s.times[1:])]
        self.assertTrue(all(0.14 <= g <= 0.20 for g in gaps), gaps)
        self.assertGreaterEqual(len(s.letters), 10)

    def test_nothing_is_sent_after_the_arms_come_down(self):
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(1.0, arms_up=True)
        s.run(0.6)                          # 꺼짐 대기 0.35초가 지나면 보내지 않는다
        count = len(s.letters)
        s.run(2.0)
        self.assertEqual(len(s.letters), count)

    def test_stop_lag_is_the_off_wait_only(self):
        """팔을 내린 뒤 마지막 글자가 나가는 시간은 꺼짐 대기(0.35초) 안이다. 차는 그 뒤 약 0.3초 더 간다."""
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(1.0, arms_up=True)
        released_at = s.now
        s.run(1.0)
        self.assertLessEqual(s.times[-1] - released_at, 0.35 + STEP)

    def test_switching_gesture_sends_the_new_letter_at_once(self):
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(1.0, arms_up=True)
        s.run(1.0, state="T_POSE")
        self.assertEqual(s.letters[0], "W")
        self.assertEqual(s.letters[-1], "S")
        self.assertEqual(s.letters.index("S"), s.letters.count("W"))   # W 가 끝나면 바로 S, 섞이지 않음

    def test_p2_left_and_right(self):
        s = Stream(letters=self.P2, repeat=0.15)
        s.run(1.0, state="LEFT_UP")
        s.run(0.8)
        s.run(1.0, state="RIGHT_UP")
        self.assertEqual(s.letters[0], "A")
        self.assertEqual(s.letters[-1], "D")
        self.assertEqual(set(s.letters), {"A", "D"})

    def test_one_laptop_can_send_all_four_letters_one_at_a_time(self):
        """노트북 1대로 시험할 때: --letters 로 네 동작을 모두 켠다. 동작은 한 번에 하나만 켜진다."""
        s = Stream(letters={**self.P1, **self.P2}, repeat=0.15)
        for state in ("ARMS_UP", "T_POSE", "LEFT_UP", "RIGHT_UP"):
            s.run(1.0, state=state)
            s.run(1.0)
        order = [letter for i, letter in enumerate(s.letters) if i == 0 or letter != s.letters[i - 1]]
        self.assertEqual(order, ["W", "S", "A", "D"])
        for earlier, later in zip(s.times, s.times[1:]):
            self.assertGreaterEqual(later - earlier, 0.14)     # 두 글자가 같은 때에 겹쳐 나가지 않는다

    def test_gesture_of_the_other_role_sends_nothing(self):
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(2.0, state="LEFT_UP")
        self.assertEqual(s.letters, [])

    def test_once_mode_with_a_letter_table_sends_each_press_once(self):
        s = Stream(letters=self.P1, repeat=0.0)
        s.run(2.0, arms_up=True)
        s.run(1.0)
        s.run(2.0, state="T_POSE")
        self.assertEqual(s.letters, ["W", "S"])

    def test_a_stalled_camera_does_not_burst_letters(self):
        """사진이 1초 끊겼다 와도 밀린 글자를 한꺼번에 보내지 않는다."""
        trigger = output.LetterTrigger(self.P1, "", 0.15)
        sent = [trigger.update({"ARMS": "ARMS_UP"}, 0.0)]
        sent.append(trigger.update({"ARMS": "ARMS_UP"}, 1.0))
        sent.append(trigger.update({"ARMS": "ARMS_UP"}, 1.03))
        self.assertEqual(sent, ["W", "W", ""])

    def test_person_lost_stops_the_letters(self):
        s = Stream(letters=self.P1, repeat=0.15)
        s.run(1.0, arms_up=True)
        s.run(0.7, person=False)             # lost 0.5초 뒤 모든 동작이 꺼진다
        count = len(s.letters)
        s.run(1.0, person=False)
        self.assertEqual(len(s.letters), count)


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

    def test_letters_are_not_queued_only_the_newest_waits(self):
        """11/19: 반복해서 보낼 때도 쌓지 않는다. 포트가 막혀 있는 동안 온 글자는 가장 최근 하나만 남는다."""
        release = threading.Event()
        entered = threading.Event()

        class SlowPort(FakePort):
            def write(self, data):
                if not self.written:
                    entered.set()
                    release.wait(3)      # 첫 글자를 쓰는 동안 막힌다
                return super().write(data)

        port = SlowPort()
        link = self.make_link(lambda p, b: port)
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        link.send("W")
        self.assertTrue(entered.wait(2))
        for letter in "ASD":             # 막힌 동안 세 글자가 더 온다
            self.assertTrue(link.send(letter))
        release.set()
        self.assertTrue(wait_until(lambda: len(port.written) == 2))
        time.sleep(0.05)
        self.assertEqual(port.written, [b"W", b"D"])

    def test_repeated_letter_is_printed_once_and_write_time_is_measured(self):
        port = FakePort()
        link = self.make_link(lambda p, b: port)
        self.assertTrue(wait_until(lambda: link.state == "OPEN"))
        for _ in range(8):
            link.send("W")
            self.assertTrue(wait_until(lambda n=link.sent_count: link.sent_count > n))
        self.assertEqual(port.written, [b"W"] * 8)
        self.assertEqual(sys.stdout.getvalue().count("W 보냄"), 1)
        self.assertGreaterEqual(link.slowest_write_ms, 0.0)

    def test_dropped_letters_are_counted_but_printed_rarely(self):
        link = output.SerialLink("TEST", 9600, open_port=lambda p, b: time.sleep(5) or FakePort(), retry_seconds=0.01)
        self.addCleanup(link.close)
        for _ in range(10):
            self.assertFalse(link.send("W"))
        self.assertEqual(link.dropped, 10)
        self.assertEqual(sys.stdout.getvalue().count("보내지 못하고 버렸습니다"), 1)

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
        out = output.LetterOutput(link, output.LetterTrigger({"ARMS_UP": "F"}))
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
            (args.port, args.baud, args.send_on, args.letter_on, args.letter_off),
            ("", 9600, "ARMS_UP", "F", ""),
        )
        # 11/11 방식: 켜지는 순간 한 번, 끌 때 S
        self.assertEqual(output.resolve_letters(args), ({"ARMS_UP": "F"}, "once", "S", ""))

    def test_letter_must_be_one_character(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            config.parse_args(["--letter-on", "FF"])

    def test_role_p1_and_p2_defaults(self):
        p1 = output.resolve_letters(config.parse_args(["--role", "P1"]))
        self.assertEqual(p1, ({"ARMS_UP": "W", "T_POSE": "S"}, "repeat", "X", "P1 repeat W/S"))
        p2 = output.resolve_letters(config.parse_args(["--role", "P2"]))
        self.assertEqual(p2, ({"LEFT_UP": "A", "RIGHT_UP": "D"}, "repeat", "X", "P2 repeat A/D"))

    def test_role_never_sends_s_when_quitting_unless_asked(self):
        """새 약속에서 S 는 「뒤로」다. 끌 때 S 가 나가면 차가 뒤로 가므로 역할을 고르면 X 를 쓴다."""
        for role in ("P1", "P2"):
            self.assertNotEqual(output.resolve_letters(config.parse_args(["--role", role]))[2], "S")
        asked = output.resolve_letters(config.parse_args(["--role", "P1", "--letter-quit", "S"]))
        self.assertEqual(asked[2], "S")
        none = output.resolve_letters(config.parse_args(["--role", "P1", "--letter-quit", ""]))
        self.assertEqual(none[2], "")

    def test_send_mode_and_letters_options(self):
        once = output.resolve_letters(config.parse_args(["--role", "P2", "--send-mode", "once"]))
        self.assertEqual(once[1], "once")
        custom = output.resolve_letters(config.parse_args(["--role", "P1", "--letters", "ARMS_UP=w, t_pose=s"]))
        self.assertEqual(custom[0], {"ARMS_UP": "w", "T_POSE": "s"})
        self.assertEqual(custom[1], "repeat")
        table_only = output.resolve_letters(config.parse_args(["--letters", "LEFT_UP=A"]))
        self.assertEqual((table_only[1], table_only[2]), ("repeat", "X"))

    def test_bad_letters_and_interval_are_refused(self):
        for bad in (["--letters", "ARMS_UP=WW"], ["--letters", "JUMP=W"], ["--letters", "ARMS_UP"],
                    ["--repeat-seconds", "0"]):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                config.parse_args(bad)

    def test_make_output_uses_the_role(self):
        out = output.make_output(config.parse_args(["--role", "P1"]))
        self.assertEqual(out.trigger.repeat_seconds, 0.15)
        self.assertEqual(out.quit_letter, "X")
        out.update({"ARMS": "ARMS_UP"}, 1.0)
        self.assertIn("[P1 repeat W/S]", out.status_text(1.2))
        self.assertIn("last W", out.status_text(1.2))


class QuietPrinting(unittest.TestCase):
    def test_print_gate_prints_a_held_letter_once(self):
        gate = output.PrintGate(gap=0.5)
        shown = [gate.should_print("W", t * 0.15) for t in range(10)]
        self.assertEqual(shown, [True] + [False] * 9)

    def test_print_gate_prints_again_after_a_pause_or_a_new_letter(self):
        gate = output.PrintGate(gap=0.5)
        self.assertTrue(gate.should_print("W", 0.0))
        self.assertTrue(gate.should_print("S", 0.15))
        self.assertTrue(gate.should_print("S", 1.0))      # 한참 쉬었다 다시 누름
        self.assertFalse(gate.should_print("S", 1.15))


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
