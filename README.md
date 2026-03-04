# Multicast Networking Lab (Python)

Small lab to experiment with UDP multicast and network debugging.

Includes:

- Multicast publisher
- Multicast subscriber
- Minimal multicast receiver

Useful for learning:

- UDP multicast
- IGMP
- VLAN behavior
- Firewall debugging
- Python socket programming

## Example

Run publisher:

```bash
python3 publisher.py --group 239.10.10.10 --port 5000 --pps 20000



python3 subscriber.py --group 239.10.10.10 --port 5000


---


Example:

**examples/run_publisher.sh**

```bash
#!/bin/bash

python3 ../publisher.py \
  --group 239.10.10.10 \
  --port 5000 \
  --pps 20000 \
  --size 256 \
  --ttl 1
