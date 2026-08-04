# **Windows Systems Engineering Knowledge Base: Architecture, Internals, and Operational Dynamics**

## **1\. Epistemic Foundation: The Systems Thinking Approach to Windows Operations**

This Knowledge Base establishes a foundational framework for reasoning about the Windows operating system in enterprise and critical infrastructure environments. It rejects the rote application of checklists in favor of a first-principles understanding of system architecture. The seasoned operator does not ask "What is the fix?" but rather "What is the state deviation, and what mechanism produced it?" This document is structured to encode durable systems thinking, enabling the diagnosis of complex, emergent failures that defy standard troubleshooting scripts.

Windows must be understood not as a monolithic product but as a collection of interdependent, stateful subsystems—Memory Manager, Object Manager, I/O Manager, Configuration Manager (Registry), and the Security Subsystem (LSA)—interacting asynchronously under constraints of hardware resources and network latency. Operational success depends on distinguishing between **deterministic behavior** (code paths guaranteed by the kernel) and **entropy** (nondeterminism introduced by drivers, hardware interrupts, network jitter, and user interaction).

### **1.1 Observability Over Action**

The primary directive of advanced Windows engineering is **observability before action**. Interventions applied without a quantified understanding of the root cause introduce "gray failures"—partial degradations that are harder to diagnose than total outages. We prioritize evidence from high-fidelity sources: Event Tracing for Windows (ETW), kernel memory dumps, and transaction logs, over heuristic "best practices" or third-party optimization tools. The discipline of "looking before fixing" prevents the compounding of errors where a remediation attempt masks the original symptom while introducing new instability.

### **1.2 The Trust Boundary Model**

Operational reasoning must strictly define trust boundaries to accurately assess security and stability risks. The distinction between User Mode (Ring 3\) and Kernel Mode (Ring 0\) is the most fundamental boundary in the Windows architecture.1 Transitions between these modes are expensive and strictly controlled via system calls. Drivers, although often running in kernel mode, represent a significant surface area for instability. Security is not merely a configuration state but a continuous negotiation of identity tokens, access control lists (ACLs), and privilege attributes across these boundaries.2

## ---

**2\. Kernel Architecture and Memory Management Internals**

Understanding the Windows NT kernel (ntoskrnl.exe) is prerequisite to diagnosing performance anomalies, resource exhaustion, and system crashes (Bug Checks). The kernel coordinates hardware abstraction, process scheduling, and memory management, serving as the arbiter of all system resources.

### **2.1 User Mode vs. Kernel Mode Dynamics**

The processor operates in two distinct modes to protect system stability and isolate critical functions from errant applications.

* **User Mode (Ring 3):** Applications, subsystems (like CSRSS), and services run in User Mode. They operate within a private virtual address space and cannot access hardware or kernel memory directly. To perform privileged operations—such as reading a file, sending a network packet, or creating a thread—user-mode threads must call into the OS via System Calls (syscalls). This triggers a context switch, transitioning the processor to Kernel Mode.1  
* **Kernel Mode (Ring 0):** Core operating system components and Kernel-Mode Drivers execute here. Code in this mode shares a single virtual address space and has unrestricted access to system memory and hardware.  
  * **Operational Insight:** High CPU usage in Kernel Mode (visible in Task Manager or Performance Monitor as "Privileged Time") typically indicates driver inefficiency, excessive I/O processing (interrupt storms), or heavy filtering (e.g., antivirus filter drivers) rather than application logic faults. Unlike User Mode crashes, which terminate a single process, a crash in Kernel Mode (an unhandled exception) is catastrophic, triggering a Bug Check (Blue Screen of Death) to preserve data integrity and prevent corruption.1  
  * **Driver Ecology:** While the User-Mode Driver Framework (UMDF) allows some drivers to run safely in Ring 3, many critical drivers (graphics, storage, networking) remain in Kernel Mode for performance reasons.1

### **2.2 Memory Management and Virtual Address Spaces**

Windows utilizes a flat 32-bit or 64-bit virtual address space, abstracting physical RAM from running processes. The Virtual Memory Manager (VMM) maps virtual addresses to physical pages (RAM) or disk storage (Pagefile).5

#### **2.2.1 Address Translation and Paging**

The CPU's Memory Management Unit (MMU) uses page tables to translate virtual addresses to physical addresses on the fly. This architecture allows Windows to overcommit memory, providing processes with more virtual memory than physically exists.6

* **Demand Paging:** Pages are only loaded into physical RAM when accessed. This minimizes startup I/O but can cause "page fault" latency during initial access. A "Hard Fault" occurs when the page must be read from the disk (pagefile or mapped file), causing significant latency compared to a "Soft Fault" (page found elsewhere in RAM).7  
* **Working Set:** The subset of virtual pages currently resident in physical RAM. The Memory Manager aggressively trims working sets when physical memory is scarce, forcing data out to the pagefile.8

#### **2.2.2 Kernel Memory Pools: Paged vs. Non-Paged**

Kernel memory is strictly divided into pools with distinct behaviors, and monitoring these is critical for diagnosing system-wide hangs or resource exhaustion.

