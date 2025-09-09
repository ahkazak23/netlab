import asyncio
import math
from netlab.udp_client import udp_ping, run_many  # absolute import

def test_udp_server_single(udp_server):
    host, port = udp_server
    rtt = asyncio.run(udp_ping(host, port, "PING"))
    assert not math.isnan(rtt) and rtt >= 0.0

def test_udp_server_many(udp_server):
    host, port = udp_server
    results = asyncio.run(run_many(host, port, count=10, concurrency=5))
    clean = [r for r in results if not math.isnan(r)]
    assert len(clean) == 10
    assert min(clean) >= 0.0