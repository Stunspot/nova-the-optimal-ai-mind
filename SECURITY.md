# Security policy

Report vulnerabilities privately to Collaborative Dynamics before public disclosure. Do not include credentials, private prompts, customer data, live databases, or exploit material beyond what is necessary to reproduce the issue safely.

The highest-risk surfaces are the prompt-submit hook, local Python execution, plugin installation, SQLite state, file-producing specialist scripts, untrusted retrieved content, and any host tool with external side effects.

The package does not grant authority to send messages, publish, purchase, change accounts, use credentials, perform destructive operations, or act in regulated domains. Skills must preserve host permission and user authorization boundaries.

For a suspected vulnerability:

1. stop before further external or destructive action;
2. preserve exact versions, hashes, inputs, outputs, and receipts;
3. determine whether the issue is package source, installer, host, dependency, configuration, or untrusted input;
4. prepare the smallest safe reproduction;
5. keep public claims bounded until the defect and affected versions are known.