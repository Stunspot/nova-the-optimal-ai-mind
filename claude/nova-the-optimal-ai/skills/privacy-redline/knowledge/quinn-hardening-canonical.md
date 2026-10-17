# **Quinn Airlock Knowledge Base \- Digital Hardening as Boundary Engineering**

## **Orientation: Hardening as Boundary Engineering**

Digital hardening is the systematic engineering of boundaries. It is the process of reducing the state space of a computing system to a minimum viable set of authorized flows. Systems security is not an accumulation of features. It is the elimination of unconstrained behavior. A system that appears secure but lacks verifiable constraints is in a failed state. Policy statements without technical enforcement are hallucinations. Hardened configuration is the only reality that persists against an adversary.

Boundary engineering requires a vertical understanding of the stack. Trust is established at the hardware level and must be extended through the firmware, the kernel, the operating system, and the application layer. Each layer must verify the integrity of the layer below it. Failure-state design is a first-class requirement. When a control breaks, the system must fail into a closed or safe state. The ultimate goal of hardening is to produce evidence-based security. An operator must be able to prove, at any moment, that the system’s configuration matches the security intent. This knowledge base defines the intent, specifies the enforcement, and dictates the evidence required to confirm success.

## **Threat-Context Adapter: Mapping Context to Topology**

Threat context determines the placement and thickness of digital boundaries. Hardening decisions must reflect the specific proximity of the adversary and the sensitivity of the assets.

### **Asset Class and Boundary Requirements**

| Asset Class | Adversary Proximity | Data Sensitivity | Recovery Tolerance | Required Boundary Profile |
| :---- | :---- | :---- | :---- | :---- |
| **Tier 0: Identity/Core** | Internal/Lateral | Critical (Keys/Hashes) | Low | Air-gapped or Hardware-Enforced Isolation. |
| **Tier 1: High-Assurance Workstation** | Remote/Physical | High (Intellectual Property) | Moderate | Measured Boot, VBS/HVCI, Full Egress Whitelisting. |
| **Tier 2: Mobile/Field Device** | Proximity/Radio | Moderate (Comms) | High | Baseband Isolation, Memory Tagging, Remote Attestation. |
| **Tier 3: General Utility** | Remote | Low | High | Standard CIS Baseline, Default-Deny Firewall. |

Operationalizing this context requires identifying hostile network exposure. A device used in a travel or hotel environment faces higher proximity risks than one in a controlled office.1 Administrative paths must be minimized to reduce the attack surface. Every administrative action must be time-bound and revocable. Supply chain assumptions are treated as potential vulnerabilities. Procurement requires provenance checks to ensure hardware has not been tampered with before deployment.3

## **System Design Workflow: The Practitioner Loop**

Hardening is a recursive lifecycle. It begins with asset identification and ends with continuous drift monitoring.

1. **Define Assets:** Enumerate every hardware component, service, and data object.  
2. **Establish Trust Zones:** Group assets based on shared sensitivity and functional requirements.  
3. **Engineers Boundaries:** Define the walls between zones (Virtualization, Firewalls, MAC).  
4. **Map Allowed Flows:** Document every legitimate interaction. Assume all other flows are prohibited.  
5. **Apply Enforcement:** Configure the controls (WDAC, AppArmor, nftables) to block unauthorized flows.  
6. **Extract Evidence:** Generate logs, hashes, and status reports to prove the state matches the intent.  
7. **Monitor for Drift:** Continuously compare current state to the baseline. Detect unauthorized changes.  
8. **Re-Baseline:** Update the baseline after authorized maintenance or system updates.4

## **Endpoint Hardening Playbook: Windows Platform Family**

Windows hardening requires dismantling legacy compatibility and enforcing hardware-backed boundaries. The structural security model relies on Virtualization-Based Security (VBS) and Hypervisor-Protected Code Integrity (HVCI).

### **Firmware and Boot Trust Establishment**

The hardware root of trust is the anchor for all subsequent layers. Secure Boot and the Trusted Platform Module (TPM) ensure the bootloader and kernel are untampered.5

* **Intent:** Prevent pre-boot and boot-time rootkits. Ensure only signed code executes.  
* **Enforcement:** Enable UEFI Secure Boot. Initialize and own TPM 2.0. Configure the platform to use the Microsoft Vulnerable Driver Blocklist.6  
* **Evidence:** Execute Confirm-SecureBootUEFI in PowerShell. Must return True. Run get-tpm. TpmReady must be True. Verify msinfo32.exe reports "Secure Boot State: On".7

### **OS Baseline Configuration**

The OS must isolate the kernel from user-mode processes and untrusted drivers. VBS uses the hardware hypervisor to create a secure memory enclave.

| Setting | Enforcement Mechanism (PowerShell/GPO) | Intent | Evidence (Registry/Command) |
| :---- | :---- | :---- | :---- |
| **Memory Integrity (HVCI)** | Enable-VBS \-MemoryIntegrity | Prevent driver-level kernel injection. | Get-CimInstance \-ClassName Win32\_DeviceGuard. SecurityServicesRunning includes 2\. |
| **Credential Guard** | Enable-VBS \-CredentialGuard | Protect Lsass secrets from memory dumping. | msinfo32.exe reports "Credential Guard: Running".8 |
| **WDAC** | Set-CIPolicy | Ensure only authorized binaries execute. | Event Viewer: Applications and Services Logs \> Microsoft \> Windows \> CodeIntegrity. |

### **Surface Minimization: Services and Protocols**

Disable protocols that facilitate lateral movement and reconnaissance.7

