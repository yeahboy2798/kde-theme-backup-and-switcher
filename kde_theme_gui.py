#!/usr/bin/env python3
import subprocess, sys
def ensure_pyqt():
    try:
        import PyQt6
        return
    except ImportError:
        print("PyQt6 not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyQt6"], check=True)
        print("PyQt6 installed. Please re-run the app.")
        sys.exit()

ensure_pyqt()


import os
import sys
import shutil
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QTextEdit,
    QMessageBox,
)
from PyQt6.QtCore import Qt

BACKUP_DIR = Path.home() / "kde-theme-backups"
KDE_THEME_CMD = "kde-theme"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDE Theme Backup & Switcher")
        self.resize(800, 500)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        # Top: backup name + button
        top_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Backup name (e.g. macosfull, win11-dark, default)")
        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)

        top_layout.addWidget(QLabel("New backup name:"))
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(backup_btn)

        main_layout.addLayout(top_layout)

        # Middle: list of backups + buttons
        mid_layout = QHBoxLayout()

        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(self.backup_list.SelectionMode.SingleSelection)

        buttons_layout = QVBoxLayout()
        restore_theme_btn = QPushButton("Restore Theme Only")
        restore_layout_btn = QPushButton("Restore Layout Only")
        restore_all_btn = QPushButton("Restore Theme + Layout")
        delete_btn = QPushButton("Delete Backup")
        refresh_btn = QPushButton("Refresh List")

        restore_theme_btn.clicked.connect(self.restore_theme)
        restore_layout_btn.clicked.connect(self.restore_layout)
        restore_all_btn.clicked.connect(self.restore_all)
        delete_btn.clicked.connect(self.delete_backup)
        refresh_btn.clicked.connect(self.load_backups)

        for b in [restore_theme_btn, restore_layout_btn, restore_all_btn, delete_btn, refresh_btn]:
            buttons_layout.addWidget(b)
        buttons_layout.addStretch()

        mid_layout.addWidget(self.backup_list, 3)
        mid_layout.addLayout(buttons_layout, 1)

        main_layout.addLayout(mid_layout)

        # Bottom: log output
        main_layout.addWidget(QLabel("Output / Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_layout.addWidget(self.log, 1)

        self.load_backups()

    # --------- helpers ---------

    def append_log(self, text: str):
        self.log.append(text)
        self.log.moveCursor(self.log.textCursor().MoveOperation.End)

    def ensure_cmd_available(self) -> bool:
        if shutil.which(KDE_THEME_CMD) is None:
            QMessageBox.critical(
                self,
                "kde-theme not found",
                f"Could not find '{KDE_THEME_CMD}' in PATH.\n\n"
                "Make sure you installed it with your install script "
                "and that /usr/local/bin is in your PATH.",
            )
            return False
        return True

    def selected_backup_name(self) -> str | None:
        item = self.backup_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No backup selected", "Please select a backup from the list.")
            return None
        return item.text()

    def run_cmd(self, args: list[str]):
        """Run kde-theme command and show output in log.
        We send a newline on stdin to satisfy any prompt (e.g. missing global theme),
        effectively choosing the default / 'skip' behaviour."""
        if not self.ensure_cmd_available():
            return

        self.append_log(f"$ {' '.join(args)}")
        try:
            # send a newline so interactive prompts don't hang the GUI
            result = subprocess.run(
                args,
                input="\n",
                capture_output=True,
                text=True,
            )
        except Exception as e:
            self.append_log(f"❌ Error running command: {e}")
            QMessageBox.critical(self, "Error", str(e))
            return

        if result.stdout:
            self.append_log(result.stdout.strip())
        if result.stderr:
            self.append_log(result.stderr.strip())

        if result.returncode != 0:
            self.append_log(f"❌ Command exited with status {result.returncode}")
            QMessageBox.warning(
                self,
                "Command failed",
                f"Command exited with status {result.returncode}.\nSee log for details.",
            )
        else:
            self.append_log("✅ Done.")

    # --------- actions ---------

    def load_backups(self):
        self.backup_list.clear()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if not BACKUP_DIR.exists():
            return

        backups = sorted(
            [p.name for p in BACKUP_DIR.iterdir() if p.is_dir()],
            key=str.lower,
        )
        self.backup_list.addItems(backups)
        self.append_log("🔄 Backup list updated.")

    def create_backup(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No name", "Please enter a backup name.")
            return

        # Basic name validation
        if any(c in name for c in " /\\:"):
            QMessageBox.warning(self, "Invalid name", "Backup name cannot contain spaces or / \\ :")
            return

        target_dir = BACKUP_DIR / name
        if target_dir.exists():
            ret = QMessageBox.question(
                self,
                "Overwrite?",
                f"A backup named '{name}' already exists.\n\n"
                "Do you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

        self.run_cmd([KDE_THEME_CMD, "backup", name])
        self.load_backups()

    def restore_theme(self):
        name = self.selected_backup_name()
        if not name:
            return
        self.run_cmd([KDE_THEME_CMD, "restore", name])

    def restore_layout(self):
        name = self.selected_backup_name()
        if not name:
            return
        ret = QMessageBox.question(
            self,
            "Restore layout?",
            "This will overwrite your current Plasma panels/widgets and Latte layout "
            f"with the layout from '{name}'.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.run_cmd([KDE_THEME_CMD, "restore-layout", name])

    def restore_all(self):
        name = self.selected_backup_name()
        if not name:
            return
        ret = QMessageBox.question(
            self,
            "Restore theme + layout?",
            "This will restore THEME and LAYOUT from the backup.\n\n"
            "Your current layout and theme may be overwritten.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.run_cmd([KDE_THEME_CMD, "restore-all", name])

    def delete_backup(self):
        name = self.selected_backup_name()
        if not name:
            return

        ret = QMessageBox.question(
            self,
            "Delete backup?",
            f"Delete backup '{name}' and its archive?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        dir_path = BACKUP_DIR / name
        tar_path = BACKUP_DIR / f"{name}.tar.gz"

        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
            if tar_path.exists():
                tar_path.unlink()
            self.append_log(f"🗑 Deleted backup '{name}'.")
        except Exception as e:
            QMessageBox.critical(self, "Delete error", str(e))
            self.append_log(f"❌ Error deleting backup '{name}': {e}")
            return

        self.load_backups()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
