#!/usr/bin/env python3
"""Mininet SDN topology: primary s1-s2-s4, alternate s1-s3-s4."""
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.topo import Topo
from mininet.log import setLogLevel, info


class RecoveryTopo(Topo):
    def build(self):
        h1 = self.addHost("h1", ip="10.0.0.1/24", mac="00:00:00:00:00:01")
        h2 = self.addHost("h2", ip="10.0.0.2/24", mac="00:00:00:00:00:02")
        switches = {
            i: self.addSwitch("s%d" % i, dpid="%016x" % i, protocols="OpenFlow13")
            for i in range(1, 5)
        }
        # Link ordering fixes switch port numbers expected in controller.py.
        self.addLink(h1, switches[1])                 # s1-eth1
        self.addLink(switches[1], switches[2])       # s1-eth2 / s2-eth1
        self.addLink(switches[1], switches[3])       # s1-eth3 / s3-eth1
        self.addLink(switches[2], switches[4])       # s2-eth2 / s4-eth1
        self.addLink(switches[3], switches[4])       # s3-eth2 / s4-eth2
        self.addLink(switches[4], h2)                 # s4-eth3


def main():
    net = Mininet(topo=RecoveryTopo(), controller=None, switch=OVSSwitch,
                  link=TCLink, autoSetMacs=False)
    net.addController("c0", controller=RemoteController,
                      ip="127.0.0.1", port=6653)
    try:
        net.start()
        info("\nPrimary: h1-s1-s2-s4-h2; backup: h1-s1-s3-s4-h2\n")
        info("Run: h2 python3 udp_receiver.py &\n")
        info("Then: h1 python3 udp_sender.py\n")
        info("Failover: link s1 s2 down (restore with 'link s1 s2 up')\n")
        CLI(net)
    finally:
        net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    main()
