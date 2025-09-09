import asyncio
import math
from netlab.tcp_client import tcp_ping, run_many  # absolute import

def test_tcp_server_single(tcp_server):
    host, port = tcp_server
    rtt = asyncio.run(tcp_ping(host, port, "PING"))
    assert not math.isnan(rtt) and rtt >= 0.0

def test_tcp_server_many(tcp_server):
    host, port = tcp_server
    results = asyncio.run(run_many(host, port, count=10, concurrency=3))
    clean = [r for r in results if not math.isnan(r)]
    assert len(clean) == 10
    assert min(clean) >= 0.0