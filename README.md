# netlab

Async TCP/UDP **PING–PONG server and clients** with a pytest suite.

## Features
- TCP server and UDP server, run individually or together
- TCP and UDP clients to send `PING` and measure RTT
- Configurable concurrency, count, and burst modes
- Pytest suite for automated testing

## Usage

### Start the server
```bash
# TCP only
python server.py -t

# UDP only
python server.py -u

# Both TCP and UDP
python server.py -t -u
```

### Run the TCP client
```bash
python tcp_client.py --count 10 --concurrency 5
```

### Run the UDP client
```bash
python udp_client.py --count 10 --concurrency 5
```

## Run tests
```bash
pytest -v
```