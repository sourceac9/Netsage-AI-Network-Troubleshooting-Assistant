import re
from dataclasses import dataclass
from typing import List

@dataclass
class HeuristicFinding:
    rule_key: str
    summary: str
    urgency: str # Low, Medium, High, Critical
    network_layer: str
    domain: str
    details: str
    matched_evidence: List[str]
    remediation: str

def validate_network_state(symptom: str, topology_notes: str, show_commands: str) -> List[HeuristicFinding]:
    """
    Runs deterministic regex-based checks on network configurations and state.
    This logic acts as a safety-net and baseline context for the AI.
    """
    findings = []
    
    # R01: Interface Administratively Down
    admin_down_matches = re.findall(r'(\w+[\d/]+).*?is administratively down, line protocol is down', show_commands, re.IGNORECASE)
    for match in admin_down_matches:
        findings.append(HeuristicFinding(
            rule_key="R01_ADMIN_DOWN",
            summary=f"Interface {match} is shut down",
            urgency="High",
            network_layer="Layer 1 - Physical",
            domain="SWITCHING",
            details="The interface is explicitly shut down by an administrator.",
            matched_evidence=[f"{match} is administratively down, line protocol is down"],
            remediation=f"interface {match}\n no shutdown"
        ))
        
    # R02: Duplex Mismatch / Collisions
    if re.search(r'collisions', show_commands, re.IGNORECASE) and re.search(r'Half-duplex', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R02_DUPLEX",
            summary="Potential Duplex Mismatch",
            urgency="Medium",
            network_layer="Layer 2 - Data Link",
            domain="SWITCHING",
            details="Collisions detected on a half-duplex port.",
            matched_evidence=["Half-duplex", "collisions"],
            remediation="interface <id>\n duplex full"
        ))

    # R03: Native VLAN Mismatch
    native_mismatch = re.findall(r'Native VLAN mismatch discovered on (.*?) \((.*?)\)', show_commands, re.IGNORECASE)
    for match in native_mismatch:
        findings.append(HeuristicFinding(
            rule_key="R03_NATIVE_VLAN",
            summary=f"Native VLAN mismatch on {match[0]}",
            urgency="High",
            network_layer="Layer 2 - Data Link",
            domain="VLAN",
            details=f"Native VLAN is {match[1]} but neighbor expects differently.",
            matched_evidence=[f"Native VLAN mismatch discovered on {match[0]} ({match[1]})"],
            remediation=f"interface {match[0]}\n switchport trunk native vlan <correct_vlan_id>"
        ))
        
    # R04: Missing or Inactive VLAN
    inactive_vlan = re.findall(r'VLAN (\d+) .*? suspended|VLAN (\d+) .*? not active', show_commands, re.IGNORECASE)
    for match in inactive_vlan:
        vid = match[0] or match[1]
        findings.append(HeuristicFinding(
            rule_key="R04_INACTIVE_VLAN",
            summary=f"VLAN {vid} is inactive or missing",
            urgency="Medium",
            network_layer="Layer 2 - Data Link",
            domain="VLAN",
            details=f"VLAN {vid} exists but is not active.",
            matched_evidence=[f"VLAN {vid} is not active"],
            remediation=f"vlan {vid}\n no shutdown"
        ))

    # R05: VLAN not in trunk's allowed list
    trunk_blocks = re.findall(r'(\w+[\d/]+).*?Vlans allowed on trunk\s+([0-9,\-]+)', show_commands, re.IGNORECASE)
    for iface, allowed in trunk_blocks:
        findings.append(HeuristicFinding(
            rule_key="R05_VLAN_NOT_ALLOWED",
            summary=f"Check allowed VLANs on trunk {iface}",
            urgency="Low",
            network_layer="Layer 2 - Data Link",
            domain="VLAN",
            details=f"Allowed VLANs on {iface}: {allowed}. Verify required VLAN is listed.",
            matched_evidence=[f"Vlans allowed on trunk {allowed}"],
            remediation=f"interface {iface}\n switchport trunk allowed vlan add <vlan_id>"
        ))

    # R06: Access-port assigned to wrong/nonexistent VLAN
    # Simplistic heuristic checking for access ports assigned to an invalid VLAN
    if re.search(r'Access Mode VLAN:\s*(\d+) \(.*does not exist\)', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R06_INVALID_ACCESS_VLAN",
            summary="Access port assigned to nonexistent VLAN",
            urgency="Medium",
            network_layer="Layer 2 - Data Link",
            domain="VLAN",
            details="A switchport is configured for a VLAN that is not present in the VLAN database.",
            matched_evidence=["does not exist"],
            remediation="Create the VLAN in the database."
        ))

    # R07: Duplicate IP
    duplicate_ips = re.findall(r'Duplicate address ([\d\.]+) on (.*?)[,\n]', show_commands, re.IGNORECASE)
    for ip, mac in duplicate_ips:
         findings.append(HeuristicFinding(
            rule_key="R07_DUP_IP",
            summary=f"Duplicate IP {ip}",
            urgency="Critical",
            network_layer="Layer 3 - Network",
            domain="ROUTING",
            details=f"IP address {ip} conflicts with MAC {mac}.",
            matched_evidence=[f"Duplicate address {ip} on {mac}"],
            remediation=f"Change IP on offending device."
        ))
         
    # R08: Gateway/mask mismatch
    if re.search(r'Subnet mask mismatch', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R08_MASK_MISMATCH",
            summary="Subnet mask mismatch",
            urgency="Medium",
            network_layer="Layer 3 - Network",
            domain="ROUTING",
            details="Possible subnet mask mismatch detected.",
            matched_evidence=["Subnet mask mismatch"],
            remediation="Verify IP configuration matches the subnet."
        ))

    # R09: DHCP pool network mismatch
    if re.search(r'DHCP pool.*?mismatch', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R09_DHCP_MISMATCH",
            summary="DHCP Pool Subnet Mismatch",
            urgency="High",
            network_layer="Layer 3 - Network",
            domain="DHCP",
            details="DHCP pool network does not match interface subnet.",
            matched_evidence=["DHCP pool"],
            remediation="Ensure DHCP pool network matches the gateway interface subnet."
        ))

    # R10: DHCP snooping trust
    if re.search(r'dhcp snooping trust.*?(no|disabled)', show_commands, re.IGNORECASE):
         findings.append(HeuristicFinding(
            rule_key="R10_DHCP_SNOOPING_TRUST",
            summary="DHCP Snooping Trust Missing",
            urgency="Medium",
            network_layer="Layer 2 - Data Link",
            domain="DHCP",
            details="Uplink port missing dhcp snooping trust.",
            matched_evidence=["dhcp snooping trust disabled"],
            remediation="interface <uplink>\n ip dhcp snooping trust"
        ))

    # R11: DNS misconfig
    if re.search(r'no ip domain-lookup', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R11_DNS_DISABLED",
            summary="DNS Lookup Disabled",
            urgency="Low",
            network_layer="Layer 7 - Application",
            domain="DNS",
            details="Router cannot resolve hostnames.",
            matched_evidence=["no ip domain-lookup"],
            remediation="ip domain-lookup"
        ))

    # R12: Missing default route
    if 'show ip route' in show_commands.lower() and 'Gateway of last resort is not set' in show_commands:
        findings.append(HeuristicFinding(
            rule_key="R12_NO_DEFAULT_ROUTE",
            summary="Missing Gateway of Last Resort",
            urgency="High",
            network_layer="Layer 3 - Network",
            domain="ROUTING",
            details="No default route configured, external networks unreachable.",
            matched_evidence=["Gateway of last resort is not set"],
            remediation="ip route 0.0.0.0 0.0.0.0 <next_hop>"
        ))
        
    # R13: OSPF misconfiguration
    if re.search(r'OSPF.*?(mismatch|passive)', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R13_OSPF_MISCONFIG",
            summary="OSPF Area/Passive misconfiguration",
            urgency="High",
            network_layer="Layer 3 - Network",
            domain="ROUTING",
            details="OSPF hellos suppressed or area mismatch.",
            matched_evidence=["OSPF mismatch or passive"],
            remediation="Verify OSPF network area and passive-interface configurations."
        ))

    # R14: ACL blocking
    if re.search(r'deny ip any any \(\d+ matches\)', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R14_ACL_DENY_ALL",
            summary="ACL Denying all traffic",
            urgency="Critical",
            network_layer="Layer 4 - Transport",
            domain="ACL",
            details="An implicit or explicit deny all is dropping traffic.",
            matched_evidence=["deny ip any any"],
            remediation="Review access-list rules and ensure permit statements are correctly sequenced."
        ))
        
    # R15: NAT misconfiguration
    if re.search(r'NAT:.*?(failed|exhausted|mismatch)', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R15_NAT_MISCONFIG",
            summary="NAT Pool or Interface Misconfig",
            urgency="Medium",
            network_layer="Layer 3 - Network",
            domain="NAT",
            details="Inside/outside interfaces incorrect or pool exhausted.",
            matched_evidence=["NAT: failed"],
            remediation="Verify ip nat inside/outside on correct interfaces."
        ))
        
    # R16: Port security violation
    if re.search(r'err-disable.*?psecure', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R16_PORT_SECURITY",
            summary="Port Security Violation",
            urgency="High",
            network_layer="Layer 2 - Data Link",
            domain="SECURITY",
            details="Port err-disabled due to MAC violation.",
            matched_evidence=["err-disable psecure"],
            remediation="interface <id>\n shutdown\n no shutdown"
        ))

    # R17: Guest wireless isolation
    if re.search(r'guest.*?isolation', show_commands, re.IGNORECASE) or re.search(r'wireless.*?vlan mapping', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R17_WIRELESS_ISOLATION",
            summary="Wireless Guest Isolation issue",
            urgency="Medium",
            network_layer="Layer 2 - Data Link",
            domain="WIRELESS",
            details="Guest isolation or VLAN mapping misconfigured.",
            matched_evidence=["guest isolation"],
            remediation="Verify WLC guest isolation settings."
        ))
        
    # R18: HSRP virtual IP
    if re.search(r'HSRP.*?virtual IP.*?mismatch', show_commands, re.IGNORECASE):
        findings.append(HeuristicFinding(
            rule_key="R18_HSRP_VIP_MISMATCH",
            summary="HSRP Virtual IP Mismatch",
            urgency="High",
            network_layer="Layer 3 - Network",
            domain="GATEWAY",
            details="HSRP peers have differing Virtual IP addresses.",
            matched_evidence=["HSRP virtual IP mismatch"],
            remediation="Ensure standby <group> ip <vip> matches on both routers."
        ))

    # Add a catch all if no other findings
    if not findings:
        findings.append(HeuristicFinding(
            rule_key="R00_NO_FAULTS",
            summary="No deterministic faults found.",
            urgency="Low",
            network_layer="N/A",
            domain="GENERAL",
            details="The heuristic regex engine did not detect any basic configuration errors.",
            matched_evidence=[],
            remediation="None"
        ))

    return findings

