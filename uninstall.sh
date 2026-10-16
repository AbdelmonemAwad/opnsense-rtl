#!/bin/sh
# Put the original page templates back and remove the mirrored stylesheets and the boot hook.

# the trigger first, so that no package installed meanwhile puts the layout back
rm -f /usr/local/share/pkg/triggers/opnsense-rtl.ucl
python3 /root/opnsense-rtl/apply_rtl.py --remove
rm -f /usr/local/etc/rc.syshook.d/start/61-opnsense-rtl
