#!/usr/bin/env python3
import subprocess
import sys
import os
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
    QFileDialog,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QPalette, QColor

BACKUP_DIR = Path.home() / "kde-theme-backups"
KDE_THEME_CMD = "kde-theme"

SCRIPT_DIR = Path(__file__).resolve().parent
UNINSTALLER_SCRIPT = SCRIPT_DIR / "uninstall-kde-theme.sh"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDE Theme Backup & Switcher")
        self.resize(900, 540)

        self.process: QProcess | None = None
        self._after_process = None

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        central.setLayout(main_layout)

        # Top: backup name + button
        top_layout = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            "Backup name (e.g. macosfull, win11-dark, default)"
        )

        # Placeholder/text colours tuned for dark theme:
        pal = self.name_edit.palette()
        pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#bfbfbf"))  # soft gray
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.name_edit.setPalette(pal)

        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)

        top_layout.addWidget(QLabel("New backup name:"))
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(backup_btn)

        main_layout.addLayout(top_layout)

        # Middle: backup list + controls
        mid_layout = QHBoxLayout()

        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(
            self.backup_list.SelectionMode.SingleSelection
        )

        buttons_layout = QVBoxLayout()
        restore_theme_btn = QPushButton("Restore Theme Only")
        restore_layout_btn = QPushButton("Restore Layout Only")
        restore_all_btn = QPushButton("Restore Theme + Layout")
        delete_btn = QPushButton("Delete Backup")
        refresh_btn = QPushButton("Refresh List")
        import_btn = QPushButton("Import Backup Archive…")
        uninstall_btn = QPushButton("Uninstall App…")

        restore_theme_btn.clicked.connect(self.restore_theme)
        restore_layout_btn.clicked.connect(self.restore_layout)
        restore_all_btn.clicked.connect(self.restore_all)
        delete_btn.clicked.connect(self.delete_backup)
        refresh_btn.clicked.connect(self.load_backups)
        import_btn.clicked.connect(self.import_backup)
        uninstall_btn.clicked.connect(self.uninstall_app)

        self.control_buttons = [
            restore_theme_btn,
            restore_layout_btn,
            restore_all_btn,
            delete_btn,
            refresh_btn,
            import_btn,
            uninstall_btn,
            backup_btn,
        ]

        for b in [
            restore_theme_btn,
            restore_layout_btn,
            restore_all_btn,
            delete_btn,
            refresh_btn,
            import_btn,
            uninstall_btn,
        ]:
            buttons_layout.addWidget(b)
        buttons_layout.addStretch()

        mid_layout.addWidget(self.backup_list, 3)
        mid_layout.addLayout(buttons_layout, 1)

        main_layout.addLayout(mid_layout)

        # Log area
        main_layout.addWidget(QLabel("Output / Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_layout.addWidget(self.log, 1)

        # Full-width progress bar + status
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setVisible(False)

        self.status_label = QLabel("Idle.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status_label)

        self.load_backups()

    # ---- Helpers ----
    def set_busy(self, busy: bool, message: str | None = None):
        if busy:
            self.progress.setVisible(True)
            self.status_label.setText(message or "Working…")
        else:
            self.progress.setVisible(False)
            self.status_label.setText(message or "Idle.")

        for b in self.control_buttons:
            b.setDisabled(busy)
        self.backup_list.setDisabled(busy)
        self.name_edit.setDisabled(busy)

    def append_log(self, text: str):
        if text:
            self.log.append(text)
            self.log.moveCursor(self.log.textCursor().MoveOperation.End)

    def ensure_cmd_available(self) -> bool:
        if shutil.which(KDE_THEME_CMD) is None:
            QMessageBox.critical(
                self,
                "kde-theme not found",
                f"Could not find '{KDE_THEME_CMD}' in PATH.\n"
                "Install via .deb or installer script.",
            )
            return False
        return True

    def selected_backup_name(self) -> str | None:
        item = self.backup_list.currentItem()
        if not item:
            QMessageBox.warning(
                self, "No backup selected", "Select a backup from the list."
            )
            return None
        return item.text()

    # ---- QProcess management ----
    def _start_process(self, args, status_message=None, on_finished=None):
        if self.process:
            QMessageBox.warning(self, "Busy", "A task is already running.")
            return
        if not args:
            return

        self.set_busy(True, status_message or f"Running: {' '.join(args)}")
        self.append_log(f"$ {' '.join(args)}")

        self.process = QProcess(self)
        self._after_process = on_finished

        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._process_finished)

        self.process.start(args[0], args[1:])
        if not self.process.waitForStarted(5000):
            self.append_log("❌ Failed to start process.")
            QMessageBox.critical(self, "Error", "Failed to start command.")
            self.set_busy(False)
            self.process = None
            self._after_process = None

    def _read_stdout(self):
        if self.process:
            out = self.process.readAllStandardOutput().data().decode(errors="ignore")
            self.append_log(out.strip())

    def _read_stderr(self):
        if self.process:
            err = self.process.readAllStandardError().data().decode(errors="ignore")
            self.append_log(err.strip())

    def _process_finished(self, exit_code, _):
        if exit_code != 0:
            self.append_log(f"❌ Command exited with {exit_code}")
            QMessageBox.warning(self, "Failed", "Command failed. See log.")
        else:
            self.append_log("✅ Done.")

        self.set_busy(False)

        cb = self._after_process
        self.process = None
        self._after_process = None
        if cb:
            cb(exit_code)

    def run_cmd(self, args, status_message=None, on_finished=None):
        if self.ensure_cmd_available():
            self._start_process(args, status_message, on_finished)

    # ---- Main actions ----
    def load_backups(self):
        self.backup_list.clear()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backups = sorted(
            [p.name for p in BACKUP_DIR.iterdir() if p.is_dir()], key=str.lower
        )
        self.backup_list.addItems(backups)
        self.append_log("🔄 Backup list updated.")

    def create_backup(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No name", "Enter a backup name.")
            return
        if any(c in name for c in " /\\:"):
            QMessageBox.warning(self, "Invalid name", "No spaces or / : \\ allowed.")
            return

        def after_backup(code):
            if code == 0:
                self.load_backups()

        self.run_cmd(
            [KDE_THEME_CMD, "backup", name], f"Creating backup '{name}'…", after_backup
        )

    def restore_theme(self):
        name = self.selected_backup_name()
        if name:
            self.run_cmd([KDE_THEME_CMD, "restore", name], f"Restoring theme '{name}'…")

    def restore_layout(self):
        name = self.selected_backup_name()
        if not name:
            return
        if (
            QMessageBox.question(
                self,
                "Restore layout?",
                f"Overwrite your current layout with '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.run_cmd(
            [KDE_THEME_CMD, "restore-layout", name], f"Restoring layout '{name}'…"
        )

    def restore_all(self):
        name = self.selected_backup_name()
        if not name:
            return
        if (
            QMessageBox.question(
                self,
                "Restore all?",
                f"Restore THEME + LAYOUT from '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.run_cmd(
            [KDE_THEME_CMD, "restore-all", name], f"Restoring theme + layout '{name}'…"
        )

    def delete_backup(self):
        name = self.selected_backup_name()
        if not name:
            return
        if (
            QMessageBox.question(
                self,
                "Delete backup?",
                f"Delete '{name}' permanently?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        shutil.rmtree(BACKUP_DIR / name, ignore_errors=True)
        tar = BACKUP_DIR / f"{name}.tar.gz"
        if tar.exists():
            tar.unlink()
        self.append_log(f"🗑 Deleted '{name}'.")
        self.load_backups()

    def import_backup(self):
        start_dir = str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import backup archive",
            start_dir,
            "KDE Backups (*.tar.gz);;All files (*)",
        )
        if not file_path:
            return

        file_path = Path(file_path)
        name = file_path.stem

        if (
            QMessageBox.question(
                self,
                "Import?",
                f"Import '{file_path.name}' as '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        target = BACKUP_DIR / name
        if target.exists():
            shutil.rmtree(target)

        def after_import(code):
            if code == 0:
                try:
                    shutil.copy2(file_path, BACKUP_DIR / file_path.name)
                except Exception:
                    pass
                self.append_log(f"📥 Imported '{file_path.name}'.")
                self.load_backups()

        self.run_cmd(
            ["tar", "-xzf", str(file_path), "-C", str(BACKUP_DIR)],
            f"Importing '{file_path.name}'…",
            after_import,
        )

    def uninstall_app(self):
        if not UNINSTALLER_SCRIPT.exists():
            QMessageBox.critical(
                self, "Missing", f"Uninstaller not found:\n{UNINSTALLER_SCRIPT}"
            )
            return

        if (
            QMessageBox.question(
                self,
                "Uninstall?",
                "Remove KDE Theme Backup + GUI?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        pkexec = shutil.which("pkexec")
        if not pkexec:
            QMessageBox.warning(
                self, "pkexec missing", f"Run manually:\n  sudo {UNINSTALLER_SCRIPT}"
            )
            return

        def after_uninstall(code):
            if code == 0:
                QMessageBox.information(self, "Done", "Uninstalled.")
                QApplication.instance().quit()

        self.run_cmd(
            [pkexec, str(UNINSTALLER_SCRIPT)], "Uninstalling…", after_uninstall
        )


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
