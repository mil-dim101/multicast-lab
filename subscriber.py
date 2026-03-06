#!/usr/bin/env python3
import argparse
import socket
import struct
import time
#v2 ilina

HEADER_FMT = "!IQH8s2x"  # 24 bytes
HEADER_SZ = struct.calcsize(HEADER_FMT)

def main():
    ap = argparse.ArgumentParser(description="UDP multicast subscriber with loss/rate stats.")
    ap.add_argument("--group", default="239.10.10.10", help="Multicast group IP")
    ap.add_argument("--port", type=int, default=5000, help="UDP port")
    ap.add_argument("--iface", default="0.0.0.0", help="Local interface IP to join on (0.0.0.0 = default)")
    ap.add_argument("--buf", type=int, default=4 * 1024 * 1024, help="SO_RCVBUF bytes")
    ap.add_argument("--report", type=float, default=1.0, help="Report interval seconds")
    args = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bigger receive buffer helps at high PPS
    try:
                                s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, args.buf)
    except OSError:
                                pass

    # Bind: on Linux, binding to ('', port) is common for multicast receive
    s.bind((args.group, args.port))

    # Join group
    mreq = socket.inet_aton(args.group) + socket.inet_aton("0.0.0.0")
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"Subscribed to {args.group}:{args.port} on iface={args.iface} (rcvbuf▒{args.buf} bytes)")
    print("Press Ctrl+C to stop.")

    last_seq = None
    recv = 0
    lost = 0
    bytes_recv = 0

    t0 = time.perf_counter()
    last_report = t0
    recv_since = 0
    bytes_since = 0
    lost_since = 0

    try:
       while True:
            data, addr = s.recvfrom(65535)
            now = time.perf_counter()

            if len(data) >= HEADER_SZ:
                seq, send_ns, pid, sym = struct.unpack_from(HEADER_FMT, data, 0)
                # Loss tracking using seq gaps
                if last_seq is not None and seq > last_seq + 1:
                    gap = (seq - last_seq - 1)
                    lost += gap
                    lost_since += gap
                last_seq = seq
            else:
                                                                # If packet too small, skip seq logic
                seq = None

            recv += 1
            recv_since += 1
            bytes_recv += len(data)
            bytes_since += len(data)

            if now - last_report >= args.report:
                dt = now - last_report
                pps = recv_since / dt
                mbps = (bytes_since * 8) / (dt * 1e6)
                loss_pct = (lost_since / max(1, (lost_since + recv_since))) * 100.0
                print(f"rx ~{pps:,.0f} pps  ~{mbps:,.2f} Mbps  lost+{lost_since} ({loss_pct:.3f}%)  total_rx={recv} total_lost={lost}")
                last_report = now
                recv_since = 0
                bytes_since = 0
                lost_since = 0

    except KeyboardInterrupt:
                                pass
    finally:
                                s.close()

if __name__ == "__main__":
                main()

