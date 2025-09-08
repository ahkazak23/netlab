#!/usr/bin/env python3
"""
netlab TCP client: sends PINGs to server and measures PONG responses.
"""
import asyncio
import time
import click
import logging

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("netlab.tcp_client")


async def tcp_ping(host: str, port: int, message: str, timeout: float = 3.0) -> float:
    start = time.perf_counter()
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(message.encode())
    await writer.drain()
    data = await reader.readline()
    end = time.perf_counter()
    response = data.decode().strip()
    if response != "PONG":
        logger.warning(f"Unexpected response: {response}")
        return float("nan")
    rtt = end - start
    logger.info(f"Received {response} from {host}:{port} in {rtt:.4f}s")
    writer.close()
    await writer.wait_closed()
    return rtt


async def run_many(host: str, port: int, count: int, concurrency: int, message: str = "PING", timeout: float = 3.0,
                   burst: bool = False):
    sem = asyncio.Semaphore(concurrency)
    results = []
    async def worker(i: int):
        async with sem:
            rtt = await tcp_ping(host, port, message, timeout)
            results.append(rtt)
    tasks = [asyncio.create_task(worker(i)) for i in range(count)]
    await asyncio.gather(*tasks)
    return results

@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=6000, type=int, help="Server port")
@click.option("--count", default=20, type=int, help="Number of PINGs to send")
@click.option("--concurrency", default=20, type=int, help="How many PINGs in flight at once")
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