#!/usr/bin/env python3
import socket, struct, sys, time

GROUP = sys.argv[1] if len(sys.argv) > 1 else "239.10.10.10"
PORT  = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
IFACE = sys.argv[3] if len(sys.argv) > 3 else "10.200.0.36"

print(f"GROUP={GROUP} PORT={PORT} IFACE={IFACE}")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind to port on all addresses (most portable for multicast recv)
s.bind(("", PORT))
print("bound OK")

# Try setting the interface explicitly (helps on some stacks)
try:
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(IFACE))
    print("set IP_MULTICAST_IF OK")
except OSError as e:
    print("set IP_MULTICAST_IF FAILED:", e)

g = socket.inet_aton(GROUP)
i = socket.inet_aton(IFACE)

# Try membership struct in two ways
ok = False
for name, mreq in [
    ("4s4s", struct.pack("4s4s", g, i)),
    ("group+iface", g + i),
]:
    try:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print("IP_ADD_MEMBERSHIP OK using", name)
        ok = True
        break
    except OSError as e:
        print("IP_ADD_MEMBERSHIP FAILED using", name, ":", e)

if not ok:
    print("Could not join group at all; exiting.")
    sys.exit(2)

# Receive loop
s.settimeout(2.0)
print("waiting for data...")
while True:
    try:
        data, addr = s.recvfrom(65535)
        print("RX", len(data), "bytes from", addr, "first8=", data[:8])
    except socket.timeout:
        print("...no data yet")
        time.sleep(0.2)
