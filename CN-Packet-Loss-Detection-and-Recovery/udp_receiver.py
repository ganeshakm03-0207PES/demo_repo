#!/usr/bin/env python3
"""Receive numbered UDP DATA packets, ACK each, count unique and recovered."""
import argparse
import socket
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="10.0.0.2")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--idle", type=float, default=10.0,
                   help="Timeout before DONE, or idle grace period after DONE")
    args = p.parse_args()
    seen = set()
    first_time = 0
    recovered = 0
    duplicates = 0
    done = False
    end_at = None
    started = time.monotonic()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.host, args.port))
        sock.settimeout(0.5)
        print("Listening on %s:%s" % (args.host, args.port), flush=True)
        while True:
            now = time.monotonic()
            if end_at is not None and now > end_at:
                break
            if end_at is None and now - started > 60:
                print("Timed out waiting for sender.")
                break
            try:
                data, peer = sock.recvfrom(2048)
            except socket.timeout:
                continue
            parts = data.decode(errors="replace").strip().split("|")
            if len(parts) == 2 and parts[0] == "DONE":
                done = True
                end_at = time.monotonic() + min(args.idle, 2.0)
                continue
            if len(parts) != 3 or parts[0] != "DATA" or not parts[1].isdigit():
                continue
            seq = int(parts[1])
            if not (1 <= seq <= args.count) or parts[2] not in ("O", "R"):
                continue
            if seq in seen:
                duplicates += 1
            else:
                seen.add(seq)
                if parts[2] == "R":
                    recovered += 1
                else:
                    first_time += 1
            sock.sendto(("ACK|%d" % seq).encode(), peer)
            if done:
                end_at = time.monotonic() + min(args.idle, 2.0)
    missing = sorted(set(range(1, args.count + 1)) - seen)
    print("Unique received: %d/%d" % (len(seen), args.count))
    print("First-transmission packets: %d | Recovered via retry: %d"
          % (first_time, recovered))
    print("Duplicate copies: %d | Final missing: %s" % (duplicates, missing))
    print("Final loss: %.2f%%" % (100.0 * len(missing) / args.count))


if __name__ == "__main__":
    main()