* **Non-Paged Pool:** This memory is guaranteed to reside in physical RAM at all times; it cannot be paged out to disk. It is used for critical kernel structures, interrupt handlers, and synchronization objects that must be accessed at high IRQL (Interrupt Request Level) where page faults are illegal.  
  * **Diagnostic Implication:** A leak in the Non-Paged Pool is a critical stability risk. It depletes physical RAM available for all other processes. Even if CPU usage is low, a system with exhausted Non-Paged Pool will become unresponsive. Operators should use poolmon.exe or Performance Monitor counters (Memory\\Pool Nonpaged Bytes) to identify leaks.5  
* **Paged Pool:** This memory can be written to the pagefile when not in use. It is used for less critical system objects. Excessive usage here can lead to system slowness due to increased paging activity.

### **2.3 The Object Manager and Handle Tables**

Windows manages resources (files, registry keys, synchronization events, processes) as **Objects**. The **Object Manager** maintains a global namespace (e.g., \\Device\\HarddiskVolume1) and controls object lifecycles.10

* **Handles:** User-mode applications interact with kernel objects exclusively via **Handles**. These are opaque indices in a per-process handle table that point to the actual kernel objects.  
* **Reference Counting:** The Object Manager maintains a reference count for every object. An object is not deleted from memory until its reference count drops to zero.  
* **Handle Leaks:** A common failure mode occurs when an application opens objects but fails to close them (call CloseHandle). This exhausts kernel memory (specifically Paged Pool) and can prevent other processes from opening files or creating threads.  
  * **Troubleshooting:** The \!handle extension in WinDbg or the "Handles" column in Task Manager/Process Explorer are essential for identification. If a process has hundreds of thousands of handles, it is likely leaking resources, potentially destabilizing the entire OS.12

## ---

**3\. The Boot Process: Initialization Principles and Failure Analysis**

The Windows boot process is a strictly ordered sequence of handoffs, transitioning from firmware to the kernel. Troubleshooting boot failures requires identifying the exact phase of interruption, as symptoms in one phase often resemble those in another but require vastly different remediation strategies.

### **3.1 Phase 1: PreBoot (Firmware and UEFI)**

Modern Windows systems utilize the Unified Extensible Firmware Interface (UEFI). The initialization flow proceeds through **SEC** (Security) \-\> **PEI** (Pre-EFI Initialization) \-\> **DXE** (Driver Execution Environment) \-\> **BDS** (Boot Device Selection).14

* **Secure Boot Mechanics:** This feature enforces trust by verifying digital signatures of the bootloader. The firmware stores keys: Platform Key (PK), Key Exchange Keys (KEK), and the Signature Database (db/dbx).16  
* **Failure Mode:** If the bootloader’s signature is invalid (e.g., modified by a rootkit or corruption) or if the signature has been revoked (present in dbx), the firmware refuses to hand off execution. This manifests as a boot loop or immediate fallback to the firmware setup menu without any Windows error message.17  
* **Troubleshooting:** In scenarios where valid bootloaders fail, checking the dbx revocation list updates is necessary. Disabling Secure Boot temporarily is a diagnostic step to rule out signature issues versus corruption.17

### **3.2 Phase 2: Windows Boot Manager**

The firmware loads bootmgfw.efi (Windows Boot Manager). This component reads the Boot Configuration Data (BCD) to determine which OS to load and where it resides.14

* **BCD Architecture:** The BCD is a registry hive loaded from the EFI System Partition. It replaces the legacy boot.ini.  
* **Operational Relevance:** "Boot Device Not Found" or a black screen with a blinking cursor often implies BCD corruption or partition misalignment.  
  * **Remediation:** The bootrec /rebuildbcd command is standard, but if the volume is unidentifiable, disk sector corruption may be preventing the BCD read. Operators must distinguish between logical BCD errors and physical I/O failures.14

### **3.3 Phase 3: Windows OS Loader**

The Boot Manager loads winload.efi. This loader is responsible for the transition from the firmware environment to the Windows kernel environment. Its duties include:

1. **Loading the Kernel:** It loads ntoskrnl.exe and the Hardware Abstraction Layer (hal.dll) into memory.  
2. **Loading Boot Start Drivers:** It loads drivers marked as BOOT\_START in the registry (e.g., file system drivers, disk filters).  
3. **Mode Transition:** It transitions the processor from real/protected mode into 64-bit long mode.14  
* **Failure Indicator:** Errors here often reference specific missing files (system32\\ntoskrnl.exe is missing or corrupt) or driver signature enforcement failures (0xc0000428). This confirms the disk is readable (Phase 2 passed), but the OS payload is compromised.

### **3.4 Phase 4: Kernel Initialization and Session Management**

Once the kernel executes, it initializes memory managers, the I/O manager, and starts the Session Manager Subsystem (smss.exe).

* **SMSS:** The first user-mode process. It creates environment variables, defines DOS device mappings (e.g., C:), and starts csrss.exe (Client/Server Runtime Subsystem) and wininit.exe.14  
* **"Pending.xml" Blocking:** A pervasive boot failure mode occurs when a Windows Update operation (Component Based Servicing) writes a pending.xml file to perform file replacements at boot. If this XML is malformed or the referenced files are missing, the kernel hangs or loops during the "Applying update operation" phase.  
  * **Advanced Remediation:** If standard rollback fails, recovery requires loading the system registry hive offline (using WinRE) and modifying the TrustedInstaller service start type, or removing the pending.xml file from C:\\Windows\\WinSxS\\ and its registry references (pendingxmlidentifier) to forcefully break the loop. This is a high-risk operation that leaves the component store in an inconsistent state, requiring subsequent DISM repair.14

