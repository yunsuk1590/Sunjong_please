"""노트북 두 대 길 시험 도구(net_check.py)의 자동 시험. 같은 노트북 안(127.0.0.1)에서 돌리므로 와이파이가 없어도 된다.

motion 폴더에서 실행한다.
  윈도우: .venv\\Scripts\\python.exe -m unittest test_net_check -v
  맥:     .venv/bin/python -m unittest test_net_check -v

와이파이를 사이에 둔 실제 시험은 자동으로 할 수 없다. net_check.py 의 설명대로 두 노트북에서 직접 한다.
"""

import _thread
import socket
import threading
import unittest

import net_check


def quiet(*_):
    pass


class Listener:
    """시험용으로 받는 쪽을 따로 도는 작업 줄에서 켠다."""

    def __enter__(self):
        self.sock = net_check.make_listener(0, "127.0.0.1")   # 0 = 빈 포트를 알아서 고른다
        self.port = self.sock.getsockname()[1]
        self.stop = threading.Event()
        self.result = {}
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
        return self

    def _run(self):
        self.result["value"] = net_check.listen_loop(self.sock, self.stop, log=quiet)

    def __exit__(self, *exc):
        self.stop.set()
        self.thread.join(2)
        self.sock.close()


class SendAndListen(unittest.TestCase):
    def test_every_letter_is_answered_on_an_open_path(self):
        with Listener() as listener:
            result = net_check.send_test("127.0.0.1", listener.port, 1.0, 0.1, "A", log=quiet)
        stats, ignored = listener.result["value"]
        self.assertGreaterEqual(result["sent"], 9)
        self.assertEqual(result["answered"], result["sent"])
        self.assertEqual(stats["127.0.0.1"].count, result["sent"])
        self.assertEqual(ignored, 0)
        self.assertLess(result["rtt_max_ms"], 100)

    def test_gaps_are_close_to_the_interval(self):
        with Listener() as listener:
            net_check.send_test("127.0.0.1", listener.port, 1.0, 0.1, "D", log=quiet)
        source = listener.result["value"][0]["127.0.0.1"]
        self.assertAlmostEqual(source.average_gap, 0.1, delta=0.03)
        self.assertEqual(source.over_limit, 0)

    def test_letters_outside_the_allowed_set_are_dropped_and_not_answered(self):
        with Listener() as listener:
            raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            raw.settimeout(0.3)
            for bad in (b"Z", b"w", b"AB", b"", b"\r"):    # 소문자, 두 글자, 빈 것, 줄바꿈은 모두 버린다
                raw.sendto(bad, ("127.0.0.1", listener.port))
            with self.assertRaises(socket.timeout):
                raw.recvfrom(64)                              # 버린 것에는 답이 오지 않는다
            raw.sendto(b"X", ("127.0.0.1", listener.port))
            self.assertEqual(raw.recvfrom(64)[0], b"X")       # 허용된 글자에는 답이 온다
            raw.close()
        stats, ignored = listener.result["value"]
        self.assertEqual(ignored, 5)
        self.assertEqual(stats["127.0.0.1"].count, 1)

    def test_no_listener_gives_no_answers_and_does_not_crash(self):
        free = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
        free.close()                                         # 아무도 안 듣는 포트
        result = net_check.send_test("127.0.0.1", port, 0.6, 0.1, "A", log=quiet)
        self.assertEqual(result["answered"], 0)
        self.assertGreater(result["sent"], 0)

    def test_summaries_explain_the_result(self):
        lines = []
        net_check.print_send_summary(
            {"sent": 10, "answered": 10, "refused": 0, "errors": 0, "rtt_avg_ms": 5.0, "rtt_max_ms": 9.0},
            log=lambda *a: lines.append(" ".join(a)))
        self.assertIn("길이 열려 있습니다", "\n".join(lines))
        lines.clear()
        net_check.print_send_summary(
            {"sent": 10, "answered": 0, "refused": 0, "errors": 0, "rtt_avg_ms": 0.0, "rtt_max_ms": 0.0},
            log=lambda *a: lines.append(" ".join(a)))
        self.assertIn("답이 하나도 안 왔습니다", "\n".join(lines))
        self.assertIn("방화벽", "\n".join(lines))

    def test_source_stats_count_gaps_over_the_car_limit(self):
        s = net_check.SourceStats()
        for t in (0.0, 0.15, 0.30, 0.80, 0.95):              # 0.5초 쉬는 구간이 하나
            s.add("A", t)
        self.assertEqual(s.count, 5)
        self.assertEqual(s.over_limit, 1)
        self.assertAlmostEqual(s.max_gap, 0.5)

    def test_ctrl_c_still_leaves_the_results(self):
        """11/20: Ctrl+C 로 끌 때 오류가 나고 받은 결과가 안 나온 문제. 끄는 때가 언제든 결과가 남아야 한다."""
        for delay in (0.10, 0.17, 0.23, 0.31, 0.37):
            listener = net_check.make_listener(0, "127.0.0.1")
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sender.sendto(b"A", ("127.0.0.1", listener.getsockname()[1]))
                timer = threading.Timer(delay, _thread.interrupt_main)    # Ctrl+C 를 누른 것과 같다
                timer.start()
                stats, ignored = net_check.listen_until_interrupt(listener, log=quiet)
                timer.join()
                self.assertEqual(stats["127.0.0.1"].count, 1, delay)
                self.assertEqual(ignored, 0)
            finally:
                sender.close()
                listener.close()

    def test_local_addresses_has_no_loopback(self):
        self.assertTrue(all(not a.startswith("127.") for a in net_check.local_addresses()))


if __name__ == "__main__":
    unittest.main()
