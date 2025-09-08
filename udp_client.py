#!/usr/bin/env python3
"""
netlab UDP client: sends PING datagrams and measures PONG RTTs.
"""

import asyncio
import time
import click
import logging
from typing import Tuple

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("netlab.udp_client")

async def udp_ping(host: str, port: int, message: str, timeout: float = 3.0) -> float:
    loop = asyncio.get_running_loop()
    on_response = loop.create_future()
    start = time.perf_counter()

    class UDPClientProtocol(asyncio.DatagramProtocol):
        def connection_made(self, transport: asyncio.DatagramTransport):
            transport.sendto(message.encode(), (host, port))

        def datagram_received(self, data: bytes, addr: Tuple[str, int]):
            on_response.set_result(data.decode().strip())

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPClientProtocol(),
        remote_addr=(host, port)
    )
    try:
        response = await asyncio.wait_for(on_response, timeout)
        end = time.perf_counter()
        rtt = end - start

        if response != "PONG":
            logger.warning(f"Unexpected response: {response}")
            return float("nan")

        logger.info(f"Received {response} from {host}:{port} in {rtt:.4f}s")
        return rtt
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for PONG")
        return float("nan")
    finally:
        transport.close()


async def run_many(host: str, port: int, count: int, concurrency: int, message: str = "PING", timeout: float = 3.0, burst: bool = False):
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def worker(i: int):
        async with sem:
            rtt = await udp_ping(host, port, message, timeout)
            results.append(rtt)

    tasks = [asyncio.create_task(worker(i)) for i in range(count)]
    await asyncio.gather(*tasks)
    return results


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=5000, type=int, help="Server UDP port")
@click.option("--count", default=20, type=int, help="Number of PINGs to send")
@click.option("--concurrency", default=20, type=int, help="How many PINGs in flight at once")
@click.option("--message", default="PING", help="Message to send")
@click.option("--timeout", default=3.0, type=float, help="Timeout in seconds")
@click.option("--burst", is_flag=True, help="Send all requests at once (ignore concurrency)")
def main(host, port, count, concurrency, message, timeout, burst):
    """UDP PING client"""
    results = asyncio.run(run_many(host, port, count, concurrency, message, timeout, burst))

    clean = [r for r in results if not (r != r)]  # filter out NaN
    logger.info(f"Success: {len(clean)}/{len(results)}")

    if clean:
        avg = sum(clean) / len(clean)
        logger.info(f"RTT avg={avg:.4f}s min={min(clean):.4f}s max={max(clean):.4f}s")
    else:
        logger.warning("No successful responses")


if __name__ == "__main__":
    main()