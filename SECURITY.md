# Security policy

## Reporting a vulnerability

Please don't open a public issue. Report it privately through GitHub instead: on the repository's **Security** tab, choose **Report a vulnerability**. Only the maintainers can see the report.

Include what you found, how to reproduce it, and what an attacker could do with it. We'll confirm we've received it, keep you posted while we work on a fix, and credit you in the release notes unless you'd rather we didn't.

## Supported versions

TelemetryTaco is pre-1.0. Fixes go into `main` and the next release; older releases aren't patched.

## Known limitations

These are known and tracked, so they don't need a report:

- **There is no authentication** ([#30](https://github.com/Agile-Flimflam/TelemetryTaco/issues/30)). Anyone who can reach the API can send events and read them all back. Don't expose a deployment to the internet without something in front of it that authenticates. See [docs/deployment.md](docs/deployment.md).
- Rate limits are per client IP and only as accurate as `TRUSTED_PROXY_COUNT` is for your proxy setup.
