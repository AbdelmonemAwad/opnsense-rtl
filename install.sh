#!/bin/sh
#-
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 Abdelmonem Awad <eg2@live.com>
#
# Install the right-to-left layout on an OPNsense firewall. Run as root from a copy of this repository:
#   sh install.sh
# The files are kept in /root/opnsense-rtl and re-applied after core updates: by a pkg trigger the
# moment an update writes a template or a stylesheet (an update that only installs packages does
# not reboot), and by a boot hook at every boot. A new release is installed from XGS: Updates
# (os-xgs-npu's Plugins tab), or by hand with self-update.py.

set -e
HERE=$(cd "$(dirname "$0")" && pwd)
DEST=/root/opnsense-rtl

mkdir -p "${DEST}"
if [ "${HERE}" != "${DEST}" ]; then
    cp "${HERE}/apply_rtl.py" "${HERE}/make_rtl_css.py" "${HERE}/rtl-extra.css" "${DEST}/"
    install -m 0755 "${HERE}/self-update.py" "${DEST}/self-update.py"
fi
install -m 0755 "${HERE}/61-opnsense-rtl" /usr/local/etc/rc.syshook.d/start/61-opnsense-rtl
mkdir -p /usr/local/share/pkg/triggers
install -m 0644 "${HERE}/opnsense-rtl.ucl" /usr/local/share/pkg/triggers/opnsense-rtl.ucl
# No daily self-update since 2026-10-20: a release is installed from XGS: Updates
# (its Plugins tab, in os-xgs-npu) or by hand with self-update.py. An older
# install's cron entry goes.
rm -f /usr/local/etc/cron.d/opnsense-rtl-update

# What this install is, for the self-update: the commit, from a git checkout, or from the
# .source-commit stamp that an xgs-image-builder image or the self-update leaves in the tree.
# Without either it is recorded as unknown, and the self-update takes the latest release once.
REV=; RDATE=; RSRC=unknown
if [ -e "${HERE}/.git" ] && REV=$(git -C "${HERE}" rev-parse HEAD 2>/dev/null); then
    RDATE=$(git -C "${HERE}" log -1 --format=%cI 2>/dev/null); RSRC=git
elif [ -s "${HERE}/.source-commit" ]; then
    read -r REV RDATE _ < "${HERE}/.source-commit"; RSRC=stamp
else
    REV=
fi
case ${REV} in *[!0-9a-f]*) REV=; RDATE=; RSRC=unknown ;; esac
install -d -m 0755 /usr/local/share/opnsense-rtl
printf '{"commit": "%s", "date": "%s", "source": "%s", "installed_at": %s}\n' \
    "${REV}" "${RDATE}" "${RSRC}" "$(date +%s)" > /usr/local/share/opnsense-rtl/installed.json
python3 "${DEST}/apply_rtl.py"