## ---

**4\. Identity, Authentication, and Security Subsystems**

Identity is the perimeter. In Windows, identity is managed via the Local Security Authority (LSA) and enforced through Access Tokens and Security Descriptors. Operational failures here are often silent, manifesting as "Access Denied" errors that do not implicate the network but rather the *security context* of the request.

### **4.1 The Access Token and Security Context**

When a user authenticates, the LSA generates an **Access Token**. This token is the digital passport for the session and contains:

* **User SID:** The unique Security Identifier for the account.  
* **Group SIDs:** SIDs for all groups the user belongs to (including transitive memberships).  
* **Privileges:** User rights such as SeShutdownPrivilege or SeDebugPrivilege.2

#### **4.1.1 Token Bloat ("MaxTokenSize")**

As users are added to more Active Directory groups, their token size increases. The token contains the SIDs of every group the user is a member of.

* **The Mechanism:** The Kerberos ticket (containing the PAC) grows with group membership. If the generated token exceeds MaxTokenSize (default 12KB in older versions, 48KB in modern Windows), authentication fails or group policy processing aborts.  
* **Calculation:** $TokenSize \\approx 1200 \+ 40d \+ 8s$, where $d$ is Domain Local groups and $s$ is Global/Universal groups.  
* **Symptoms:** Users experience bizarre, intermittent "Access Denied" errors, or Group Policy fails to apply specific settings.  
* **Diagnostic:** Use klist to view ticket sizes or check the registry values (HKLM\\System\\CurrentControlSet\\Control\\Lsa\\Kerberos\\Parameters\\MaxTokenSize) to diagnose and adjust this limit.21

### **4.2 Kerberos Architecture and Failure Modes**

Kerberos is the default authentication protocol for Active Directory. It relies on mutual authentication via tickets and is highly sensitive to time skew and duplicate identities.

1. **AS-REQ / AS-REP:** User authenticates to the Key Distribution Center (KDC) and receives a Ticket Granting Ticket (TGT).  
2. **TGS-REQ / TGS-REP:** User presents TGT to request a Service Ticket (ST) for a specific resource (e.g., CIFS/File Share).  
3. **AP-REQ:** User presents the ST to the application server.

#### **4.2.1 Critical Failure: KRB\_AP\_ERR\_MODIFIED**

This specific error indicates that the service ticket presented by the client could not be decrypted by the server. This is a cryptographic mismatch, not a network failure.

* **Root Cause:** The server's machine account password (stored in Active Directory) does not match the password stored locally in the server's LSA secret (System Hive). Alternatively, duplicate Service Principal Names (SPNs) exist in the directory, causing the KDC to encrypt the ticket with the wrong account's key.  
* **Operational Scenario:** This frequently happens after restoring a VM snapshot of a server (reverting its local password state to an older value) or when multiple servers behind a load balancer share an identity without proper clustering configuration.  
* **Remediation:** Reset the computer account password (Reset-ComputerMachinePassword) or identify duplicate SPNs (setspn \-X).23

### **4.3 PAC Validation and Golden/Silver Ticket Attacks**

The **Privilege Attribute Certificate (PAC)** is an extension field in the Kerberos ticket containing the user's group memberships and other authorization data. It is signed by the KDC.

* **Golden Ticket Attack:** A forged TGT created using the stolen NTLM hash of the KRBTGT account. Since the KRBTGT key validates the TGT, an attacker can create tickets with arbitrary group memberships (e.g., Domain Admin) and infinite lifetimes. This grants domain-wide persistence.25  
* **Silver Ticket Attack:** A forged Service Ticket signed with a specific service account's hash (e.g., the SQL Service account). This grants access only to that specific service but bypasses the KDC entirely. Detection relies on analyzing Event ID 4769 (Service Ticket Request) for anomalies where no preceding TGT request (Event ID 4768\) exists.27  
* **PAC Validation Defense:** By default, services may not validate the PAC signature with the KDC to reduce load. Enabling ValidateKdcPacSignature (Registry: HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa\\Kerberos\\Parameters, Value: 1\) forces the server to verify the PAC with a Domain Controller.  
  * **Tradeoff:** While this adds security, it introduces latency and a hard dependency on DC availability for every authentication request. It does *not* fully prevent Golden Tickets (since the KDC identity itself is spoofed if KRBTGT is compromised) but acts as a defense-in-depth measure against forged service tickets.29

### **4.4 Hybrid Identity: Azure AD Connect Internals**

In hybrid environments, the **Azure AD Connect Authentication Agent** facilitates Pass-through Authentication (PTA), allowing users to sign in to cloud resources using on-premises validation.

* **Mechanism:** The agent makes an outbound HTTPS connection to Azure. When a user signs in, Azure queues a validation request. The agent picks it up, calls the Win32 LogonUser API against the local Active Directory, and returns the result.32  
* **Troubleshooting:**  
  * **"Stopped-Extension-DLL-Exception":** A generic error in the synchronization service often caused by password expiration of the connector account or corruption in the MIISClient.  
  * **Trace Logs:** Agent logs are located in %ProgramData%\\Microsoft\\Azure AD Connect Authentication Agent\\Trace. These text logs contain detailed error codes (e.g., AADSTS80005 for unpredictable web exceptions, AADSTS80002 for timeouts) essential for diagnosing connectivity issues that Event Viewer misses.34

