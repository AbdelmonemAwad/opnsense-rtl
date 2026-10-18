# Security

## Reporting a vulnerability

**Not in a public issue, please.** Report it privately through GitHub -
[**Report a vulnerability**](https://github.com/AbdelmonemAwad/opnsense-rtl/security/advisories/new),
on the Security tab - where only you and the owner see it, and the fix can be prepared before anything is
public. Without a GitHub account, write to **eg2@live.com**. Either way, include:

- what is affected - the template patches, the generated stylesheets, the installer, the hooks and the self-update;
- the version you installed and the OPNsense version;
- how to reproduce it, and what you saw.

This is one person's project, worked on in the evenings: expect an answer within days, not hours.
A fix is made in a pull request and the reporter credited in it, unless they ask not to be.

## What is supported

The newest version on `main`, and the newest release where there are releases. Fixes go there,
with no backports.

## Worth knowing before you report

- **It patches the GUI's templates.** A patch that breaks the login page, or lets a template do something the original does not, is a vulnerability: report it here, privately.
- The installer and the self-update run as root: anything that makes them install something other than this repository's files is a vulnerability.
- **Never send a configuration backup.** It holds keys and passwords.
