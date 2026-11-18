#!/usr/bin/env python3
"""OS-Ken OpenFlow 1.3 static primary/backup path controller.

Run: osken-manager --observe-links controller.py

This reconstruction uses OpenFlow port-status events plus OS-Ken link events.
Switch port numbers must match topology.py.
"""
import time
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology import event

COOKIE = 0xC0DE2026
ETH_TYPES = (0x0800, 0x0806)  # IPv4, ARP; avoid swallowing LLDP discovery
PRIMARY = {
    1: ((1, 2), (2, 1)),
    2: ((1, 2), (2, 1)),
    3: (),
    4: ((1, 3), (3, 1)),
}
BACKUP = {
    1: ((1, 3), (3, 1)),
    2: (),
    3: ((1, 2), (2, 1)),
    4: ((2, 3), (3, 2)),
}


class PacketLossRecovery(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapaths = {}
        self.backup_active = False

    def _install_rules(self, dp):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        dpid = dp.id
        # Delete only this app's previously installed flows.
        delete = parser.OFPFlowMod(
            datapath=dp, command=ofp.OFPFC_DELETE,
            cookie=COOKIE, cookie_mask=0xffffffffffffffff,
            table_id=ofp.OFPTT_ALL, out_port=ofp.OFPP_ANY,
            out_group=ofp.OFPG_ANY)
        dp.send_msg(delete)
        selected = BACKUP if self.backup_active else PRIMARY
        for in_port, out_port in selected.get(dpid, ()):
            for eth_type in ETH_TYPES:
                match = parser.OFPMatch(in_port=in_port, eth_type=eth_type)
                actions = [parser.OFPActionOutput(out_port)]
                instructions = [parser.OFPInstructionActions(
                    ofp.OFPIT_APPLY_ACTIONS, actions)]
                dp.send_msg(parser.OFPFlowMod(
                    datapath=dp, cookie=COOKIE, priority=100,
                    match=match, instructions=instructions))
        dp.send_msg(parser.OFPBarrierRequest(dp))

    def _set_backup(self, state, reason):
        if self.backup_active == state:
            return
        started = time.monotonic()
        self.backup_active = state
        for dp in self.datapaths.values():
            self._install_rules(dp)
        elapsed_ms = (time.monotonic() - started) * 1000
        self.logger.info("%s (%s); controller rule-send time %.3f ms",
                         "BACKUP" if state else "PRIMARY", reason, elapsed_ms)
        self.logger.info("Rule-send time is NOT end-to-end recovery latency")

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        self._install_rules(dp)
        self.logger.info("Configured s%s for %s path",
                         dp.id, "backup" if self.backup_active else "primary")

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status(self, ev):
        msg = ev.msg
        dp = msg.datapath
        port = msg.desc.port_no
        # Primary physical link is s1:2 <-> s2:1.
        if (dp.id, port) not in ((1, 2), (2, 1)):
            return
        ofp = dp.ofproto
        down = (msg.reason == ofp.OFPPR_DELETE or
                bool(msg.desc.state & ofp.OFPPS_LINK_DOWN))
        self._set_backup(down, "primary-link port status s%s:%s" % (dp.id, port))

    @set_ev_cls(event.EventLinkDelete)
    def link_deleted(self, ev):
        link = ev.link
        if {link.src.dpid, link.dst.dpid} == {1, 2}:
            self._set_backup(True, "link s1-s2 deleted")

    @set_ev_cls(event.EventLinkAdd)
    def link_added(self, ev):
        link = ev.link
        if {link.src.dpid, link.dst.dpid} == {1, 2}:
            self._set_backup(False, "link s1-s2 restored")
