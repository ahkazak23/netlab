# tests/conftest.py
import asyncio
import socket
import threading
import time
import contextlib
import pytest

# Prefer absolute import; ensure netlab/__init__.py and netlab/tests/__init__.py exist
from netlab.server import run_tcp_server, run_udp_server

HOST = "127.0.0.1"


def _free_port(family=socket.AF_INET, type_=socket.SOCK_STREAM) -> int:
    with contextlib.closing(socket.socket(family, type_)) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


class LoopThread(threading.Thread):
    """Background asyncio loop so we can run servers while tests run in the main thread."""
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self._ready = threading.Event()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()

    def start_and_wait(self):
        self.start()
        self._ready.wait()

    def create_task(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join(timeout=2)


@pytest.fixture(scope="session")
def loop_thread():
    th = LoopThread()
    th.start_and_wait()
    yield th
    th.stop()


@pytest.fixture
def tcp_server(loop_thread):
    port = _free_port()
    fut = loop_thread.create_task(run_tcp_server(HOST, port))
    # allow server to bind/accept
    time.sleep(0.25)
    yield HOST, port
    fut.cancel()
    try:
        fut.result(timeout=2)
    except Exception:
        pass
    time.sleep(0.05)


@pytest.fixture
def udp_server(loop_thread):
    port = _free_port(type_=socket.SOCK_DGRAM)
    fut = loop_thread.create_task(run_udp_server(HOST, port))
    time.sleep(0.25)
    yield HOST, port
    fut.cancel()
    try:
        fut.result(timeout=2)
    except Exception:
        pass
    time.sleep(0.05)


@pytest.fixture
def both_server(loop_thread):
    port_tcp = _free_port()
    port_udp = _free_port(type_=socket.SOCK_DGRAM)
    fut_tcp = loop_thread.create_task(run_tcp_server(HOST, port_tcp))
    fut_udp = loop_thread.create_task(run_udp_server(HOST, port_udp))
    time.sleep(0.3)
    yield (HOST, port_tcp), (HOST, port_udp)
    for fut in (fut_tcp, fut_udp):
        fut.cancel()
        try:
            fut.result(timeout=2)
        except Exception:
            pass
    time.sleep(0.05)