* **SMB v1.0:** Disable-WindowsOptionalFeature \-Online \-FeatureName SMB1Protocol. **Evidence:** Get-SmbServerConfiguration. EnableSMB1Protocol is False.  
* **NetBIOS over TCP/IP:** Set TcpipNetbiosOptions to 2 on all interfaces.7 **Evidence:** wmic nicconfig get tcpipnetbiosoptions. Output is 2\.  
* **LLMNR:** Set EnableMulticast to 0 in HKLM\\Software\\Policies\\Microsoft\\Windows NT\\DNSClient. **Evidence:** reg query returns 0\.  
* **PowerShell v2.0:** Disable-WindowsOptionalFeature \-Online \-FeatureName MicrosoftWindowsPowerShellV2Root. **Evidence:** Get-WindowsOptionalFeature shows state as Disabled.

### **Privilege Segmentation and Application Surface**

Remove permanent administrative rights. Use AppLocker or WDAC to restrict execution to specific directories.9

* **Intent:** Prevent unauthorized binary execution and privilege escalation.  
* **Enforcement:** Set User Account Control (UAC) to "Always Notify" and "Require credentials on the secure desktop." Implement AppLocker "Allow" rules for C:\\Windows and C:\\Program Files. Block all other paths.7  
* **Evidence:** Attempt execution from C:\\Users\\Public\\Downloads. System must deny access. Check AppLocker Event ID 8004\.9

## **Endpoint Hardening Playbook: macOS Platform Family**

macOS hardening centers on Apple silicon’s integration with System Integrity Protection (SIP) and the Secure Enclave Processor (SEP).11

### **Firmware and Hardware Trust**

Hardware-level security is enforced by the Boot ROM and SEP.

* **Intent:** Ensure immutable root of trust. Protect biometric data and encryption keys.11  
* **Enforcement:** Set "Full Security" in Startup Security Utility. Enable FileVault 2 Full Disk Encryption.12  
* **Evidence:** csrutil status must report enabled. fdesetup status must report FileVault is On.

### **OS and Kernel Hardening**

SIP prevents the modification of system-protected files and folders, even by the root user.

* **Intent:** Contain the impact of a root-level compromise.  
* **Enforcement:** Use the macOS Security Compliance Project (mSCP) to apply the 800-53 high-assurance baseline.13  
* **Evidence:** Run the compliance script: sudo./build/cis\_lvl1\_ODVs/cis\_lvl1\_ODVs\_compliance.sh. Review the output for failed checks.15

### **Peripheral and Radio Discipline**

Mobile macOS devices require strict control over radio interfaces and accessory connections.17

* **Intent:** Prevent DMA-based attacks over Thunderbolt and proximity-based attacks over Bluetooth.12  
* **Enforcement:** Enable "Accessory Security" to require approval for new USB/Thunderbolt devices. Disable "AirPlay Receiver" and "Screen Sharing".12  
* **Evidence:** system\_profiler SPBluetoothDataType. system\_profiler SPThunderboltDataType.

### **Advanced Protection: Lockdown Mode**

Lockdown Mode is a extreme hardening state for high-threat environments.17

* **Mechanism:** Disables Just-In-Time (JIT) compilation in Safari. Blocks most message attachments. Disables profile installation.  
* **Enforcement:** Enable via Settings \> Privacy & Security \> Lockdown Mode.  
* **Evidence:** Verify "Lockdown Mode" is active in system settings. Attempt to visit a site requiring complex JIT; Safari must block it.18

## **Endpoint Hardening Playbook: Linux Platform Family**

Linux hardening is a configuration-heavy exercise in kernel tuning and Mandatory Access Control (MAC).

### **Kernel Self-Protection**

The kernel must be configured to deny runtime modifications and restrict memory access.

* **Intent:** Neutralize kernel-level exploits.  
* **Enforcement:** Set kernel.modules\_disabled \= 1 via sysctl post-boot to prevent the loading of malicious modules.19  
* **Evidence:** sysctl kernel.modules\_disabled. Output is 1\.

### **Sysctl Hardening Parameters**

| Parameter | Recommended Value | Intent |
| :---- | :---- | :---- |
| kernel.randomize\_va\_space | 2 | Full ASLR for processes and shared libraries.20 |
| net.ipv4.conf.all.accept\_redirects | 0 | Prevent ICMP redirect-based traffic hijacking.21 |
| net.ipv4.tcp\_syncookies | 1 | Mitigate SYN flood DoS attacks.21 |
| fs.protected\_hardlinks | 1 | Prevent hardlink-based unauthorized file access.21 |
| kernel.yama.ptrace\_scope | 2 | Restrict ptrace to the root user only.19 |

### **Mandatory Access Control (MAC)**

AppArmor and SELinux enforce policy-based restrictions on every process.

* **Intent:** Contain the blast radius of compromised applications.23  
* **Enforcement:** Set SELinux to Enforcing mode or AppArmor to Enforced. Apply profiles to all network-facing services (SSH, Web, Mail).23  
* **Evidence:** sestatus. aa-status. All critical services must be in enforce mode.23

## **Endpoint Hardening Playbook: Mobile (GrapheneOS and iOS)**

Mobile security is boundary engineering for devices with high physical risk and radio exposure.

### **GrapheneOS (Android)**

GrapheneOS provides the most robust mobile hardening framework via attack surface reduction and memory safety.

* **Hardened Malloc:** Uses out-of-line metadata and guard pages to prevent heap corruption exploits.24  
* **Hardware Port Control:** Disables data lines on the USB-C port when the device is locked.25  
* **Enforcement:** Use the Auditor app for hardware-based remote attestation.25  
* **Evidence:** Auditor app returns a "Green" status signed by the hardware's secure element.

### **iOS 18 (Apple)**

iOS 18 introduces granular control over app-level permissions and system-level hardening.27

