"""
NetSage AI - Deterministic Network Rule Checker

This checker analyzes network evidence without using AI.

Checks:
- Duplicate IP conflicts
- Interface status
- VLAN assignment
- Trunk VLANs
- Gateway/subnet
- DHCP
- DNS
- Routing / OSPF
- ACL
- NAT
- Wireless
"""

import ipaddress
import re
from typing import Any, Dict, List


# ============================================================
# GENERAL HELPER
# ============================================================

def result(check, passed, message, evidence=None):
    """Create a standard checker result."""

    return {
        "check": check,
        "passed": passed,
        "message": message,
        "evidence": evidence or []
    }


# ============================================================
# DUPLICATE IP CHECK
# ============================================================

def check_duplicate_ips(text: str) -> Dict[str, Any]:
    """
    Detect duplicate IP configuration only when the evidence
    explicitly indicates an IP conflict.

    IMPORTANT:
    Seeing the same IP multiple times in show-command output
    does NOT automatically mean there is a duplicate IP.
    """

    duplicate_patterns = [
        r"duplicate\s+ip",
        r"ip\s+conflict",
        r"address\s+conflict",
        r"same\s+ip",
        r"two\s+(?:devices|hosts|clients).*same\s+ip",
        r"two\s+(?:devices|hosts|clients).*same\s+address",
    ]

    for pattern in duplicate_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return result(
                "duplicate_ip",
                False,
                "Evidence explicitly indicates a possible duplicate IP address.",
                [match.group(0)]
            )

    return result(
        "duplicate_ip",
        True,
        "No explicit duplicate IP conflict detected."
    )


# ============================================================
# INTERFACE STATUS CHECK
# ============================================================

def check_interface_status(text: str) -> Dict[str, Any]:
    """Look for obvious interface-down conditions."""

    lowered = text.lower()

    if "administratively down" in lowered:

        return result(
            "interface_status",
            False,
            "Interface is administratively down."
        )

    if re.search(r"\bdown/down\b", lowered):

        return result(
            "interface_status",
            False,
            "Interface appears to be down/down."
        )

    return result(
        "interface_status",
        True,
        "No explicit interface-down condition detected."
    )


# ============================================================
# VLAN CHECK
# ============================================================

def check_vlan(text: str) -> Dict[str, Any]:
    """
    Detect VLAN assignment mismatches.

    Example:

        PC1 connected to SW1 access port intended for VLAN 10.
        VLAN 10: Fa0/2
        VLAN 20: Fa0/1
        PC1 is connected to Fa0/1.
    """

    intended_match = re.search(
        r"(?:intended for|should be in|should use|required VLAN)"
        r"\s*(?:VLAN\s*)?(\d+)",
        text,
        re.IGNORECASE
    )

    connected_match = re.search(
        r"(?:PC1|PC|host)[^\n]*?"
        r"(?:connected to|using)\s+"
        r"(?:port\s*)?([A-Za-z]+\d+/\d+)",
        text,
        re.IGNORECASE
    )

    if not intended_match or not connected_match:

        return result(
            "vlan",
            True,
            "No clear VLAN assignment mismatch could be extracted."
        )

    intended_vlan = intended_match.group(1)

    connected_port = connected_match.group(1)

    vlan_match = re.search(
        rf"VLAN\s+(\d+)\s*:\s*{re.escape(connected_port)}",
        text,
        re.IGNORECASE
    )

    if vlan_match:

        actual_vlan = vlan_match.group(1)

        if actual_vlan != intended_vlan:

            return result(
                "vlan",
                False,
                f"Port {connected_port} is assigned to VLAN "
                f"{actual_vlan}, but VLAN {intended_vlan} is required.",
                [
                    f"Connected port: {connected_port}",
                    f"Actual VLAN: {actual_vlan}",
                    f"Required VLAN: {intended_vlan}"
                ]
            )

    return result(
        "vlan",
        True,
        "No VLAN assignment mismatch detected."
    )


# ============================================================
# TRUNK VLAN CHECK
# ============================================================

