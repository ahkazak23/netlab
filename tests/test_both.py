import asyncio
import math
from netlab.tcp_client import run_many as run_many_tcp  # absolute import
from netlab.udp_client import run_many as run_many_udp  # absolute import

def test_both_server(both_server):
    (tcp_host, tcp_port), (udp_host, udp_port) = both_server

    async def run_all():
        t_tcp = asyncio.create_task(run_many_tcp(tcp_host, tcp_port, count=5, concurrency=2))
        t_udp = asyncio.create_task(run_many_udp(udp_host, udp_port, count=5, concurrency=2))
        return await asyncio.gather(t_tcp, t_udp)

    tcp_res, udp_res = asyncio.run(run_all())

    tcp_clean = [r for r in tcp_res if not math.isnan(r)]
    udp_clean = [r for r in udp_res if not math.isnan(r)]

    assert len(tcp_clean) == 5
    assert len(udp_clean) == 5
    assert min(tcp_clean) >= 0.0
    assert min(udp_clean) >= 0.0