* **Lock Apps:** Secure individual apps with FaceID. **Enforcement:** Long-press app \> "Require Face ID".28  
* **Bluetooth Privacy:** Limit app access to Bluetooth connections.28  
* **Verification:** Use "Safety Check" to review and revoke data sharing permissions.18

## **Compartmentalization: Qubes OS and Kicksecure**

Compartmentalization is the ultimate boundary engineering strategy. It assumes the underlying OS is vulnerable and isolates tasks into separate domains.29

### **Qubes OS Architecture**

Qubes uses the Xen hypervisor to create isolated "qubes" for different trust domains.29

* **Dom0:** The administrative domain. It has no network access.29  
* **Service Qubes:** sys-net and sys-firewall handle the network stack. A compromise in sys-net is contained and cannot reach the "Work" or "Vault" qubes.29  
* **Disposable VMs:** Use for risky activities. They self-destruct upon closing the window.29  
* **Enforcement:** Assign all USB controllers to sys-usb. Assign network hardware to sys-net.  
* **Evidence:** Run qvm-ls. Confirm that sensitive qubes (e.g., Vault) have NetVM set to None.

### **Kicksecure Hardening**

Kicksecure is a hardened Linux base that can be used standalone or as a Qubes template.33

* **SUID Disabler:** Removes SUID bits from binaries to prevent privilege escalation.3  
* **systemcheck:** A diagnostic tool that verifies the hardening state of the OS.34  
* **Enforcement:** Run systemcheck after every update or configuration change.  
* **Evidence:** systemcheck output reports no security warnings or configuration errors.33

## **Network Isolation and Segmentation Architectures**

Network security is not a perimeter. It is a series of internal boundaries defined by Zero Trust principles.1

### **NIST SP 800-207 Zero Trust Tenets**

1. Treat all data sources and computing services as resources.1  
2. Secure all communications regardless of network location.36  
3. Grant access to individual resources on a per-session basis.35  
4. Determine access by dynamic policy including identity, device posture, and behavior.1

### **Micro-segmentation and Blast Radius**

Segmentation prevents lateral movement after an initial breach.2

* **Physical vs. Logical:** Prefer physical isolation for Tier 0 assets. Use VLANs and VRFs for Tier 1 and Tier 2\.35  
* **Egress Restriction:** Egress is a primary control. Block all outbound traffic by default. Allow only specific destinations (IP/FQDN) required for function.22  
* **Verification:** Use tcpdump to monitor for "Rejected" egress attempts. Run nft list ruleset to confirm policy drop on all chains.39

### **Resolver Control and DNS Integrity**

DNS is a critical control point and metadata leak vector.22

* **Intent:** Prevent DNS hijacking and leakage of browsing metadata.  
* **Enforcement:** Use DNS over HTTPS (DoH) or DNS over TLS (DoT). Hardcode resolvers to trusted, non-logging providers.  
* **Evidence:** Use dig or nslookup to verify queries are being answered by the intended encrypted resolver.

## **Default-Deny Control Logic Across Layers**

Default-deny is the implementation of the "implicit denial" principle. If a flow is not explicitly allowed, it is blocked.

### **Firewall and Network Policy**

* **Host Firewalls:** Every endpoint must run a firewall in default-deny mode. **Evidence:** netsh advfirewall show allprofiles (Windows) or nft list ruleset (Linux).38  
* **Cloud Security Groups:** Apply default-deny rules at the infrastructure level.

### **Application Allowlisting and Capabilities**

* **Executable Control:** Block all binary execution from user-mode writable paths.7  
* **Capabilities (Linux):** Use setcap to grant only specific privileges to processes rather than full root access.

### **Identity and Privilege Boundaries**

* **Just-In-Time (JIT) Access:** Grant administrative privileges only for the duration of the task.1  
* **Separate Roles:** Use separate accounts for administrative tasks and daily work. Never browse the web or open email with a privileged account.12

## **Cryptographic Operations and Secrets Handling**

Secrets are dynamic objects. Their lifecycle must be governed by hardware-backed roots of trust and automated rotation.

### **Secrets Lifecycle Management**

| Phase | Standard / Mechanism | Intent |
| :---- | :---- | :---- |
| **Generation** | TPM 2.0 / Hardware RNG | Ensure high entropy and non-predictability.41 |
| **Storage** | Secure Enclave / TPM NVRAM | Prevent extraction of private keys.11 |
| **Use** | Audience Binding / Scoping | Prevent secret reuse across different services.1 |
| **Rotation** | Automated / Trigger-based | Limit the validity window of compromised secrets.43 |
| **Revocation** | OCSP / CRL | Immediately invalidate compromised certificates.44 |

### **TPM 2.0 and Measured Boot**

Measured boot records the state of the system in Platform Configuration Registers (PCRs).45

* **PCR 0-7:** Firmware, UEFI settings, Secure Boot state.46  
* **PCR 8-15:** Kernel command line, initrd, bootloader configuration.46  
* **Enforcement:** Seal disk encryption keys to a specific PCR state (e.g., PCR 0, 7, 11). If any component is changed, the TPM will not unseal the key.41  
* **Evidence:** tpm2\_pcrread. The output must match the known-good hash baseline for the device.

### **Null Seeds and Reset Integrity**

The Linux kernel uses the TPM's **null seed** to derive keys that are unique to the current boot session.41

* **Mechanism:** The null seed changes every time the TPM is reset.  
* **Intent:** Ensure that trust established in one session cannot be replayed after a reset or reboot.41  
* **Verification:** Compare the kernel's null\_name (found in /sys/class/tpm/tpm0/null\_name) with a userspace-reconstructed hash. A mismatch indicates an interposer or TPM compromise.41

## **Secure Communications and Metadata Minimization**

