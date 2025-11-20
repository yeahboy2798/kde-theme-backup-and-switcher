#!/bin/bash
echo "🗑  Uninstalling KDE Theme Backup & Switcher…"

FILES=(
    "/usr/bin/kde-theme"
    "/usr/bin/kde-theme-gui"
)

DIRS=(
    "/usr/lib/kde-theme-backup"
)

DESKTOP_FILE="/usr/share/applications/kde-theme-backup.desktop"

ICON_BASE="/usr/share/icons/hicolor"
ICON_SIZES=(16x16 24x24 32x32 48x48 64x64 128x128 256x256 512x512 scalable)

# Remove binaries
for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "🗑  Removing $f"
        sudo rm -f "$f"
    else
        echo "⚠️  $f not found (already removed)"
    fi
done

# Remove app directory
for d in "${DIRS[@]}"; do
    if [ -d "$d" ]; then
        echo "🗑  Removing directory $d"
        sudo rm -rf "$d"
    else
        echo "⚠️  Directory $d not found (already removed)"
    fi
done

# Remove desktop entry
if [ -f "$DESKTOP_FILE" ]; then
    echo "🗑  Removing desktop entry $DESKTOP_FILE"
    sudo rm -f "$DESKTOP_FILE"
else
    echo "⚠️  Desktop entry already removed"
fi

# Remove icons for all sizes
for size in "${ICON_SIZES[@]}"; do
    ICON_PATH="$ICON_BASE/$size/apps/kde-theme-backup.png"
    if [ -f "$ICON_PATH" ]; then
        echo "🗑  Removing icon: $ICON_PATH"
        sudo rm -f "$ICON_PATH"
    fi
done

# Clear icon cache
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    echo "🔄 Updating icon cache…"
    sudo gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1
fi

# Clear desktop cache
sudo update-desktop-database >/dev/null 2>&1

# Clear shell command cache
hash -r

echo "✅ Uninstallation complete!"
echo "If installed via .deb, you may also run:"
echo "  sudo dpkg -r kde-theme-backup"
