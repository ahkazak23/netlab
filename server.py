#!/usr/bin/env python3
"""
netlab server: TCP/UDP PONG server.

CLI:
  python server.py -t        # TCP
  python server.py -u        # UDP
  python server.py -t -u     # both

If no flags are given, asks interactively.
"""
import asyncio
import logging
import click
from typing import Tuple

TCP_DEFAULT_HOST = "127.0.0.1"
TCP_DEFAULT_PORT = 6000
UDP_DEFAULT_HOST = "127.0.0.1"
UDP_DEFAULT_PORT = 5000

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("netlab.server")


async def handle_tcp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    # Client
    addr = writer.get_extra_info("peername")
    logger.info(f"TCP connection from {addr}")

    # Message
    data = await reader.read(1024)
    if not data:
        writer.close()
        await writer.wait_closed()
        return
    message = data.decode().strip()
    logger.info(f"Received from {addr}: {message}")

    # Response
    if message == "PING":
        writer.write(b"PONG\n")
        await writer.drain()
        logger.info(f"Sent PONG to {addr}")
    else:
        writer.write(b"ERR\n")
        await writer.drain()
        logger.info(f"Sent ERR to {addr}")

    # Close
    writer.close()
    await writer.wait_closed()


class PongUDP(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        message = data.decode().strip()
        logger.info(f"UDP datagram from {addr}: {message}")

        if message == "PING":
            self.transport.sendto(b"PONG", addr)
            logger.info(f"Sent PONG to {addr}")
        else:
            self.transport.sendto(b"ERR", addr)
            logger.info(f"Sent ERR to {addr}")

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        logger.info("UDP server ready")


async def run_tcp_server(host: str = TCP_DEFAULT_HOST, port: int = TCP_DEFAULT_PORT):
    server = await asyncio.start_server(handle_tcp, host, port)
    logger.info(f"TCP server listening on {host}:{port}")
    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        server.close()
        await server.wait_closed()
        raise


async def run_udp_server(host: str = UDP_DEFAULT_HOST, port: int = UDP_DEFAULT_PORT):
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: PongUDP(),
        local_addr=(host, port)
    )
    logger.info(f"UDP server listening on {host}:{port}")
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()
        await asyncio.sleep(0)


async def run_both():
    await asyncio.gather(
        run_tcp_server(),
        run_udp_server()
    )


@click.command()
@click.option("-t", "tcp", is_flag=True, help="Start TCP server")
@click.option("-u", "udp", is_flag=True, help="Start UDP server")
def main(tcp: bool, udp: bool):
    """TCP/UDP PONG server"""
    if not tcp and not udp:
        choice = input("TCP or UDP? (tcp/udp/both): ").strip().lower()
        if choice == "tcp":
            tcp = True
        elif choice == "udp":
            udp = True
        elif choice == "both":
            tcp, udp = True, True

    logger.info(f"Starting server(s): TCP={tcp}, UDP={udp}")

    if tcp and not udp:
        asyncio.run(run_tcp_server())
    elif udp and not tcp:
        asyncio.run(run_udp_server())
    elif tcp and udp:
        asyncio.run(run_both())


if __name__ == "__main__":
    main()