Communication security requires isolating the channel and minimizing the metadata signature.47

### **Channel Selection and Metadata**

* **WireGuard:** A stealth VPN protocol. It does not respond to unauthenticated packets, making the endpoint invisible to scanners.49 **Enforcement:** Use pre-shared keys (PSK) for post-quantum resistance.50  
* **Signal Protocol:** Provides end-to-end encryption and minimizes server-side metadata.47  
* **Metadata Mitigation:** Use "Disappearing Messages" to reduce the data footprint. Use "Sealed Sender" to hide the sender's identity from the server.48

### **Identity Verification Rituals**

Encryption is useless without identity proof.

* **Safety Numbers:** Manually verify safety numbers/fingerprints via an out-of-band channel (physical meeting, voice call, different app).48  
* **Attestation:** Use the GrapheneOS Auditor app or Windows Attestation to prove the remote device is in a secure state before sharing sensitive data.25

## **Verification and Audit Framework**

Verification is the act of proving that the system is constrained as intended.

### **Port and Listener Enumeration**

* **Intent:** Identify unauthorized network exposure.  
* **Steps:** Run ss \-tulpn (Linux) or netstat \-ano (Windows). Cross-reference with the allowed flow map.  
* **Evidence:** All listening ports must be documented and justified. Any undocumented port is a failure.

### **Policy Enforcement Testing**

* **Firewall:** Attempt an outbound connection to an unauthorized IP. It must be dropped.  
* **MAC:** Attempt to read /etc/shadow from a non-privileged application. Access must be denied by AppArmor/SELinux.23  
* **WDAC/AppLocker:** Attempt to run an unsigned .exe from the user's Temp folder. It must be blocked.7

### **Leak Testing**

* **Egress Leak:** Monitor traffic while opening a browser or app. Check for telemetry or "phone home" traffic to unauthorized domains.  
* **DNS Leak:** Visit a DNS leak test site. Confirm that all queries are handled by the intended encrypted resolver.

### **Drift Detection and Re-baselining**

Drift is the inevitable divergence from the hardened baseline.4

* **Automated SRE:** Use automated tools to scan for configuration changes daily.4  
* **Evidence:** A "Drift Report" showing zero unauthorized changes to critical registry keys or sysctl parameters.

## **Lifecycle Operations: Procure to Decommission**

Security begins at procurement and ends with physical destruction or secure erasure.

### **Procurement and Provenance**

* **Assumptions:** The supply chain is a threat vector.  
* **Action:** Purchase from verified vendors. Inspect for physical tampering (seals, screws). Verify firmware hashes against vendor-provided manifests.3

### **Secure Decommissioning**

Data must be rendered unrecoverable before asset disposal.52

* **NVMe Crypto Erase:** Instructs the SSD controller to destroy the internal encryption key.  
* **Enforcement:** nvme format /dev/nvmeX \-s 2 \-n 0xffffffff.53  
* **Evidence:** hexdump /dev/nvmeX. Must return no recognizable data (zeros or random).54

### **Maintenance and Exception Management**

* **Exception Policy:** Every hardening exception must be time-bound, documented, and have a named owner.  
* **Triage:** Patch critical vulnerabilities within 24-48 hours. Use automated update channels for browsers and non-critical software.23

## **Failure-Mode Engineering**

Document the system's behavior when controls break.

### **Failure States and Safe Defaults**

* **Silent Logging Failure:** If logs cannot be written, the system must halt sensitive operations to prevent un-audited activity.  
* **Fallback Mechanisms:** Disable "legacy" fallbacks (e.g., falling back to NTLM if Kerberos fails; falling back to HTTP if HTTPS fails).  
* **Emergency Recovery:** Ensure recovery paths (BIOS password reset, recovery keys) are protected with physical security. If physical security is breached, the data must remain encrypted.3

## **Advanced Considerations: Side-Channels and Rollbacks**

Experts must address threats that bypass traditional software boundaries.

### **Side-Channel Exposure**

Systems leak information through physical phenomena.56

* **Timing Attacks:** Use constant-time cryptographic implementations.17  
* **Power/EM Analysis:** Use hardware with EM shielding and power noise generation.58  
* **Acoustic/Thermal:** Implement physical isolation for Tier 0 hardware.57

### **Rollback and Downgrade Attacks**

Attacker force the system to run an older, insecure version.60

* **Enforcement:** Hardware-backed version counters in the TPM or Secure Element. The system must refuse to boot if the firmware or OS version is lower than the counter.26  
* **Evidence:** fwupdmgr get-updates. Verify that the current version is equal to or greater than the hardware-stored minimum.

## **Case Evidence: Mechanical Failure Analysis**

### **Case 1: SolarWinds Supply-Chain Drift**

* **System Context:** Software build system for network management tools.  
* **Boundary Intent:** Restricted egress to prevent C2 communication.  
* **Failure:** Malicious code injected into signed updates. The build server had unconstrained egress, allowing the malware to download its second-stage payload.61  
* **Verification:** Egress monitoring and integrity checks on signed binaries would have alerted the operators to anomalous data flows and modified artifacts.

### **Case 2: Okta Support Breach (HAR File Abuse)**

* **System Context:** Support portal for a global identity provider.  
* **Boundary Intent:** Authentication tokens must be used only by the intended client.  
* **Failure:** Support technicians requested HAR files for troubleshooting. Attackers hijacked the session tokens found in these files.  
* **Actual Event:** Attackers used hijacked tokens to perform API actions as administrators.62  
* **Verification:** Behavioral monitoring for "unusual location/device" and "impossible travel" identified the anomaly.63  
* **Design Change:** Implement Sender-Constrained Tokens to bind the secret to a specific client hardware identity.

