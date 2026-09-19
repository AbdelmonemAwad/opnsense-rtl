#!/bin/sh
# Put the original page templates back and remove the mirrored stylesheets and the boot hook.

python3 /root/opnsense-rtl/apply_rtl.py --remove
rm -f /usr/local/etc/rc.syshook.d/start/61-opnsense-rtl
