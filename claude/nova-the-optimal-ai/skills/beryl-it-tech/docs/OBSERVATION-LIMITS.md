# What a three-second observation can tell you

A sample describes a few conditions on the Windows computer running the companion. Use it to compare moments and decide what to examine next. Its values do not measure the cause of a slowdown.

## Read the values in their actual scope

**CPU busy time** is the busy fraction of system CPU time over the three-second interval. It does not identify an application or measure how long your action waited. Windows configurations with more than one active processor group leave whole-PC CPU unavailable rather than presenting a partial reading as complete. Failed or unusable timing counters also remain unavailable.

**RAM available** is physical memory available at the end of the interval. It includes reusable memory. A single reading does not establish a memory leak, excessive paging or application-specific use.

**Space available to this account** refers to the Windows system volume, with account quotas reflected where applicable. The saved reading also retains total volume free space and the account's reported capacity. These are space measurements, not storage health or speed. The companion does not enumerate drives or inspect their files.

**Power** reports the current AC and battery information Windows supplies. An unknown value remains unknown. “No system battery” and “battery information unavailable” are different results. The companion does not predict remaining battery life or change power settings.

The comparison uses percentage points for a difference between CPU percentages and scaled byte units, including MiB or GiB, for memory and space. One GiB is 1,073,741,824 bytes. Original values remain beside each difference.

## Keep time, workload and identity together

The CPU reading covers the stated interval. RAM, space and power are point readings at its end. Tell Beryl what you were doing around each sample and what conditions changed. The companion does not capture that context automatically.

Comparison requires two distinct samples with the same known local machine identity. That identity is a hash of the Windows computer name, not a unique hardware identity. A rename or copied folder can prevent comparison, and duplicate computer names can limit what a match establishes. Keep the original readings and their identity note with the question.

If comparison is blocked, inspect each saved sample under **Observe this PC**. Ask Beryl how to compare the actual circumstances; do not relabel a sample to force a match.

## Keep the next question open

These readings do not measure temperature, thermal throttling, network quality, storage health, storage speed or an individual application's delay. A value changing after an intervention does not prove that intervention caused the change or resolved the original failure.

Beryl can use the observations beside your symptom and other evidence to choose the next discriminating test. Proposed tests in an investigation remain proposals until their actual results are recorded and assessed. The fixed Windows observation is the companion's only direct device-observation action.

[Take and compare observations](FIRST-USE.md) or [read the prepared investigation](READ-AN-INVESTIGATION.md).