## **Templates and Artifacts: Copiable Enforcement**

### **Trust Zone & Allowed-Flow Sheet**

| Source Zone | Dest Zone | Protocol | Port | Justification | Evidence Artifact |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Tier 1 Workstation** | **Internal DNS** | UDP | 53 | Name resolution. | Firewall Log ID 5156\. |
| **App Server** | **DB Segment** | TCP | 5432 | Database query. | SQL Audit Log. |
| **Management VM** | **Endpoint** | TCP | 22 | Remote maintenance. | SSHD Success Log. |

### **Attack Surface Inventory Template**

| Component | Justification | Required? | Hardening Applied | Verification Check |
| :---- | :---- | :---- | :---- | :---- |
| **Bluetooth** | None. | No. | Disabled in BIOS. | system\_profiler |
| **SMB v1.0** | None. | No. | Uninstalled. | Get-SmbServerConfig |
| **Camera** | Web Conferencing. | Yes. | Approved per-app. | Privacy Settings |

### **Decommissioning Checklist**

1. \[ \] Identify all namespaces on the device: nvme list.54  
2. \[ \] Verify Cryptographic Erase support: nvme id-ctrl /dev/nvme0 | grep fna.64  
3. \[ \] Set a temporary drive password to verify state change.55  
4. \[ \] Execute Format with Crypto Erase: nvme format /dev/nvme0 \-s 2 \-n 0xffffffff.53  
5. \[ \] Verify erasure: hexdump /dev/nvme0. Must return null.54  
6. \[ \] Log Serial Number, Timestamp, and Operator name for the audit trail.

## **Dismantling Common Misconceptions**

Hardening replaces "vibes" with mechanical constraints.

* **"Encryption equals security":** False. Encryption without key governance is a lock with the key in it. Hardening is the governance.11  
* **"VPN equals anonymity":** False. A VPN only shifts trust from the ISP to the VPN provider. Metadata still leaks.48  
* **"Updated devices are automatically safe":** False. Updates can introduce new attack surfaces or malicious code (SolarWinds).61  
* **"Biometrics equal identity":** False. Biometrics are usernames, not passwords. They must be backed by hardware attestation.11  
* **"One device can host multiple trust domains":** False. Without strict compartmentalization (Qubes), a compromise in one domain is a compromise of the entire device.29

## **Annotated Bibliography: Stable Principles vs. Decay Notes**

* **NIST SP 800-207 (Zero Trust Architecture):** Foundational for network boundaries.1 *Decay:* Static IP-based examples are aging; identity-based metadata is the new frontier.  
* **Apple Platform Security (2024):** Crucial for silicon trust layers.11 *Decay:* Watch for "Cryptex" updates which change how the system volume is verified.  
* **CIS Benchmarks (Windows/Linux/Mac):** The standard for baseline configuration.66 *Decay:* These decay every 6 months with new OS releases. Always use the latest version (e.g., Windows 11 24H2).  
* **GrapheneOS Features:** The leading research in mobile hardening.26 *Decay:* Hardware support changes frequently. Pixel 6 is nearing EOL; focus on Pixel 8/9 for MTE support.69  
* **Qubes OS Documentation:** Masterclass in spatial isolation.32 *Decay:* Xen vulnerabilities are rare but critical. Monitor the Qubes Security Advisories (QSA).

Digital hardening is the transition from "what the system can do" to "what the system is permitted to do." It is a state of constant verification. Configuration is real. Policy is not. Metadata is data. Drift is inevitable. Verification is the only proof of survival.

#### **Works cited**

