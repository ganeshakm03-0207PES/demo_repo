# SDN Packet Loss Detection and Recovery (CN Mini Project)

**Status:** Reconstructed source based on the documented project design. The original Python source files were not available when this GitHub copy was created. Syntax and controller/Mininet runtime behavior still need verification in the intended Ubuntu/Mininet environment; do not attribute earlier experiment numbers to this reconstructed source without rerunning.

## Project overview

- **Mininet:** 2 hosts (h1, h2), 4 Open vSwitch switches (s1–s4)
- **Primary:** h1 → s1 → s2 → s4 → h2
- **Backup:** h1 → s1 → s3 → s4 → h2
- **Protocol:** OpenFlow 1.3, controlled using **OS-Ken**, not Ryu
- **UDP:** numbered DATA packets, ACK messages, up to five retry rounds
- **IP:** h1 = 10.0.0.1, h2 = 10.0.0.2, UDP port 5000

## Files

| File | Purpose |
|---|---|
| `topology.py` | Creates the Mininet topology |
| `controller.py` | OS-Ken controller with primary and backup path rules |
| `udp_sender.py` | Sends 100 packets and retransmits missing ACKs |
| `udp_receiver.py` | Receives packets, acknowledges them, and reports statistics |

## Setup and run (Ubuntu/Linux)

Install Mininet, Open vSwitch and an OS-Ken version compatible with your Python environment. Start from the directory containing the files.

**Terminal 1:**

```bash
osken-manager --observe-links controller.py
```

**Terminal 2:**

```bash
sudo mn -c
sudo python3 topology.py
```

**Inside the `mininet>` prompt:**

```bash
pingall
h2 python3 udp_receiver.py &
h1 python3 udp_sender.py
```

To simulate a primary link outage:

```bash
link s1 s2 down
pingall
sh ovs-ofctl -O OpenFlow13 dump-flows s1
sh ovs-ofctl -O OpenFlow13 dump-flows s3
link s1 s2 up
```

Inject and remove loss on the primary route:

```bash
sh tc qdisc replace dev s1-eth2 root netem loss 20%
h1 ping -c 50 10.0.0.2
sh tc qdisc del dev s1-eth2 root
```

Run the receiver again for each UDP test; it exits after receiving DONE from the sender (or after a timeout).

## Previously documented observations

These measurements came from prior project-report screenshots, **not** from executing this reconstructed version:

- Normal case: 100 of 100 unique UDP packets received
- With configured 20% link impairment: 41/50 ICMP replies (18% observed packet loss)
- UDP retries: 124 total transmissions, including 24 retries; 100/100 acknowledged
- Link-down connectivity: 50/50 ICMP replies via alternate path
- Controller-reported rule-send/programming time: 3.323 ms. **Not** an end-to-end recovery-time measurement.

## Verification still required

- Check `osken-manager` compatibility and `--observe-links` discovery in your VM.
- Validate switch-port assignments and flow tables against the topology.
- Repeat baseline, netem loss, UDP retransmission, and s1–s2 failure tests.
- Measure true application interruption separately from controller rule-programming time.

Do not treat these files as an exact transcription of the original lab source.
