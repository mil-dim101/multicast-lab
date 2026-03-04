#!/usr/bin/env python3
import argparse
import socket
import struct
import time
import os

def make_socket(ttl: int, iface_ip: str | None):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # TTL: 1 = stays on local subnet; >1 needed if routing multicast across VLANs/routers
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("b", ttl))

    # Optional: pick outbound interface by IP (recommended if host has multiple VLANs/NICs)
    if iface_ip:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(iface_ip))

    # Avoid fragmentation surprises (best effort; may not exist on all OS)
    #try:
    #            s.setsockopt(socket.IPPROTO_IP, socket.IP_MTU_DISCOVER, 2)  # IP_PMTUDISC_DO
    #except OSError:
    #            pass

    return s

def main():
    ap = argparse.ArgumentParser(description="UDP multicast publisher (market-data style).")
    ap.add_argument("--group", default="239.10.10.10", help="Multicast group IP")
    ap.add_argument("--port", type=int, default=5000, help="UDP destination port")
    ap.add_argument("--pps", type=int, default=50000, help="Packets per second to send")
    ap.add_argument("--size", type=int, default=256, help="Payload size bytes (including header)")
    ap.add_argument("--ttl", type=int, default=1, help="Multicast TTL (1=local subnet)")
    ap.add_argument("--iface", default=None, help="Outbound interface IP (e.g. 10.100.0.50)")
    ap.add_argument("--seconds", type=int, default=30, help="Duration to run")
    ap.add_argument("--symbol", default="LAB", help="Fake symbol tag")
    args = ap.parse_args()

    if args.size < 32:
                raise SystemExit("Payload --size must be >= 32")

    s = make_socket(args.ttl, args.iface)

    dest = (args.group, args.port)
    pid = os.getpid() & 0xFFFF

    # Simple binary header:
    #   uint32 seq
    #   uint64 send_time_ns
    #   uint16 pid
    #   8 bytes symbol (padded)
    # total 4+8+2+8 = 22 bytes; pad to 24 for alignment
    header_fmt = "!IQH8s2x"  # 24 bytes
    pad_len = args.size - struct.calcsize(header_fmt)
    pad = b"\x00" * pad_len

    seq = 0
    start = time.perf_counter()
    end = start + args.seconds

    interval = 1.0 / max(1, args.pps)
    next_send = start

    last_report = start
    sent_since = 0

    print(f"Publishing to {args.group}:{args.port}  pps={args.pps} size={args.size} ttl={args.ttl} iface={args.iface}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            now = time.perf_counter()
            if now >= end:
                    break

            # send as many packets as needed to catch up (handles minor scheduling jitter)
            while now >= next_send:
                send_ns = time.time_ns()
                sym = args.symbol.encode("ascii", "ignore")[:8].ljust(8, b"\x00")
                pkt = struct.pack(header_fmt, seq, send_ns, pid, sym) + pad
                s.sendto(pkt, dest)
                seq += 1
                sent_since += 1
                next_send += interval
                now = time.perf_counter()

            # small sleep to reduce CPU, still keeps high pps fairly stable
            time.sleep(min(0.0005, max(0.0, next_send - time.perf_counter())))

            if now - last_report >= 1.0:
                elapsed = now - last_report
                pps_actual = sent_since / elapsed
                mbps = (pps_actual * args.size * 8) / 1e6
                print(f"sent seq={seq-1}  ~{pps_actual:,.0f} pps  ~{mbps:,.2f} Mbps")
                last_report = now
                sent_since = 0

    except KeyboardInterrupt:
                pass
    finally:
                s.close()

if __name__ == "__main__":
        main()
