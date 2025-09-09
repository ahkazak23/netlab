#!/usr/bin/env python3
"""
netlab UDP client: sends PING datagrams and measures PONG RTTs.
"""

import asyncio
import time
import click
import logging
from typing import Tuple, Optional

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("netlab.udp_client")


async def udp_ping(host: str, port: int, message: str, timeout: float = 3.0) -> float:
    """Send one UDP datagram, wait for 'PONG', return RTT (seconds) or NaN on failure."""
    loop = asyncio.get_running_loop()
    on_response: asyncio.Future[str] = loop.create_future()
    start = time.perf_counter()

    class UDPClientProtocol(asyncio.DatagramProtocol):
        transport: Optional[asyncio.DatagramTransport] = None

        def connection_made(self, transport: asyncio.DatagramTransport):
            self.transport = transport
            transport.sendto(message.encode())

        def datagram_received(self, data: bytes, addr: Tuple[str, int]):
            if not on_response.done():
                on_response.set_result(data.decode().strip())

        def error_received(self, exc: Exception):
            if not on_response.done():
                on_response.set_exception(exc)

    try:
        transport, _ = await loop.create_datagram_endpoint(
            lambda: UDPClientProtocol(),
            remote_addr=(host, port),
        )
    except OSError as e:
        logger.warning(f"UDP socket error: {e}")
        return float("nan")

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
    except Exception as e:
        logger.warning(f"UDP receive error: {e}")
        return float("nan")
    finally:
        transport.close()


async def run_many(
    host: str,
    port: int,
    count: int,
    concurrency: int,
    message: str = "PING",
    timeout: float = 3.0,
    burst: bool = False,
) -> list[float]:
    """Send multiple UDP PINGs; return list of RTTs (NaN for failures)."""
    if count <= 0:
        return []
    concurrency = max(1, concurrency)

    results: list[float] = []

    async def worker(_: int):
        rtt = await udp_ping(host, port, message, timeout)
        results.append(rtt)

    if burst:
        # fire all at once
        tasks = [asyncio.create_task(worker(i)) for i in range(count)]
    else:
        # throttle with a semaphore
        sem = asyncio.Semaphore(concurrency)

        async def limited_worker(i: int):
            async with sem:
                await worker(i)

        tasks = [asyncio.create_task(limited_worker(i)) for i in range(count)]

    await asyncio.gather(*tasks)
    return results


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=5000, type=int, help="Server UDP port")
@click.option("--count", default=20, type=click.IntRange(min=0), help="Number of PINGs to send")
@click.option("--concurrency", default=20, type=click.IntRange(min=1), help="How many PINGs in flight at once")
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
