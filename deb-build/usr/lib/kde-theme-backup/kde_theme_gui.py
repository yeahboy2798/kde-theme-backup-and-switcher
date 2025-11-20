#!/usr/bin/env python3
import os
import sys
import shutil
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
    QProgressBar,
)
from PyQt6.QtCore import Qt, QProcess

BACKUP_DIR = Path.home() / "kde-theme-backups"
KDE_THEME_CMD = "kde-theme"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDE Theme Backup & Switcher")
        self.resize(800, 520)

        self.process: QProcess | None = None

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
        self.btn_restore_theme = QPushButton("Restore Theme Only")
        self.btn_restore_layout = QPushButton("Restore Layout Only")
        self.btn_restore_all = QPushButton("Restore Theme + Layout")
        self.btn_delete = QPushButton("Delete Backup")
        self.btn_refresh = QPushButton("Refresh List")

        self.btn_restore_theme.clicked.connect(self.restore_theme)
        self.btn_restore_layout.clicked.connect(self.restore_layout)
        self.btn_restore_all.clicked.connect(self.restore_all)
        self.btn_delete.clicked.connect(self.delete_backup)
        self.btn_refresh.clicked.connect(self.load_backups)

        for b in [
            self.btn_restore_theme,
            self.btn_restore_layout,
            self.btn_restore_all,
            self.btn_delete,
            self.btn_refresh,
        ]:
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

        # Busy spinner / progress bar (indeterminate)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 0,0 = busy / indeterminate
        self.progress.setTextVisible(False)
        self.progress.hide()
        main_layout.addWidget(self.progress)

        # Status text
        self.status_label = QLabel("Idle")
        main_layout.addWidget(self.status_label)

        self.load_backups()

    # --------- helpers ---------

    def set_busy(self, busy: bool, message: str | None = None):
        if busy:
            self.progress.show()
            self.status_label.setText(message or "Working…")
        else:
            self.progress.hide()
            self.status_label.setText("Idle")

    def set_buttons_enabled(self, enabled: bool):
        self.name_edit.setEnabled(enabled)
        self.backup_list.setEnabled(enabled)
        for btn in [
            self.btn_restore_theme,
            self.btn_restore_layout,
            self.btn_restore_all,
            self.btn_delete,
            self.btn_refresh,
        ]:
            btn.setEnabled(enabled)

    def append_log(self, text: str):
        if not text:
            return
        self.log.append(text)
        self.log.moveCursor(self.log.textCursor().MoveOperation.End)

    def ensure_cmd_available(self) -> bool:
        if shutil.which(KDE_THEME_CMD) is None:
            QMessageBox.critical(
                self,
                "kde-theme not found",
                f"Could not find '{KDE_THEME_CMD}' in PATH.\n\n"
                "Make sure you installed it (kde-theme CLI) "
                "and that /usr/bin or /usr/local/bin is in your PATH.",
            )
            return False
        return True

    def selected_backup_name(self) -> str | None:
        item = self.backup_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No backup selected", "Please select a backup from the list.")
            return None
        return item.text()

    # --------- QProcess-based command runner ---------

    def run_cmd(self, args: list[str], busy_message: str = "Working…"):
        if not self.ensure_cmd_available():
            return

        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(
                self,
                "Command running",
                "Another operation is still running. Please wait for it to finish.",
            )
            return

        self.append_log(f"$ {' '.join(args)}")

        self.process = QProcess(self)
        self.process.setProgram(args[0])
        self.process.setArguments(args[1:])
        # Merge stdout and stderr
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.finished.connect(self.on_process_finished)

        self.set_buttons_enabled(False)
        self.set_busy(True, busy_message)
        self.process.start()

        # Send a newline so any interactive prompts (e.g. theme missing) don't block forever
        try:
            self.process.write(b"\n")
            self.process.closeWriteChannel()
        except Exception:
            pass

    def on_ready_read(self):
        if self.process is None:
            return
        try:
            data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        except Exception:
            data = ""
        if data:
            for line in data.rstrip().splitlines():
                self.append_log(line)

    def on_process_finished(self, exit_code: int, _status):
        self.set_buttons_enabled(True)
        self.set_busy(False)
        if exit_code == 0:
            self.append_log("✅ Done.")
        else:
            self.append_log(f"❌ Command exited with status {exit_code}")
            QMessageBox.warning(
                self,
                "Command failed",
                f"Command exited with status {exit_code}.\nSee log for details.",
            )
        self.process = None
        # refresh list in case backups changed
        self.load_backups()

    # --------- actions ---------

    def load_backups(self):
        self.backup_list.clear()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backups = sorted(
            [p.name for p in BACKUP_DIR.iterdir() if p.is_dir()],
            key=str.lower,
        )
        self.backup_list.addItems(backups)

    def create_backup(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No name", "Please enter a backup name.")
            return

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

        self.run_cmd([KDE_THEME_CMD, "backup", name], busy_message=f"Creating backup '{name}'…")

    def restore_theme(self):
        name = self.selected_backup_name()
        if not name:
            return
        self.run_cmd([KDE_THEME_CMD, "restore", name], busy_message=f"Restoring theme from '{name}'…")

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
        self.run_cmd([KDE_THEME_CMD, "restore-layout", name], busy_message=f"Restoring layout from '{name}'…")

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
        self.run_cmd([KDE_THEME_CMD, "restore-all", name], busy_message=f"Restoring theme + layout from '{name}'…")

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
                import shutil as _shutil
                _shutil.rmtree(dir_path)
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