def check_trunk_vlan(text: str) -> Dict[str, Any]:
    """
    Detect a required VLAN that is missing from a trunk's
    allowed VLAN list.
    """

    required_match = re.search(
        r"(?:Required VLAN|required VLAN)\s*:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    allowed_match = re.search(
        r"(?:Allowed VLANs|allowed VLANs)\s*:\s*([0-9,\s]+)",
        text,
        re.IGNORECASE
    )

    if not required_match or not allowed_match:

        return result(
            "trunk_vlan",
            True,
            "No explicit trunk VLAN mismatch could be extracted."
        )

    required_vlan = required_match.group(1)

    allowed_vlans = re.findall(
        r"\d+",
        allowed_match.group(1)
    )

    if required_vlan not in allowed_vlans:

        return result(
            "trunk_vlan",
            False,
            f"Required VLAN {required_vlan} is not allowed on the trunk.",
            [
                f"Required VLAN: {required_vlan}",
                f"Allowed VLANs: {', '.join(allowed_vlans)}"
            ]
        )

    return result(
        "trunk_vlan",
        True,
        f"Required VLAN {required_vlan} is allowed on the trunk."
    )


# ============================================================
# GATEWAY / SUBNET CHECK
# ============================================================

def check_gateway_from_text(text: str) -> Dict[str, Any]:
    """
    Check whether the default gateway belongs to the
    host's subnet.
    """

    ip_match = re.search(
        r"(?:PC|Host)[^\n]*?(?:IP|address)\s*:\s*"
        r"(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?",
        text,
        re.IGNORECASE
    )

    gateway_match = re.search(
        r"(?:PC )?(?:gateway|default gateway)\s*:\s*"
        r"(\d+\.\d+\.\d+\.\d+)",
        text,
        re.IGNORECASE
    )

    if not ip_match or not gateway_match:

        return result(
            "gateway",
            True,
            "No structured IP/gateway information was found to check."
        )

    ip = ip_match.group(1)

    prefix = ip_match.group(2) or "24"

    gateway = gateway_match.group(1)

    try:

        network = ipaddress.ip_network(
            f"{ip}/{prefix}",
            strict=False
        )

        gateway_ip = ipaddress.ip_address(gateway)

        if gateway_ip not in network:

            return result(
                "gateway",
                False,
                "Gateway mismatch: gateway is outside the host's subnet.",
                [
                    f"Host IP: {ip}/{prefix}",
                    f"Gateway: {gateway}",
                    f"Host network: {network}"
                ]
            )

        return result(
            "gateway",
            True,
            "Gateway belongs to the host's subnet.",
            [
                f"Host IP: {ip}/{prefix}",
                f"Gateway: {gateway}"
            ]
        )

    except ValueError:

        return result(
            "gateway",
            False,
            "Invalid IP address or subnet information detected."
        )


# ============================================================
# DHCP CHECK
# ============================================================

def check_dhcp(text: str) -> Dict[str, Any]:
    """Detect common DHCP failures."""

    lowered = text.lower()

    if "no available" in lowered and "dhcp" in lowered:

        return result(
            "dhcp",
            False,
            "DHCP pool appears to have no available addresses."
        )

    if "apipa" in lowered or "169.254." in lowered:

        return result(
            "dhcp",
            False,
            "Client has an APIPA address, indicating DHCP address assignment failed."
        )

    if "bindings: none" in lowered:

        return result(
            "dhcp",
            False,
            "No DHCP binding was found for the affected client."
        )

    if "available: 0" in lowered:

        return result(
            "dhcp",
            False,
            "DHCP pool is exhausted."
        )

    return result(
        "dhcp",
        True,
        "No obvious DHCP failure detected."
    )


# ============================================================
# DNS CHECK
# ============================================================

def check_dns(text: str) -> Dict[str, Any]:
    """Detect common DNS failures."""

    lowered = text.lower()

    if "dns server timeout" in lowered:

        return result(
            "dns",
            False,
            "DNS server request is timing out."
        )

    if "nxdomain" in lowered:

        return result(
            "dns",
            False,
            "DNS returned NXDOMAIN for the requested name."
        )

    if "servfail" in lowered:

        return result(
            "dns",
            False,
            "DNS server returned SERVFAIL."
        )

    return result(
        "dns",
        True,
        "No obvious DNS failure detected."
    )


# ============================================================
# ROUTING CHECK
# ============================================================

