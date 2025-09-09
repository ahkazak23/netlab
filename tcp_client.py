#!/usr/bin/env python3
"""
netlab TCP client: sends PINGs to server and measures PONG responses.
"""
import asyncio
import time
import click
import logging
from typing import Optional

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("netlab.tcp_client")


async def tcp_ping(host: str, port: int, message: str, timeout: float = 3.0) -> float:
    """Open a TCP connection, send one message, expect 'PONG' line, return RTT (seconds) or NaN on failure."""
    start = time.perf_counter()
    writer: Optional[asyncio.StreamWriter] = None
    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.write((message + "\n").encode())
        await writer.drain()

        data = await asyncio.wait_for(reader.readline(), timeout)
        end = time.perf_counter()

        response = data.decode().strip()
        if response != "PONG":
            logger.warning(f"Unexpected response: {response}")
            return float("nan")

        rtt = end - start
        logger.info(f"Received {response} from {host}:{port} in {rtt:.4f}s")
        return rtt
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for PONG")
        return float("nan")
    except (ConnectionRefusedError, OSError) as e:
        logger.warning(f"Connection failed: {e}")
        return float("nan")
    finally:
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass


async def run_many(
    host: str,
    port: int,
    count: int,
    concurrency: int,
    message: str = "PING",
    timeout: float = 3.0,
    burst: bool = False,
) -> list[float]:
    """Send multiple TCP PINGs; return list of RTTs (NaN for failures)."""
    if count <= 0:
        return []
    concurrency = max(1, concurrency)

    results: list[float] = []

    async def worker(_: int):
        rtt = await tcp_ping(host, port, message, timeout)
        results.append(rtt)

    if burst:
        tasks = [asyncio.create_task(worker(i)) for i in range(count)]
    else:
        sem = asyncio.Semaphore(concurrency)

        async def limited_worker(i: int):
            async with sem:
                await worker(i)

        tasks = [asyncio.create_task(limited_worker(i)) for i in range(count)]

    await asyncio.gather(*tasks)
    return results


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=6000, type=int, help="Server port")
@click.option("--count", default=20, type=click.IntRange(min=0), help="Number of PINGs to send")
@click.option("--concurrency", default=20, type=click.IntRange(min=1), help="How many PINGs in flight at once")
@click.option("--message", default="PING", help="Message to send")
@click.option("--timeout", default=3.0, type=float, help="Timeout in seconds")
@click.option("--burst", is_flag=True, help="Send all requests at once (ignore concurrency)")
def main(host, port, count, concurrency, message, timeout, burst):
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