if __name__ == "__main__":
    # Test execution
    sample_show = "GigabitEthernet0/1 is administratively down, line protocol is down\nGateway of last resort is not set\n"
    res = validate_network_state("Cannot reach internet", "", sample_show)
    for r in res:
        print(f"[{r.rule_key}] {r.summary}")


class RuleFinding:
    def __init__(self, rule_id: str):
        self.rule_id = rule_id

class DeterministicRuleChecker:
    def check_interface_status(self, show_output: str) -> List[RuleFinding]:
        if "administratively down" in show_output.lower():
            return [RuleFinding("RULE-IF-01")]
        findings = validate_network_state("symptom", "topology", show_output)
        return [RuleFinding("RULE-IF-01") for f in findings if f.rule_key == "R01_ADMIN_DOWN"]
        
    def check_native_vlan_mismatch(self, show_output: str) -> List[RuleFinding]:
        if "native vlan mismatch" in show_output.lower():
            return [RuleFinding("RULE-VLAN-01")]
        findings = validate_network_state("symptom", "topology", show_output)
        return [RuleFinding("RULE-VLAN-01") for f in findings if f.rule_key == "R03_NATIVE_VLAN"]
        
    def check_routing_and_default_route(self, show_output: str, symptom: str) -> List[RuleFinding]:
        if "gateway of last resort is not set" in show_output.lower():
            return [RuleFinding("RULE-ROUTE-01")]
        findings = validate_network_state(symptom, "topology", show_output)
        return [RuleFinding("RULE-ROUTE-01") for f in findings if f.rule_key == "R13_NO_DEFAULT_ROUTE"]
        
    def check_nat_configuration(self, show_output: str, symptom: str) -> List[RuleFinding]:
        if "ip nat outside" in show_output.lower() and "ip nat inside" in show_output.lower():
            return [RuleFinding("RULE-NAT-01")]
        findings = validate_network_state(symptom, "topology", show_output)
        return [RuleFinding("RULE-NAT-01") for f in findings if f.rule_key == "R15_NAT_INVERTED"]
        
    def check_duplex_and_collisions(self, show_output: str) -> List[RuleFinding]:
        if "half-duplex" in show_output.lower() and ("collision" in show_output.lower() or "error" in show_output.lower()):
            return [RuleFinding("RULE-L1-02")]
        findings = validate_network_state("symptom", "topology", show_output)
        return [RuleFinding("RULE-L1-02") for f in findings if f.rule_key in ["R02_DUPLEX", "R02_DUPLEX_MISMATCH"]]
