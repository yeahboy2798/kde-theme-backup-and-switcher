#!/bin/bash
set -e

# Where we'll install the GUI Python script
APP_LIB_DIR="/usr/lib/kde-theme-backup"
APP_SCRIPT="$APP_LIB_DIR/kde_theme_gui.py"

# Wrapper binary name
WRAPPER_BIN="/usr/local/bin/kde-theme-gui"

# Desktop file location (user-local)
DESKTOP_FILE="$HOME/.local/share/applications/kde-theme-backup-gui.desktop"

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

# Ensure Python & PyQt6 are installed (Debian/Ubuntu style)
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is not installed. Please install it first."
  exit 1
fi

if ! python3 - << 'EOF'
try:
    import PyQt6  # type: ignore
except ImportError:
    raise SystemExit(1)
EOF
then
  echo "PyQt6 is not installed. On Debian/Ubuntu, install it with:"
  echo "  sudo apt install python3-pyqt6"
  exit 1
fi

echo "Installing KDE Theme Backup & Switcher GUI..."

# Copy GUI script to /usr/lib/kde-theme-backup
mkdir -p "$APP_LIB_DIR"
cp "$(dirname "$0")/kde_theme_gui.py" "$APP_LIB_DIR/"
chmod 644 "$APP_SCRIPT"

# Create wrapper executable in /usr/local/bin
cat > "$WRAPPER_BIN" <<EOF
#!/bin/bash
python3 "$APP_SCRIPT" "\$@"
EOF

chmod +x "$WRAPPER_BIN"

# Create desktop file in user's applications menu
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=KDE Theme Backup & Switcher
Comment=Backup and restore KDE Plasma themes and layouts
Exec=kde-theme-gui
Icon=preferences-desktop-theme-global
Terminal=false
Categories=Settings;Utility;Qt;KDE;
Keywords=kde;theme;layout;backup;switcher;
EOF

# Refresh desktop database (best effort)
update-desktop-database "$(dirname "$DESKTOP_FILE")" 2>/dev/null || true

echo "✅ Installed GUI:"
echo "  - Script:   $APP_SCRIPT"
echo "  - Wrapper:  $WRAPPER_BIN"
echo "  - Desktop:  $DESKTOP_FILE"
echo
echo "You can now launch it from your KDE menu (search: 'KDE Theme Backup & Switcher')"
echo "or run: kde-theme-gui"
