#!/usr/bin/env python3
"""Send 100 numbered UDP packets; retry unacknowledged packets (max 5 rounds)."""
import argparse
import socket
import time


def collect_acks(sock, acknowledged, deadline):
    while time.monotonic() < deadline:
        sock.settimeout(max(0.01, deadline - time.monotonic()))
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            break
        parts = data.decode(errors="replace").strip().split("|")
        if len(parts) == 2 and parts[0] == "ACK" and parts[1].isdigit():
            acknowledged.add(int(parts[1]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="10.0.0.2")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--wait", type=float, default=0.8)
    args = p.parse_args()
    destination = (args.host, args.port)
    acknowledged = set()
    total_sent = 0
    start = time.monotonic()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", 0))
        for seq in range(1, args.count + 1):
            sock.sendto(("DATA|%d|O" % seq).encode(), destination)
            total_sent += 1
            time.sleep(0.002)
        collect_acks(sock, acknowledged, time.monotonic() + args.wait)
        for round_no in range(1, args.rounds + 1):
            missing = sorted(set(range(1, args.count + 1)) - acknowledged)
            if not missing:
                break
            print("Retry round %d: %d unacknowledged" % (round_no, len(missing)))
            for seq in missing:
                sock.sendto(("DATA|%d|R" % seq).encode(), destination)
                total_sent += 1
                time.sleep(0.002)
            collect_acks(sock, acknowledged, time.monotonic() + args.wait)
        for _ in range(3):
            sock.sendto(("DONE|%d" % args.count).encode(), destination)
            time.sleep(0.1)
    print("Originals: %d | Total transmissions: %d | Retransmissions: %d"
          % (args.count, total_sent, total_sent - args.count))
    print("Acknowledged: %d/%d | Still missing: %s"
          % (len(acknowledged), args.count,
             sorted(set(range(1, args.count + 1)) - acknowledged)))
    print("Elapsed: %.3f s" % (time.monotonic() - start))


if __name__ == "__main__":
    main()
