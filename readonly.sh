#!/bin/sh
# Remount root back to read-only after ./readwrite.sh, restoring
# protection against SD-card corruption from a hard power-loss.
#
# Usage: ./readonly.sh

set -eu

sudo mount -o remount,ro /
mount | grep ' / '
