#!/bin/bash
#
# build-deb.sh - build a .deb that installs BOTH:
#   - kde-theme (CLI)
#   - KDE Theme Backup & Switcher GUI
#
# Usage:
#   ./build-deb.sh [version]
#
# Requirements:
#   - This script must be run from the repo root
#   - Files expected in the repo root:
#       kde-theme
#       kde_theme_gui.py
#       uninstall-kde-theme.sh
#       kdethemebackup.png
#
# Output:
#   kde-theme-backup_<version>_all.deb (default version: 1.0.0)

set -e

PKG_NAME="kde-theme-backup"
VERSION="${1:-1.0.0}"
BUILD_DIR="deb-build"
INSTALL_ROOT="$BUILD_DIR/usr"
DEBIAN_DIR="$BUILD_DIR/DEBIAN"

echo "🔧 Building $PKG_NAME version $VERSION"

# Sanity checks
for f in kde-theme kde_theme_gui.py uninstall-kde-theme.sh kdethemebackup.png; do
  if [ ! -f "$f" ]; then
    echo "❌ Required file '$f' not found in current directory."
    exit 1
  fi
done

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$INSTALL_ROOT/bin"          "$INSTALL_ROOT/lib/kde-theme-backup"          "$INSTALL_ROOT/share/applications"          "$INSTALL_ROOT/share/icons/hicolor/256x256/apps"          "$DEBIAN_DIR"

# ----- Install CLI -----
echo "📦 Installing CLI to deb tree…"
cp kde-theme "$INSTALL_ROOT/bin/kde-theme"
chmod 755 "$INSTALL_ROOT/bin/kde-theme"

# ----- GUI launcher wrapper -----
echo "📦 Installing GUI launcher…"
cat > "$INSTALL_ROOT/bin/kde-theme-gui" << 'EOF'
#!/bin/bash
exec python3 /usr/lib/kde-theme-backup/kde_theme_gui.py "$@"
EOF
chmod 755 "$INSTALL_ROOT/bin/kde-theme-gui"

# ----- GUI Python file -----
echo "📦 Installing GUI python script…"
cp kde_theme_gui.py "$INSTALL_ROOT/lib/kde-theme-backup/kde_theme_gui.py"
chmod 755 "$INSTALL_ROOT/lib/kde-theme-backup/kde_theme_gui.py"

# ----- Uninstaller script -----
echo "📦 Installing uninstaller…"
cp uninstall-kde-theme.sh "$INSTALL_ROOT/lib/kde-theme-backup/uninstall-kde-theme.sh"
chmod 755 "$INSTALL_ROOT/lib/kde-theme-backup/uninstall-kde-theme.sh"

# ----- Desktop entry -----
echo "📦 Writing desktop file…"
cat > "$INSTALL_ROOT/share/applications/kde-theme-backup.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=KDE Theme Backup & Switcher
Comment=Backup and restore KDE Plasma themes and layouts
Exec=kde-theme-gui
Icon=kde-theme-backup
Terminal=false
Categories=Utility;Settings;Qt;KDE;
Keywords=kde;theme;layout;backup;switcher;
EOF

# ----- Icon -----
echo "📦 Installing icon…"
cp kdethemebackup.png "$INSTALL_ROOT/share/icons/hicolor/256x256/apps/kdethemebackup.png"
chmod 644 "$INSTALL_ROOT/share/icons/hicolor/256x256/apps/kdethemebackup.png"

# ----- DEBIAN/control -----
echo "📦 Writing DEBIAN/control…"
cat > "$DEBIAN_DIR/control" << EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: yeahboy2798
Depends: bash, python3, python3-pyqt6
Description: Backup and restore KDE Plasma themes, layouts, and appearance.
 KDE Theme Backup & Switcher provides a simple CLI (kde-theme) and GUI
 to snapshot and restore KDE theme setups, including panels, widgets,
 icons, colors, cursors, Kvantum, and Latte Dock layouts.
EOF

chmod 644 "$DEBIAN_DIR/control"

# ----- Build the .deb -----
OUT_DEB="installer.deb"
echo "🧱 Building .deb -> $OUT_DEB"
dpkg-deb --build "$BUILD_DIR" "$OUT_DEB"

echo "✅ Done. Created $OUT_DEB"