## ---

**5\. Networking Stack: Tuning and Diagnostics**

Windows networking is built on a modular stack (NDIS, TCP/IP, WFP). Performance issues in server environments often arise from default configurations that are tuned for client compatibility rather than high-throughput server workloads.

### **5.1 Port Exhaustion and Registry Tuning**

In high-concurrency scenarios (e.g., proxy servers, heavy SQL clients), Windows may run out of ephemeral ports (dynamic ports).

* **The Symptom:** WSAEADDRINUSE errors, dropped connections, or inability to establish new outbound sockets.  
* **The Mechanism:** When a TCP connection closes, it enters a TIME\_WAIT state for 240 seconds (default) to ensure all packets are received. During this time, the port cannot be reused. If the connection rate exceeds the port recycling rate, the pool exhausts.  
* **Diagnostic:** Use netstat \-ano | find "TIME\_WAIT" to quantify the backlog.  
* **Registry Tuning (HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters):**  
  * MaxUserPort: Increases the dynamic port range (default is often dynamic 49152-65535; can be expanded up to 65534). Note that netsh int ipv4 set dynamicport tcp is the preferred modern method to adjust this range.36  
  * TcpTimedWaitDelay: Reduces the wait time (e.g., to 30 seconds), freeing ports faster.  
  * **Warning:** Setting TcpTimedWaitDelay too low can cause packet collision if the network has high latency, leading to data corruption or reset connections.36

| Registry Value | Default | Recommended (High Load) | Risk |
| :---- | :---- | :---- | :---- |
| MaxUserPort | Dynamic (approx 16k) | 65534 | Port conflict with static services |
| TcpTimedWaitDelay | 240s (0xF0) | 30s (0x1E) | Packet collision/confusion |

### **5.2 Network Virtualization: RSS and VMQ**

For high-speed (10GbE+) networking, single-core CPU processing becomes a bottleneck. Processing network interrupts on CPU0 only will saturate that core while others remain idle.

* **Receive Side Scaling (RSS):** Distributes incoming network processing across multiple CPU cores by hashing packet headers.  
  * **Configuration:** Use Set-NetAdapterRss to configure the BaseProcessorNumber and MaxProcessors. Ensure these align with the hardware NUMA topology to avoid expensive memory access across nodes.41  
* **Virtual Machine Queue (VMQ):** Uses hardware filtering on the NIC to DMA packets directly to VM memory, bypassing the host switch overhead.  
  * **Configuration Hazard:** If VMQ is enabled on a NIC that doesn't support it properly (driver bugs) or is misconfigured in the Hyper-V switch, it causes massive packet loss or latency.  
  * **Diagnostic:** Use Get-NetAdapterVmq and Get-NetAdapterVmqQueue to verify processor assignments. A common misconfiguration is failing to exclude the "Base Processor" (usually CPU0) from VMQ usage, causing contention with the host OS.43

### **5.3 SMB and RPC Internals**

* **RPC (Remote Procedure Call):** The backbone of Windows management. It uses the **Endpoint Mapper (EPM)** on port 135 to negotiate dynamic high ports. Firewalls blocking these high ports result in "RPC Server Unavailable."  
  * **Debugging:** The error 0x6BA (RPC Server Unavailable) requires checking the EPM response *and* the dynamic port range connectivity.46  
* **SMB Performance:** File transfer slowness is often due to small I/O sizes or lack of parallelism. The SMB client throttles throughput on high-latency links by default. Disabling bandwidth throttling via the registry (DisableBandwidthThrottling in LanmanWorkstation\\Parameters) can significantly improve throughput on WAN links.47

## ---

**6\. Update Architecture and State Management**

Windows updates are not simple file replacements; they are complex transactions managed by the **Component Based Servicing (CBS)** stack. Understanding this prevents the destruction of the OS during cleanup attempts.

### **6.1 The Component Store (WinSxS)**

Located at C:\\Windows\\WinSxS, this directory contains all versions of system components.

* **The Hard Link Illusion:** Files in C:\\Windows\\System32 are essentially hard links to the WinSxS store. Tools that claim WinSxS is "bloated" often double-count these files. "Deleting" WinSxS to save space effectively deletes the operating system's files.  
* **Corruption Repair:** If the component store is corrupt, updates fail. The DISM /Online /Cleanup-Image /RestoreHealth command interacts with the CBS engine to repair the store from a known good source (Windows Update or ISO).  
* **States:** Packages exist in states: **Absent**, **Staged** (present but inactive), **Installed**, and **Superseded**. Understanding these states prevents the error of trying to "install" a corrupted package when it should be "unstaged" first.49

### **6.2 Cluster Aware Updating (CAU)**

CAU orchestrates updates across a Failover Cluster to maintain availability.

