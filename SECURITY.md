# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Send a report by email to **m.lettieri@microbees.com** with:

- a description of the vulnerability
- steps to reproduce
- potential impact
- any suggested fix (optional)

You will receive an acknowledgement within **48 hours** and a status update
within **7 days**.

## Scope

ScribIA reads git history and writes documentation files within the
repository it is run from. It does not make network requests, store
credentials, or communicate with external services. The main attack surface
is **malicious content in git diff output** that could be passed to
documentation templates — please report any injection or path-traversal
finding.
