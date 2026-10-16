#!/bin/sh
# Install the right-to-left layout on an OPNsense firewall. Run as root from a copy of this repository:
#   sh install.sh
# The files are kept in /root/opnsense-rtl and re-applied after core updates: by a pkg trigger the
# moment an update writes a template or a stylesheet (an update that only installs packages does
# not reboot), and by a boot hook at every boot.

set -e
HERE=$(cd "$(dirname "$0")" && pwd)
DEST=/root/opnsense-rtl

mkdir -p "${DEST}"
if [ "${HERE}" != "${DEST}" ]; then
    cp "${HERE}/apply_rtl.py" "${HERE}/make_rtl_css.py" "${HERE}/rtl-extra.css" "${DEST}/"
fi
install -m 0755 "${HERE}/61-opnsense-rtl" /usr/local/etc/rc.syshook.d/start/61-opnsense-rtl
mkdir -p /usr/local/share/pkg/triggers
install -m 0644 "${HERE}/opnsense-rtl.ucl" /usr/local/share/pkg/triggers/opnsense-rtl.ucl
python3 "${DEST}/apply_rtl.py"