* **Workflow:** It places a node in Maintenance Mode (draining roles via Live Migration), installs updates (via Windows Update Agent), reboots, and validates the node before proceeding to the next.  
* **Architecture:** It uses a Coordinator node (which can be self-updating). Logs are found in Microsoft-Windows-ClusterAwareUpdating event channels.  
* **Failure Modes:** Failures often stem from WMI connectivity issues between the coordinator and nodes, or timeouts when draining roles. If the CAU plugin fails, the cluster may be left in a partitioned state.52

### **6.3 State Drift and the "Debloater" Myth**

Operators must rigorously avoid "Debloater" scripts found on consumer forums. These scripts often force-remove dependencies (e.g., removing the AppX framework or Store backend) that appear dormant but are required for Sysprep, future feature updates, or the shell (Start Menu). Removing them creates a "frankin-OS" that cannot be serviced, leading to unrecoverable errors (0x800f081f) during cumulative updates or "Access Denied" errors when shell components try to load.55

## ---

**7\. Advanced Diagnostics: The Discipline of Observation**

The difference between a guess and a diagnosis is tracing. The following tools provide the necessary fidelity for root cause analysis.

### **7.1 Event Tracing for Windows (ETW)**

ETW is the kernel's unified tracing mechanism. It is low-overhead, omnipresent, and always on.

* **Architecture:** **Providers** emit events, **Controllers** start/stop sessions, and **Consumers** read the .etl files.  
* **WPR/WPA:** The **Windows Performance Recorder (WPR)** captures ETW traces. The **Windows Performance Analyzer (WPA)** visualizes them.  
* **Case Study \- High CPU:** Task Manager shows svchost.exe at 100%. This is useless information.  
  * **Workflow:** Capture a trace with WPR (CPU profile). Open in WPA. Group by "Service" to reveal the specific sub-service (e.g., wuauserv). Analyze the **Stack** column in WPA (loading symbols) to reveal the exact function call (e.g., ntdll\!RtlAllocateHeap) causing the spin. This differentiates between a memory leak, a tight loop, or lock contention.57

### **7.2 Process Monitor (ProcMon)**

ProcMon captures File System, Registry, and Network activity in real-time.

* **Boot Logging:** Capable of tracing boot-time drivers before the UI loads, essential for diagnosing slow startups.  
* **"Access Denied" Analysis:** Filtering for Result \= ACCESS DENIED is the definitive way to diagnose permission issues. It reveals exactly which user context attempted to access which resource and failed, often exposing missing ACLs on obscure registry keys or temp folders that event logs do not capture.60

### **7.3 Crash Dump Analysis (WinDbg)**

When a system halts (Bug Check), it writes memory to a .dmp file.

* **The Command:** \!analyze \-v is the starting point.  
* **Reasoning:** Identify the "Faulting IP" (Instruction Pointer). Is it in a Microsoft module (likely hardware/corruption) or a third-party driver (likely the root cause)?  
* **Paging in Dumps:** Kernel memory dumps do not contain user-mode memory. If the crash was triggered by a user-mode process passing bad data to a driver, a kernel dump may be insufficient. A "Complete Memory Dump" is required for full context.63

### **7.4 Wait Chain Traversal**

When an application hangs (Stop Responding), it is often waiting on a resource held by another thread.

* **Mechanism:** The **Wait Chain Traversal (WCT)** API allows the OS to detect these dependencies.  
* **Diagnostic:** In Task Manager or Resource Monitor, right-click the process and select "Analyze Wait Chain." It will identify if the process is deadlocked or waiting for network I/O. This is often faster than a full debugger session.66

## ---

**8\. Conclusion: The Strategic Operator**

Operating Windows at scale requires abandoning the "reboot and pray" methodology. The system is deterministic; every error code (0x80070005 \- Access Denied, 0xC0000005 \- Access Violation) is a precise breadcrumb leading to a specific subsystem interaction.

The strategic operator:

1. **Validates Identity:** Checks for Kerberos skew, SPN duplicates, and token bloat before blaming the network.  
2. **Tunes for Workload:** Adjusts TCP parameters and NIC offloads (RSS/VMQ) based on server role, not defaults.  
3. **Respects State:** Uses DISM/PowerShell for configuration, avoids destructive "cleaners," and understands the CBS servicing model.  
4. **Diagnoses with Data:** Uses ETW/WPA/ProcMon to prove the root cause.

By adhering to these principles, the Windows environment shifts from a black box of random failures to a managed, observable system where uptime is a product of engineering, not luck.

### **Appendix: Diagnostic Reference Table**

