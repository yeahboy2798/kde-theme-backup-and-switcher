# kde-theme-backup

A tiny CLI tool to **snapshot and restore KDE Plasma setups**:

- Global theme (LookAndFeel)
- Plasma + app theme config
- Icons, color schemes, wallpapers
- Kvantum themes & config
- Latte Dock config/layouts
- Panel & widget layout (optional)

Perfect for distro hopping or messing with themes without fear 😄

---

## Features and CLI usage

- `kde-theme backup <name>`  
  Create a named snapshot under `~/kde-theme-backups/<name>` and `<name>.tar.gz`.

- `kde-theme restore <name>`  
  Restore **theme only** (no panel/widget layout overwrite).  
  Also restores Kvantum, icons, wallpapers, Latte configs, etc.

- `kde-theme restore-layout <name>`  
  Restore **panel & widget layout + Latte layouts**.  
  Warns about missing plasmoids before applying.

- `kde-theme restore-all <name>`  
  Restore theme **and** layout together.

- `kde-theme list`  
  List available snapshots.

- Automatically:
  - Saves the current **Global Theme ID**.
  - On restore, applies the saved global theme with `lookandfeeltool`.
  - If the theme isn’t installed, warns you and lets you install it first.

---

The tool works via:

- A **CLI** (`kde-theme`)  
- An optional **GUI** (`kde_theme_gui.py`) built with PyQt6

## GUI usage

- Requirements:
  - Python 3
  - PyQt6 (on Debian/Ubuntu-based distros: `sudo apt install python3-pyqt6`)
  - If the theme isn’t installed, warns you and lets you install it first.

- Make kde_theme_gui.py executable
- `chmod +x kde_theme_gui.py`
- Launch gui
- `./kde_theme_gui.py`  

---


## Install

```bash
git clone git@github.com:yeahboy2798/kde-theme-backup-and-switcher.git
cd kde-theme-backup-and-switcher
chmod +x kde-theme install-kde-theme.sh
sudo ./install-kde-theme.sh
# kde-theme-backup-and-switcher