1. What Is NIST SP 800-207? zero trust Architecture Framework \- Palo Alto Networks, accessed February 19, 2026, [https://www.paloaltonetworks.com/cyberpedia/what-is-nist-sp-800-207](https://www.paloaltonetworks.com/cyberpedia/what-is-nist-sp-800-207)  
2. NIST SP 800-207 – The Definitive Guide to Zero Trust Architecture \- TerraZone, accessed February 19, 2026, [https://terrazone.io/nist-sp-800-207/](https://terrazone.io/nist-sp-800-207/)  
3. Kicksecure Documentation, accessed February 19, 2026, [https://www.kicksecure.com/wiki/Documentation](https://www.kicksecure.com/wiki/Documentation)  
4. AI SRE in Practice: Diagnosing Configuration Drift in Deployment Failures \- Komodor, accessed February 19, 2026, [https://komodor.com/blog/ai-sre-in-practice-diagnosing-configuration-drift-in-deployment-failures/](https://komodor.com/blog/ai-sre-in-practice-diagnosing-configuration-drift-in-deployment-failures/)  
5. Security baselines guide | Microsoft Learn, accessed February 19, 2026, [https://learn.microsoft.com/en-us/windows/security/operating-system-security/device-management/windows-security-configuration-framework/windows-security-baselines](https://learn.microsoft.com/en-us/windows/security/operating-system-security/device-management/windows-security-configuration-framework/windows-security-baselines)  
6. Windows security documentation | Microsoft Learn, accessed February 19, 2026, [https://learn.microsoft.com/en-us/windows/security/](https://learn.microsoft.com/en-us/windows/security/)  
7. Scripting Endpoint Hardening for MSPs: CIS Benchmarks via PowerShell | NinjaOne, accessed February 19, 2026, [https://www.ninjaone.com/blog/scripting-endpoint-hardening-for-msps-cis-benchmarks-via-powershell/](https://www.ninjaone.com/blog/scripting-endpoint-hardening-for-msps-cis-benchmarks-via-powershell/)  
8. Created a Windows 11 Hardening Script/Guide with PowerShell that uses official and supported methods : r/Windows11 \- Reddit, accessed February 19, 2026, [https://www.reddit.com/r/Windows11/comments/10iqdnn/created\_a\_windows\_11\_hardening\_scriptguide\_with/](https://www.reddit.com/r/Windows11/comments/10iqdnn/created_a_windows_11_hardening_scriptguide_with/)  
9. A PowerShell module to test a machine against the CIS Benchmarks \- GitHub, accessed February 19, 2026, [https://github.com/HersheyTaichou/CIS-Benchmarks](https://github.com/HersheyTaichou/CIS-Benchmarks)  
10. Looking for CIS Benchmark v4 Script for Windows 11 Pro Standalone Machine Hardening Help? : r/PowerShell \- Reddit, accessed February 19, 2026, [https://www.reddit.com/r/PowerShell/comments/1lkqimb/looking\_for\_cis\_benchmark\_v4\_script\_for\_windows/](https://www.reddit.com/r/PowerShell/comments/1lkqimb/looking_for_cis_benchmark_v4_script_for_windows/)  
11. Apple Platform Security, accessed February 19, 2026, [https://help.apple.com/pdf/security/en\_US/apple-platform-security-guide.pdf](https://help.apple.com/pdf/security/en_US/apple-platform-security-guide.pdf)  
12. beerisgood/macOS\_Hardening: a collection about macOS \- GitHub, accessed February 19, 2026, [https://github.com/beerisgood/macOS\_Hardening](https://github.com/beerisgood/macOS_Hardening)  
13. Using the macOS Security Compliance Project \- Apple Training, accessed February 19, 2026, [https://it-training.apple.com/compliance/tutorials/course/sec015/](https://it-training.apple.com/compliance/tutorials/course/sec015/)  
14. Enforcing macOS Security Compliance Project Baselines with Workspace ONE | Omnissa, accessed February 19, 2026, [https://techzone.omnissa.com/resource/enforcing-macos-security-compliance-project-baselines-workspace-one-operational-tutorial](https://techzone.omnissa.com/resource/enforcing-macos-security-compliance-project-baselines-workspace-one-operational-tutorial)  
15. Fixing Compliance on Endpoints in a Baseline Approach \- Apple Training, accessed February 19, 2026, [https://it-training.apple.com/compliance/tutorials/course/sec036/](https://it-training.apple.com/compliance/tutorials/course/sec036/)  
16. Checking Compliance on Endpoints in a Baseline Approach \- Apple Training, accessed February 19, 2026, [https://it-training.apple.com/compliance/tutorials/course/sec035/](https://it-training.apple.com/compliance/tutorials/course/sec035/)  
17. Apple Platform Security Guide (May 2024\) \- Michael Tsai, accessed February 19, 2026, [https://mjtsai.com/blog/2024/05/09/apple-platform-security-guide-may-2024/](https://mjtsai.com/blog/2024/05/09/apple-platform-security-guide-may-2024/)  
18. Lock, Hide, and Protect: iOS 18's Security Features Explained \- Phone Repair NZ, accessed February 19, 2026, [https://www.phonerepair.nz/blog/lock-hide-and-protect-ios-18s-security-features-explained](https://www.phonerepair.nz/blog/lock-hide-and-protect-ios-18s-security-features-explained)  
19. Increase kernel integrity with disabled Linux kernel modules loading \- Linux Audit, accessed February 19, 2026, [https://linux-audit.com/kernel/increase-kernel-integrity-with-disabled-linux-kernel-modules-loading/](https://linux-audit.com/kernel/increase-kernel-integrity-with-disabled-linux-kernel-modules-loading/)  
20. VPS Kernel Hardening: Essential Sysctl Tweaks That Work \- Vodien, accessed February 19, 2026, [https://www.vodien.com/learn/vps-kernel/](https://www.vodien.com/learn/vps-kernel/)  
21. Sysctl Hardening: Advanced Linux Kernel Security Techniques \- CalCom Software, accessed February 19, 2026, [https://calcomsoftware.com/sysctl-configuration-hardening/](https://calcomsoftware.com/sysctl-configuration-hardening/)  
22. Mastering Linux Security: 100 Essential Tips for Distro Hardening, accessed February 19, 2026, [https://www.logicweb.com/knowledge-base/linux-tips/mastering-linux-security-100-essential-tips-for-distro-hardening/](https://www.logicweb.com/knowledge-base/linux-tips/mastering-linux-security-100-essential-tips-for-distro-hardening/)  
23. Linux Server Hardening Steps and Best Practices \- zenarmor.com, accessed February 19, 2026, [https://www.zenarmor.com/docs/linux-tutorials/linux-server-hardening-steps-and-best-practices](https://www.zenarmor.com/docs/linux-tutorials/linux-server-hardening-steps-and-best-practices)  
24. Exploring GrapheneOS secure allocator: Hardened Malloc \- Synacktiv, accessed February 19, 2026, [https://synacktiv.com/en/publications/exploring-grapheneos-secure-allocator-hardened-malloc](https://synacktiv.com/en/publications/exploring-grapheneos-secure-allocator-hardened-malloc)  
25. Features overview | GrapheneOS, accessed February 19, 2026, [https://grapheneos.org/features](https://grapheneos.org/features)  
26. GrapheneOS Privacy and Security Features Broken Down \- Cape, accessed February 19, 2026, [https://www.cape.co/blog/grapheneos-privacy-and-security-features](https://www.cape.co/blog/grapheneos-privacy-and-security-features)  
27. iOS 18 settings to lock down your privacy and security, accessed February 19, 2026, [https://www.helpnetsecurity.com/2025/02/19/ios-18-privacy-security-settings/](https://www.helpnetsecurity.com/2025/02/19/ios-18-privacy-security-settings/)  
28. Enhanced Security and Privacy Features in Apple's iOS 18 You Need To Know About, accessed February 19, 2026, [https://www.securemac.com/news/enhanced-security-and-privacy-features-in-ios-18](https://www.securemac.com/news/enhanced-security-and-privacy-features-in-ios-18)  
29. A quick peek at Qubes OS \- Security By Isolation \- HackLab Bergamo, accessed February 19, 2026, [https://www.hacklabg.net/wp-content/uploads/2023/05/Qubes-OS-Security-by-Isolation.pdf](https://www.hacklabg.net/wp-content/uploads/2023/05/Qubes-OS-Security-by-Isolation.pdf)  
30. qubes-doc/introduction/intro.rst at main \- GitHub, accessed February 19, 2026, [https://github.com/QubesOs/qubes-doc/blob/main/introduction/intro.rst](https://github.com/QubesOs/qubes-doc/blob/main/introduction/intro.rst)  
31. Qubes OS \- Wikipedia, accessed February 19, 2026, [https://en.wikipedia.org/wiki/Qubes\_OS](https://en.wikipedia.org/wiki/Qubes_OS)  
32. Architecture — Qubes OS Documentation, accessed February 19, 2026, [https://doc.qubes-os.org/en/latest/developer/system/architecture.html](https://doc.qubes-os.org/en/latest/developer/system/architecture.html)  
33. System Hardening Checklist \- Kicksecure, accessed February 19, 2026, [https://www.kicksecure.com/wiki/System\_Hardening\_Checklist](https://www.kicksecure.com/wiki/System_Hardening_Checklist)  
34. A Security Hardened Linux Distribution \- Kicksecure, accessed February 19, 2026, [https://www.kicksecure.com/wiki/About](https://www.kicksecure.com/wiki/About)  
35. About NIST 800-207 compliance in 2025 \- Thoropass, accessed February 19, 2026, [https://www.thoropass.com/blog/about-nist-800-207-compliance-in-2025](https://www.thoropass.com/blog/about-nist-800-207-compliance-in-2025)  
36. What is the NIST SP 800-207 cybersecurity framework? \- CyberArk, accessed February 19, 2026, [https://www.cyberark.com/what-is/nist-sp-800-207-cybersecurity-framework/](https://www.cyberark.com/what-is/nist-sp-800-207-cybersecurity-framework/)  
37. ServiceNow Supports NIST 800-207 Zero-Trust Cybersecurity, accessed February 19, 2026, [https://www.servicenow.com/community/secops-articles/servicenow-supports-nist-800-207-zero-trust-cybersecurity/ta-p/3455669](https://www.servicenow.com/community/secops-articles/servicenow-supports-nist-800-207-zero-trust-cybersecurity/ta-p/3455669)  
38. System Hardening with CIS Benchmarks | by Kartik Gupta | Jan, 2026 | Medium, accessed February 19, 2026, [https://medium.com/@berab88696/system-hardening-with-cis-benchmarks-e3b5e7f0fb0c](https://medium.com/@berab88696/system-hardening-with-cis-benchmarks-e3b5e7f0fb0c)  
39. How to Configure nftables Firewall Rules \- OneUptime, accessed February 19, 2026, [https://oneuptime.com/blog/post/2026-01-24-nftables-firewall-rules/view](https://oneuptime.com/blog/post/2026-01-24-nftables-firewall-rules/view)  
40. Using tcpdump with iptables? \- Server Fault, accessed February 19, 2026, [https://serverfault.com/questions/531839/using-tcpdump-with-iptables](https://serverfault.com/questions/531839/using-tcpdump-with-iptables)  
41. TPM Security — The Linux Kernel documentation, accessed February 19, 2026, [https://docs.kernel.org/security/tpm/tpm-security.html](https://docs.kernel.org/security/tpm/tpm-security.html)  
42. Physical TPM Attestation Keys and certificates | Intel® Trust Authority, accessed February 19, 2026, [https://docs.trustauthority.intel.com/main/articles/articles/ita/tpm-ak-provision.html](https://docs.trustauthority.intel.com/main/articles/articles/ita/tpm-ak-provision.html)  
43. openconfig/attestz: API for TPM attestation and enrollment for certificates \- GitHub, accessed February 19, 2026, [https://github.com/openconfig/attestz](https://github.com/openconfig/attestz)  
44. Verify hardware-backed key pairs with key attestation | Security \- Android Developers, accessed February 19, 2026, [https://developer.android.com/privacy-and-security/security-key-attestation](https://developer.android.com/privacy-and-security/security-key-attestation)  
45. Measured Boot — Das U-Boot unknown version documentation, accessed February 19, 2026, [https://docs.u-boot.org/en/latest/usage/measured\_boot.html](https://docs.u-boot.org/en/latest/usage/measured_boot.html)  
46. Trusted Platform Module \- ArchWiki, accessed February 19, 2026, [https://wiki.archlinux.org/title/Trusted\_Platform\_Module](https://wiki.archlinux.org/title/Trusted_Platform_Module)  
47. A Formal Security Analysis of the Signal Messaging Protocol | Request PDF \- ResearchGate, accessed February 19, 2026, [https://www.researchgate.net/publication/345422166\_A\_Formal\_Security\_Analysis\_of\_the\_Signal\_Messaging\_Protocol](https://www.researchgate.net/publication/345422166_A_Formal_Security_Analysis_of_the_Signal_Messaging_Protocol)  
48. Signal Explained: Safe Messaging and Privacy Tips \- Nym, accessed February 19, 2026, [https://nym.com/blog/what-is-signal](https://nym.com/blog/what-is-signal)  
49. Formal Verification of the WireGuard Protocol, accessed February 19, 2026, [https://www.wireguard.com/papers/wireguard-formal-verification.pdf](https://www.wireguard.com/papers/wireguard-formal-verification.pdf)  
50. Protocol & Cryptography \- WireGuard, accessed February 19, 2026, [https://www.wireguard.com/protocol/](https://www.wireguard.com/protocol/)  
51. WireGuard: The Next-Gen VPN Protocol | Keysight Blogs, accessed February 19, 2026, [https://www.keysight.com/blogs/en/tech/nwvs/2022/09/22/wireguard-the-next-gen-vpn-protocol](https://www.keysight.com/blogs/en/tech/nwvs/2022/09/22/wireguard-the-next-gen-vpn-protocol)  
52. Secure Erase: A Comprehensive Guide for 2025 \- Schattenkodierer \- Shadecoder, accessed February 19, 2026, [https://www.shadecoder.com/de/topics/secure-erase-a-comprehensive-guide-for-2025](https://www.shadecoder.com/de/topics/secure-erase-a-comprehensive-guide-for-2025)  
53. Solid state drive/Memory cell clearing \- ArchWiki, accessed February 19, 2026, [https://wiki.archlinux.org/title/Solid\_state\_drive/Memory\_cell\_clearing](https://wiki.archlinux.org/title/Solid_state_drive/Memory_cell_clearing)  
54. NVMe Secure Erase \- tinyapps.org, accessed February 19, 2026, [https://tinyapps.org/docs/nvme-secure-erase.html](https://tinyapps.org/docs/nvme-secure-erase.html)  
55. SSD \- SATA / NVMe secure wipe : r/sysadmin \- Reddit, accessed February 19, 2026, [https://www.reddit.com/r/sysadmin/comments/1ou4q94/ssd\_sata\_nvme\_secure\_wipe/](https://www.reddit.com/r/sysadmin/comments/1ou4q94/ssd_sata_nvme_secure_wipe/)  
56. Side-channel attack \- Wikipedia, accessed February 19, 2026, [https://en.wikipedia.org/wiki/Side-channel\_attack](https://en.wikipedia.org/wiki/Side-channel_attack)  
57. Side-Channel Attacks: Methods Exploits and Defense Guide, accessed February 19, 2026, [https://www.startupdefense.io/cyberattacks/side-channel-attack](https://www.startupdefense.io/cyberattacks/side-channel-attack)  
58. Side Channel Attacks: An Overview of Exploits, Defenses, and Emerging Trends \- Medium, accessed February 19, 2026, [https://medium.com/@syskey0909/side-channel-attacks-an-overview-of-exploits-defenses-and-emerging-trends-2d20accc3cbd](https://medium.com/@syskey0909/side-channel-attacks-an-overview-of-exploits-defenses-and-emerging-trends-2d20accc3cbd)  
59. Understanding Side-Channel Attacks: A Comprehensive Guide \- eMazzanti Technologies, accessed February 19, 2026, [https://www.emazzanti.net/understanding-side-channel-attacks/](https://www.emazzanti.net/understanding-side-channel-attacks/)  
60. iOS Platform Security \- ISEC, accessed February 19, 2026, [https://www.isec.tugraz.at/wp-content/uploads/2023/09/2024-05-03-iOS-Platform-Security.pdf](https://www.isec.tugraz.at/wp-content/uploads/2023/09/2024-05-03-iOS-Platform-Security.pdf)  
61. SolarWinds Issues Advisory Regarding Salesloft Drift Security Incident \- Cyber Press, accessed February 19, 2026, [https://cyberpress.org/solarwinds-releases/](https://cyberpress.org/solarwinds-releases/)  
62. Okta October 2023 Security Incident Investigation Closure, accessed February 19, 2026, [https://sec.okta.com/articles/harfiles/](https://sec.okta.com/articles/harfiles/)  
63. Five Lessons Learned from Okta's Support Site Breach \- Valence Security, accessed February 19, 2026, [https://www.valencesecurity.com/resources/blogs/five-lessons-learned-from-oktas-support-site-breach](https://www.valencesecurity.com/resources/blogs/five-lessons-learned-from-oktas-support-site-breach)  
64. Secure data deletion for NVMe drive \- IBM, accessed February 19, 2026, [https://www.ibm.com/docs/linuxonibm/liaau/secure\_nvme.html](https://www.ibm.com/docs/linuxonibm/liaau/secure_nvme.html)  
65. Configuring the Trusted Platform Module (TPM) Key Attestation \- Uwe Gradenegger, accessed February 19, 2026, [https://www.gradenegger.eu/en/configuring-the-trusted-platform-module-tpm-key-attestation/](https://www.gradenegger.eu/en/configuring-the-trusted-platform-module-tpm-key-attestation/)  
66. CIS Benchmarks March 2024 Update, accessed February 19, 2026, [https://www.cisecurity.org/insights/blog/cis-benchmarks-march-2024-update](https://www.cisecurity.org/insights/blog/cis-benchmarks-march-2024-update)  
67. Microsoft Windows Desktop \- CIS Benchmarks, accessed February 19, 2026, [https://www.cisecurity.org/benchmark/microsoft\_windows\_desktop](https://www.cisecurity.org/benchmark/microsoft_windows_desktop)  
68. GrapheneOS: the private and secure mobile OS, accessed February 19, 2026, [https://grapheneos.org/](https://grapheneos.org/)  
69. Graphene OS: a security-enhanced Android build \- LWN.net, accessed February 19, 2026, [https://lwn.net/Articles/1030004/](https://lwn.net/Articles/1030004/)  
70. Documentation style guide \- Qubes OS, accessed February 19, 2026, [https://www.qubes-os.org/doc/documentation-style-guide/](https://www.qubes-os.org/doc/documentation-style-guide/)