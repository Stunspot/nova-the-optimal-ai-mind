# Capability reminders

Nova should not forget a useful ability just because it lives in a plugin folder somewhere. MIND’s reminder layer keeps a small, public-safe map of the capabilities that ship with this package and can bring nearby ones to Nova’s attention while she is understanding your request.

This is a reminder, not an autopilot. A returned capability is not selected, activated, installed, healthy, recommended, or authorized. Nova still decides whether it fits the job, and you still control any real-world action.

## What happens when you add something

Talk normally: “add this skill,” “install this plugin,” “we should wire in a tool that can…,” or “replace that old program.” Capability Promotion is meant to recognize that kind of moment and remind MIND that the new durable ability may need a reminder card of its own.

That is deliberately a conversational trigger. MIND does not repeatedly scan or hash your entire harness looking for changes. The goal is simply that the act of adding something cool does not create a future “why does Nova never remember this exists?” problem.

## What is stored

The public reminder map contains authored capability descriptions, aliases, relations, and semantic representations. It does not include private skill bodies, credentials, personal records, private source paths, or raw task text.

The included map is structurally checked and available for local use. Its broader behavioral qualification is still in progress. If the reminder path is unavailable, Nova can still work with capabilities Codex exposes; she should say that the reminder field was unavailable rather than pretending otherwise.

For the privacy boundary, see [Privacy and trust](PRIVACY-AND-TRUST.md). For repair steps, see [Troubleshooting](TROUBLESHOOTING.md).
