# kde-theme-backup

A tiny CLI & GUI tool to **snapshot, restore, and switch KDE Plasma setups**:

- Global theme (LookAndFeel)
- Plasma + KDE app configuration
- Icons, color schemes, wallpapers
- Kvantum themes & config
- Latte Dock config & layouts
- Panel & widget layout (optional)

Perfect for people who constantly explore new looks but want to snap back to their own theme without re-customizing everything.

> 📌 Backups and restores are **per-user**. Copies you create only apply to the current account; restoring them on another user account is not supported yet.

---

# ✨ Features

### CLI (`kde-theme`)
- `kde-theme backup <name>`  
  Create a named snapshot under `~/kde-theme-backups/<name>`.

- `kde-theme restore <name>`  
  Restore **theme only** (safe).

- `kde-theme restore-layout <name>`  
  Restore **panels, widgets, and Latte Dock**.

- `kde-theme restore-all <name>`  
  Restore **both theme & layout**.

- `kde-theme list`  
  Show all backups.

### Automatic behaviors:
- Detects and applies the saved **Global Theme ID**
- Warns about missing plasmoids/widgets
- Restores Kvantum, icons, color schemes, Latte, wallpapers, etc.

### GUI (`kde-theme-gui`)
A PyQt6 interface to:

- Create backups
- Restore theme / layout / both
- Delete backups
- View log output in real time  
- No terminal needed

---

# 🖥️ GUI Usage (Manual Execution)

If you want to run the GUI manually from the repo:

### Requirements:
```bash
sudo apt install python3 python3-pyqt6
```

### Run:

```bash
chmod +x kde_theme_gui.py
./kde_theme_gui.py
```

---

# 📦 Install (Development Version, from Repo)

```bash
git clone https://github.com/yeahboy2798/kde-theme-backup-and-switcher
cd kde-theme-backup-and-switcher
chmod +x kde-theme install-kde-theme.sh
sudo ./install-kde-theme.sh
```

This installs the CLI:

```
/usr/local/bin/kde-theme
```

---

# 🧩 Install via .deb (Recommended)

You can install the full application — **CLI + GUI + menu launcher + icon** — using the provided `.deb` package.

### Install:

```bash
sudo dpkg -i installer.deb
```

This installs:

| Component | Path |
|----------|------|
| CLI (`kde-theme`) | `/usr/bin/kde-theme` |
| GUI (`kde-theme-gui`) | `/usr/bin/kde-theme-gui` |
| GUI Python code | `/usr/lib/kde-theme-backup/kde_theme_gui.py` |
| Application launcher | `/usr/share/applications/kde-theme-backup.desktop` |
| App icon | `/usr/share/icons/hicolor/256x256/apps/kdethemebackup.png` |

### Run:

CLI:

```bash
kde-theme list
```

GUI:

```bash
kde-theme-gui
```

Or launch from the KDE Menu:

**KDE Theme Backup & Switcher**

---

# 📁 Backup Format

Backups are stored in:

```
~/kde-theme-backups/<name>/
~/kde-theme-backups/<name>.tar.gz
```

Backups include:

- plasma-org.kde.plasma.desktop-appletsrc  
- kdeglobals, plasmarc, kwinrc, kwinrulesrc  
- icons, wallpapers, schemes  
- Kvantum configs  
- Latte Dock configs  
- Panel/widget layout  
- Global Theme ID  

---

# 🧽 Uninstallation

```bash
sudo rm /usr/bin/kde-theme
sudo rm /usr/bin/kde-theme-gui
sudo rm -r /usr/lib/kde-theme-backup
sudo rm /usr/share/applications/kde-theme-backup.desktop
sudo rm /usr/share/icons/hicolor/256x256/apps/kdethemebackup.png
```

(Optional)
```bash
rm -r ~/kde-theme-backups
```

---
