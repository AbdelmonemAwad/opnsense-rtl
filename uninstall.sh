#!/bin/sh
#-
# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 Abdelmonem Awad <eg2@live.com>
#
# Put the original page templates back and remove the mirrored stylesheets and the boot hook.

# the self-update and the trigger first, so that nothing puts the layout back meanwhile
rm -f /usr/local/etc/cron.d/opnsense-rtl-update
rm -f /usr/local/share/pkg/triggers/opnsense-rtl.ucl
python3 /root/opnsense-rtl/apply_rtl.py --remove
rm -f /usr/local/etc/rc.syshook.d/start/61-opnsense-rtl
rm -f /root/opnsense-rtl/self-update.py
rm -rf /usr/local/share/opnsense-rtl
