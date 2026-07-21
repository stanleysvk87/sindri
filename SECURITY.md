# Security policy

Sindri is a personal/homelab tool, not a maintained enterprise product —
see the [README's "Security model" and "Known limitations"](./README.md#security-model)
sections for what is and isn't handled today, and read `docs/SANDBOX.md`
/ `docs/REMOTE_EXEC.md` before enabling either of those optional
features.

## Reporting a vulnerability

If you find a security issue, please open a
[GitHub Security Advisory](https://github.com/stanleysvk87/sindri/security/advisories/new)
(private, not a public issue) instead of filing a normal issue. Include:

- what you found and why it matters (impact),
- steps to reproduce,
- which version/commit you tested against.

There's no bug bounty and no SLA — this is maintained by one person in
their spare time — but reports are read and taken seriously, and fixes
for anything real ship as soon as practical.

## Supported versions

Only the `master` branch / latest commit is supported. There are no
long-term-support releases.
