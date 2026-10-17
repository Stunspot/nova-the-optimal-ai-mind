# Locate the first broken boundary in the path

Model the path: endpoint power/radio/cable → link association → local interface → address configuration → gateway/local routing → DNS → transport → TLS/authentication → application/service. Test adjacent boundaries rather than declaring “the internet is down.”

## Distinguish nearby failures

- Link present does not establish IP configuration.
- An IP address does not establish gateway reachability.
- Gateway reachability does not establish DNS.
- DNS resolution does not establish transport, TLS, identity, or service health.
- One successful ping does not establish application quality; ICMP may differ from the affected path.

Compare affected and unaffected devices, networks, protocols, names versus literal addresses, wired versus wireless, and local versus external destinations. Record DHCP lease, address/subnet/gateway, DNS servers, signal/channel conditions, route, VPN/proxy state, firewall/policy, timestamps, loss, latency, and reproducibility only as relevant.

Before changing a client resolver, router forwarder, DHCP option, firmware, or shared network policy, capture the current value and the model/build authority that makes the change applicable. Prefer a time-bounded comparison with an explicit restore condition. Preserve the prior setting and configuration export when available; do not substitute a factory reset for a discriminating test.

For Wi-Fi, separate RF association and signal quality from IP and service layers. Consider interference, congestion, band steering, power saving, roaming, driver/firmware, access-point state, and upstream service without dumping every possibility. Change channel, band, adapter, AP, or location only as a controlled comparison.

For deeper architecture, load `../knowledge/network-architecture.md`. Preserve shared-fate dependencies such as DNS, identity, VPN, and cloud control planes. Use current vendor/provider status and primary documentation for volatile outages, configuration, and security behavior.
