from typing import List

LEX = {
    "ospf": [2328],
    "arp": [826],
    "tcp": [9293],
    "bgp": [4271],
    "ipv4": [791, 1812],
    "ipv6": [8200],
}


def get_target_rfcs(q: str) -> List[int]:
    ql = q.lower()
    for k, v in LEX.items():
        if k in ql:
            return v
    return []