| Symptom | Primary Tool | Key Indicator/Command |
| :---- | :---- | :---- |
| **Boot Failure** | WinRE Command Prompt | Check pending.xml in WinSxS; bootrec /rebuildbcd. |
| **High CPU (Unknown)** | WPA (Windows Performance Analyzer) | Sampled CPU Usage \-\> Stack Walk (Look for specific driver functions). |
| **Access Denied** | Process Monitor | Filter: Result is ACCESS DENIED. Check path and user context. |
| **Port Exhaustion** | Netstat / Regedit | \`netstat \-ano |
| **Auth Failures** | Event Viewer (Security) | Event ID 4624 (Logon), 4768 (TGT), 4769 (TGS), 4771 (Kerberos Pre-Auth Failed). |
| **BSOD** | WinDbg | \!analyze \-v, lm (list modules), \!thread. |
| **Slow Network (VM)** | PowerShell | Get-NetAdapterVmq, Get-NetAdapterRss. Verify Base Processor alignment. |
| **App Hang** | Resource Monitor | Right-click process \-\> "Analyze Wait Chain". |

#### **Works cited**

1. User Mode and Kernel Mode \- Windows drivers \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/user-mode-and-kernel-mode](https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/user-mode-and-kernel-mode)  
2. Parts of the Access Control Model \- Win32 apps | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-components](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-components)  
3. Windows Security Model for Driver Developers \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/driversecurity/windows-security-model](https://learn.microsoft.com/en-us/windows-hardware/drivers/driversecurity/windows-security-model)  
4. \!analyze (WinDbg) \- Windows drivers | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-analyze](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-analyze)  
5. Memory Management for Windows Drivers \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-for-drivers](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/managing-memory-for-drivers)  
6. Virtual Address Space (Memory Management) \- Win32 apps | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows/win32/memory/virtual-address-space](https://learn.microsoft.com/en-us/windows/win32/memory/virtual-address-space)  
7. Physical and Virtual Memory in Windows 10 \- Microsoft Q\&A, accessed January 1, 2026, [https://learn.microsoft.com/en-us/answers/questions/2696389/physical-and-virtual-memory-in-windows-10](https://learn.microsoft.com/en-us/answers/questions/2696389/physical-and-virtual-memory-in-windows-10)  
8. Memory Management Architecture Guide \- SQL Server | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/sql/relational-databases/memory-management-architecture-guide?view=sql-server-ver17](https://learn.microsoft.com/en-us/sql/relational-databases/memory-management-architecture-guide?view=sql-server-ver17)  
9. Overview of Windows Memory Space \- Windows drivers \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/overview-of-windows-memory-space](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/overview-of-windows-memory-space)  
10. Windows Kernel-Mode Object Manager \- Windows drivers \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/windows-kernel-mode-object-manager](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/windows-kernel-mode-object-manager)  
11. Kernel-Mode Driver Architecture Design Guide \- Windows drivers | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/](https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/)  
12. \!handle (WinDbg) \- Windows drivers | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-handle](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-handle)  
13. Kernel Objects \- Win32 apps \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows/win32/sysinfo/kernel-objects](https://learn.microsoft.com/en-us/windows/win32/sysinfo/kernel-objects)  
14. Windows boot issues troubleshooting \- Windows Client | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-boot-issues-troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/windows-boot-issues-troubleshooting)  
15. Delivering a great startup and shutdown experience | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/test/weg/delivering-a-great-startup-and-shutdown-experience](https://learn.microsoft.com/en-us/windows-hardware/test/weg/delivering-a-great-startup-and-shutdown-experience)  
16. Windows Secure Boot Key Creation and Management Guidance | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-secure-boot-key-creation-and-management-guidance?view=windows-11](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-secure-boot-key-creation-and-management-guidance?view=windows-11)  
17. Secure boot | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/oem-secure-boot](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/oem-secure-boot)  
18. Windows 10 Booting process in details \- Microsoft Q\&A, accessed January 1, 2026, [https://learn.microsoft.com/en-us/answers/questions/3255385/windows-10-booting-process-in-details](https://learn.microsoft.com/en-us/answers/questions/3255385/windows-10-booting-process-in-details)  
19. CBS Pending reboot after rebooting \- Server Fault, accessed January 1, 2026, [https://serverfault.com/questions/807939/cbs-pending-reboot-after-rebooting](https://serverfault.com/questions/807939/cbs-pending-reboot-after-rebooting)  
20. Access Tokens \- Win32 apps \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens)  
21. Best Practices for Securing Active Directory, accessed January 1, 2026, [https://repo.zenk-security.com/Protocoles\_reseaux\_securisation/Best%20Practices%20for%20Securing%20Active%20Directory.pdf](https://repo.zenk-security.com/Protocoles_reseaux_securisation/Best%20Practices%20for%20Securing%20Active%20Directory.pdf)  
22. Windows \- Marcelo's Spaces \- WordPress.com, accessed January 1, 2026, [https://marcelodba.wordpress.com/tag/windows/](https://marcelodba.wordpress.com/tag/windows/)  
23. Kerberos client receives KRB\_AP\_ERR\_MODIFIED error \- Windows ..., accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/kerberos-client-krb-ap-err-modified-error](https://learn.microsoft.com/en-us/troubleshoot/windows-server/windows-security/kerberos-client-krb-ap-err-modified-error)  
24. 4769(S, F) A Kerberos service ticket was requested. \- Windows 10 | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4769](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4769)  
25. What is a Golden Ticket Attack? \- Xcitium, accessed January 1, 2026, [https://www.xcitium.com/knowledge-base/golden-ticket-attack/](https://www.xcitium.com/knowledge-base/golden-ticket-attack/)  
26. Golden Ticket Attacks: The Account That is Always There\! \- Wolf & Company, P.C., accessed January 1, 2026, [https://www.wolfandco.com/resources/blog/golden-ticket-attacks-account-always-there/](https://www.wolfandco.com/resources/blog/golden-ticket-attacks-account-always-there/)  
27. How to Defend Against Silver Ticket Attacks | Semperis Guide, accessed January 1, 2026, [https://www.semperis.com/blog/how-to-defend-against-silver-ticket-attacks/](https://www.semperis.com/blog/how-to-defend-against-silver-ticket-attacks/)  
28. What is a Silver Ticket Attack? | CrowdStrike, accessed January 1, 2026, [https://www.crowdstrike.com/en-us/cybersecurity-101/cyberattacks/silver-ticket-attack/](https://www.crowdstrike.com/en-us/cybersecurity-101/cyberattacks/silver-ticket-attack/)  
29. Active Directory Security Fundamentals (Part 1)- Kerberos \- RootDSE, accessed January 1, 2026, [https://rootdse.org/posts/active-directory-security-1/](https://rootdse.org/posts/active-directory-security-1/)  
30. Optimize Nodinite Performance – Disabling PAC Verification for Kerberos, accessed January 1, 2026, [https://docs.nodinite.com/Documentation/InstallAndUpdate?doc=/Troubleshooting/Windows/PACVerification](https://docs.nodinite.com/Documentation/InstallAndUpdate?doc=/Troubleshooting/Windows/PACVerification)  
31. How the Kerberos PAC Works \- Netwrix, accessed January 1, 2026, [https://netwrix.com/en/resources/blog/what-is-the-kerberos-pac/](https://netwrix.com/en/resources/blog/what-is-the-kerberos-pac/)  
32. Microsoft Entra Connect: Pass-through Authentication, accessed January 1, 2026, [https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta](https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta)  
33. Microsoft Entra pass-through authentication \- Quickstart, accessed January 1, 2026, [https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta-quick-start](https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta-quick-start)  
34. User Privacy and Microsoft Entra pass-through authentication, accessed January 1, 2026, [https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta-user-privacy](https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/how-to-connect-pta-user-privacy)  
35. Microsoft Entra Connect: Troubleshoot Pass-through Authentication, accessed January 1, 2026, [https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/tshoot-connect-pass-through-authentication](https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/tshoot-connect-pass-through-authentication)  
36. TCP/IP port exhaustion troubleshooting \- Windows Client | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting)  
37. How to see what is reserving ephemeral port ranges on Windows? \- Stack Overflow, accessed January 1, 2026, [https://stackoverflow.com/questions/54010365/how-to-see-what-is-reserving-ephemeral-port-ranges-on-windows](https://stackoverflow.com/questions/54010365/how-to-see-what-is-reserving-ephemeral-port-ranges-on-windows)  
38. all of sudden windows machines failing to authenticate for domain users. \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/answers/questions/5664728/all-of-sudden-windows-machines-failing-to-authenti](https://learn.microsoft.com/en-us/answers/questions/5664728/all-of-sudden-windows-machines-failing-to-authenti)  
39. Windows 10 ephemeral port exhaustion but netstat says otherwise? \- Super User, accessed January 1, 2026, [https://superuser.com/questions/1348102/windows-10-ephemeral-port-exhaustion-but-netstat-says-otherwise](https://superuser.com/questions/1348102/windows-10-ephemeral-port-exhaustion-but-netstat-says-otherwise)  
40. Adjusting TCP Settings for Heavy Load on Windows, accessed January 1, 2026, [https://docs.oracle.com/cd/E23507\_01/Search.20073/ATGSearchAdmin/html/s1207adjustingtcpsettingsforheavyload01.html](https://docs.oracle.com/cd/E23507_01/Search.20073/ATGSearchAdmin/html/s1207adjustingtcpsettingsforheavyload01.html)  
41. Set-NetAdapterRss (NetAdapter) | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/powershell/module/netadapter/set-netadapterrss?view=windowsserver2025-ps](https://learn.microsoft.com/en-us/powershell/module/netadapter/set-netadapterrss?view=windowsserver2025-ps)  
42. Set the Number of RSS Processors for Improved Performance \- Windows drivers, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/network/setting-the-number-of-rss-processors](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/setting-the-number-of-rss-processors)  
43. Virtual Machine Queue Offloading \- 29.3 \- ID:705831 | Intel® Ethernet Adapters and Devices User Guide, accessed January 1, 2026, [https://edc.intel.com/content/www/id/id/design/products/ethernet/adapters-and-devices-user-guide/29.3/virtual-machine-queue-offloading/](https://edc.intel.com/content/www/id/id/design/products/ethernet/adapters-and-devices-user-guide/29.3/virtual-machine-queue-offloading/)  
44. RSS and VMQ Tuning on Windows Servers \- Broadcom Inc., accessed January 1, 2026, [https://www.broadcom.com/support/knowledgebase/1211161326328/rss-and-vmq-tuning-on-windows-servers](https://www.broadcom.com/support/knowledgebase/1211161326328/rss-and-vmq-tuning-on-windows-servers)  
45. Virtual Receive-side Scaling in Windows Server 2012 R2 | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/dn383582(v=ws.11)](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-r2-and-2012/dn383582\(v=ws.11\))  
46. RPC error troubleshooting guidance \- Windows Client \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/rpc-errors-troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/rpc-errors-troubleshooting)  
47. Optimizing Windows configuration for VDI desktops \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/remote-desktop-services-vdi-optimize-configuration](https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/remote-desktop-services-vdi-optimize-configuration)  
48. Slow SMB files transfer speed \- Windows Server \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/slow-smb-file-transfer](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/slow-smb-file-transfer)  
49. Clean Up the WinSxS Folder \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/clean-up-the-winsxs-folder?view=windows-11](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/clean-up-the-winsxs-folder?view=windows-11)  
50. Large WinSxS directory causes disk space issues \- Windows Client \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/previous-versions/troubleshoot/windows-client/address-disk-space-issues-caused-by-winsxs](https://learn.microsoft.com/en-us/previous-versions/troubleshoot/windows-client/address-disk-space-issues-caused-by-winsxs)  
51. Understanding Component-Based Servicing | Microsoft Community Hub, accessed January 1, 2026, [https://techcommunity.microsoft.com/blog/askperf/understanding-component-based-servicing/373012](https://techcommunity.microsoft.com/blog/askperf/understanding-component-based-servicing/373012)  
52. Cluster-Aware Updating overview \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-server/failover-clustering/cluster-aware-updating](https://learn.microsoft.com/en-us/windows-server/failover-clustering/cluster-aware-updating)  
53. Cluster-Aware Updating \- Frequently Asked Questions \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-server/failover-clustering/cluster-aware-updating-faq](https://learn.microsoft.com/en-us/windows-server/failover-clustering/cluster-aware-updating-faq)  
54. Windows Server Failover Clustering \- NXLog Platform Documentation, accessed January 1, 2026, [https://docs.nxlog.co/integrate/windows-server-failover-clustering.html](https://docs.nxlog.co/integrate/windows-server-failover-clustering.html)  
55. Please don't use "debloat" software, scripts or commands, especially if you don't know exactly what it does : r/Windows11 \- Reddit, accessed January 1, 2026, [https://www.reddit.com/r/Windows11/comments/1m95ltl/please\_dont\_use\_debloat\_software\_scripts\_or/](https://www.reddit.com/r/Windows11/comments/1m95ltl/please_dont_use_debloat_software_scripts_or/)  
56. Debloating Windows 11: Why a Cleaner PC Can Break Updates, accessed January 1, 2026, [https://windowsforum.com/threads/debloating-windows-11-why-a-cleaner-pc-can-break-updates.383570/](https://windowsforum.com/threads/debloating-windows-11-why-a-cleaner-pc-can-break-updates.383570/)  
57. CPU Analysis | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/test/wpt/cpu-analysis](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/cpu-analysis)  
58. Page 2 – Performance is everything. But correctness comes first. \- Alois Kraus, accessed January 1, 2026, [https://aloiskraus.wordpress.com/page/2/](https://aloiskraus.wordpress.com/page/2/)  
59. svchost.exe Windows process \- What is it? \- Neuber software, accessed January 1, 2026, [https://www.neuber.com/taskmanager/process/svchost.exe.html](https://www.neuber.com/taskmanager/process/svchost.exe.html)  
60. Getting started with Procmon: The Beginner's Guide to Monitoring Windows Systems, accessed January 1, 2026, [https://www.advancedinstaller.com/process-monitor-beginner-guide.html](https://www.advancedinstaller.com/process-monitor-beginner-guide.html)  
61. Start Button is not working in Windows Server 2019 \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-my/answers/questions/5584398/start-button-is-not-working-in-windows-server-2019](https://learn.microsoft.com/en-my/answers/questions/5584398/start-button-is-not-working-in-windows-server-2019)  
62. Case of the unexplained: Windows troubleshooting with Mark Russinovich Microsoft Ignite English English \- Filmot, accessed January 1, 2026, [https://filmot.com/sidebyside/QJTTMLOMMMc/en/en/English/English/Case+of+the+unexplained%3A+Windows+troubleshooting+with+Mark+Russinovich/Microsoft+Ignite](https://filmot.com/sidebyside/QJTTMLOMMMc/en/en/English/English/Case+of+the+unexplained%3A+Windows+troubleshooting+with+Mark+Russinovich/Microsoft+Ignite)  
63. Analyze a Kernel-Mode Dump File by Using WinDbg \- Windows drivers | Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/analyzing-a-kernel-mode-dump-file-with-windbg](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/analyzing-a-kernel-mode-dump-file-with-windbg)  
64. Read small memory dump files \- Windows Client \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/read-small-memory-dump-file](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/read-small-memory-dump-file)  
65. Memory dump file options \- Windows Server \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/memory-dump-file-options](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/memory-dump-file-options)  
66. CPU usage always around 40% because of wait-chain? \- Super User, accessed January 1, 2026, [https://superuser.com/questions/568867/cpu-usage-always-around-40-because-of-wait-chain](https://superuser.com/questions/568867/cpu-usage-always-around-40-because-of-wait-chain)  
67. Alternative Tools for Application Hangs | Microsoft Community Hub, accessed January 1, 2026, [https://techcommunity.microsoft.com/blog/askperf/alternative-tools-for-application-hangs/1685245](https://techcommunity.microsoft.com/blog/askperf/alternative-tools-for-application-hangs/1685245)  
68. Wait chain traversal \- Win32 apps \- Microsoft Learn, accessed January 1, 2026, [https://learn.microsoft.com/en-us/windows/win32/debug/wait-chain-traversal](https://learn.microsoft.com/en-us/windows/win32/debug/wait-chain-traversal)