def check_routing(text: str) -> Dict[str, Any]:
    """Detect missing routes and OSPF problems."""

    lowered = text.lower()

    if "route not present" in lowered:

        return result(
            "routing",
            False,
            "Required route is missing from the routing table."
        )

    if "not present" in lowered and "route" in lowered:

        return result(
            "routing",
            False,
            "Evidence indicates that a required route is missing."
        )

    if "no neighbors" in lowered and "ospf" in lowered:

        area_numbers = re.findall(
            r"area\s*:\s*(\d+)",
            lowered
        )

        if len(area_numbers) >= 2:

            if area_numbers[0] != area_numbers[1]:

                return result(
                    "routing",
                    False,
                    "OSPF neighbors are not forming because the configured areas differ.",
                    [
                        f"Detected OSPF areas: {area_numbers[0]} and {area_numbers[1]}"
                    ]
                )

        return result(
            "routing",
            False,
            "OSPF neighbor relationship is not established."
        )

    return result(
        "routing",
        True,
        "No obvious routing failure detected."
    )


# ============================================================
# ACL CHECK
# ============================================================

def check_acl(text: str) -> Dict[str, Any]:
    """Detect ACL rules explicitly denying traffic."""

    lowered = text.lower()

    if "acl" not in lowered and "access-list" not in lowered:

        return result(
            "acl",
            True,
            "No ACL evidence detected."
        )

    if "deny" in lowered:

        return result(
            "acl",
            False,
            "ACL evidence contains a deny rule that may block the required traffic."
        )

    return result(
        "acl",
        True,
        "No explicit ACL deny detected."
    )


# ============================================================
# NAT CHECK
# ============================================================

def check_nat(text: str) -> Dict[str, Any]:
    """Detect common NAT failures."""

    lowered = text.lower()

    if "no translations" in lowered:

        return result(
            "nat",
            False,
            "No NAT translations were found."
        )

    if "no static mapping" in lowered:

        return result(
            "nat",
            False,
            "Required static NAT/port-forwarding mapping is missing."
        )

    if "not translated" in lowered:

        return result(
            "nat",
            False,
            "Traffic from the affected subnet is not being translated."
        )

    return result(
        "nat",
        True,
        "No obvious NAT failure detected."
    )


# ============================================================
# WIRELESS CHECK
# ============================================================

def check_wireless(text: str) -> Dict[str, Any]:
    """Detect common wireless problems."""

    lowered = text.lower()

    if "wrong vlan" in lowered:

        return result(
            "wireless",
            False,
            "Wireless access port appears to be mapped to the wrong VLAN."
        )

    if "authentication failures" in lowered:

        return result(
            "wireless",
            False,
            "Wireless clients are experiencing authentication failures."
        )

    if (
        "guest" in lowered
        and "internal" in lowered
        and "permit ip any any" in lowered
    ):

        return result(
            "wireless",
            False,
            "Guest wireless traffic is explicitly permitted to internal networks."
        )

    return result(
        "wireless",
        True,
        "No obvious wireless failure detected."
    )


# ============================================================
# RUN ALL CHECKS
# ============================================================

def run_checks(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Run all deterministic checks against the case evidence.
    """

    text_parts = [
        str(case.get("symptom", "")),
        str(case.get("topology_note", "")),
        str(case.get("show_output", "")),
    ]

    text = "\n".join(text_parts)

    results = []

    results.append(check_duplicate_ips(text))
    results.append(check_interface_status(text))
    results.append(check_vlan(text))
    results.append(check_trunk_vlan(text))
    results.append(check_gateway_from_text(text))
    results.append(check_dhcp(text))
    results.append(check_dns(text))
    results.append(check_routing(text))
    results.append(check_acl(text))
    results.append(check_nat(text))
    results.append(check_wireless(text))

    return results


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_case = {
        "case_id": "1",

        "symptom":
            "PC cannot reach another device in the same VLAN",

        "topology_note":
            "PC1 connected to SW1 access port intended for VLAN 10.",

        "show_output":
            "show vlan brief\n"
            "VLAN 10: Fa0/2\n"
            "VLAN 20: Fa0/1\n"
            "PC1 is connected to Fa0/1."
    }

    print("\n======================================")
    print("       NETSAGE RULE CHECKER")
    print("======================================\n")

    results = run_checks(test_case)

    for item in results:

        status = "PASS" if item["passed"] else "FLAG"

        print(f"[{status}] {item['check']}")
        print(f"      {item['message']}")

        if item["evidence"]:
            print(
                f"      Evidence: {item['evidence']}"
            )

        print()