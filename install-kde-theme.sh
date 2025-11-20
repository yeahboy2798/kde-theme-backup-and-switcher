#!/bin/bash
set -e

TARGET="/usr/local/bin/kde-theme"

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

cp "$(dirname "$0")/kde-theme" "$TARGET"
chmod +x "$TARGET"

echo "Installed kde-theme to $TARGET"
