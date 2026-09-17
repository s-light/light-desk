#!/bin/sh
# Temporarily remount root read-write, for making changes (git pull,
# editing configs, deploying scripts) on a board set up with
# setup-readonly-root.sh. Pair with ./readonly.sh when done.
#
# Usage: ./readwrite.sh

set -eu

sudo mount -o remount,rw /
mount | grep ' / '
