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

BACKUP_DIR = Path.home() / "kde-theme-backups"
KDE_THEME_CMD = "kde-theme"

# Path to optional uninstaller script (to be installed with the app)
SCRIPT_DIR = Path(__file__).resolve().parent
UNINSTALLER_SCRIPT = SCRIPT_DIR / "uninstall-kde-theme.sh"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDE Theme Backup & Switcher")
        self.resize(900, 540)

        self.process: QProcess | None = None
        self._after_process = None  # optional callback(exit_code: int)

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

        # Log label + log area
        main_layout.addWidget(QLabel("Output / Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        main_layout.addWidget(self.log, 1)

        # Bottom: full-width progress bar + status label
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)  # indeterminate while visible
        self.progress.setVisible(False)

        self.status_label = QLabel("Idle.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.status_label)

        self.load_backups()

    # --------- helpers ---------

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
                "Make sure you installed it with your install script or .deb "
                "and that /usr/bin is in your PATH.",
            )
            return False
        return True

    def selected_backup_name(self) -> str | None:
        item = self.backup_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No backup selected", "Please select a backup from the list.")
            return None
        return item.text()

    # ---------- process management (async, non-blocking) ----------

    def _start_process(self, args: list[str], status_message: str | None = None, on_finished=None):
        if self.process is not None:
            QMessageBox.warning(
                self,
                "Already running",
                "A command is already running. Please wait for it to finish.",
            )
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

        program = args[0]
        arguments = args[1:]
        self.process.start(program, arguments)

        if not self.process.waitForStarted(5000):  # 5s to start
            self.append_log("❌ Failed to start process.")
            QMessageBox.critical(self, "Error", "Failed to start process.")
            self.set_busy(False, "Idle.")
            self.process = None
            self._after_process = None

    def _read_stdout(self):
        if self.process is None:
            return
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.append_log(data.strip())

    def _read_stderr(self):
        if self.process is None:
            return
        data = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log(data.strip())

    def _process_finished(self, exit_code: int, exit_status):
        if self.process is None:
            return

        if exit_code != 0:
            self.append_log(f"❌ Command exited with status {exit_code}")
            QMessageBox.warning(
                self,
                "Command failed",
                f"Command exited with status {exit_code}.\nSee log for details.",
            )
        else:
            self.append_log("✅ Done.")

        self.set_busy(False, "Idle.")

        cb = self._after_process
        self.process = None
        self._after_process = None

        if cb is not None:
            try:
                cb(exit_code)
            except Exception as e:
                self.append_log(f"❌ Error in callback: {e}")

    def run_cmd(self, args: list[str], status_message: str | None = None, on_finished=None):
        if not self.ensure_cmd_available():
            return
        self._start_process(args, status_message=status_message, on_finished=on_finished)

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

        def after_backup(exit_code: int):
            if exit_code == 0:
                self.load_backups()

        self.run_cmd(
            [KDE_THEME_CMD, "backup", name],
            status_message=f"Creating backup '{name}'…",
            on_finished=after_backup,
        )

    def restore_theme(self):
        name = self.selected_backup_name()
        if not name:
            return
        self.run_cmd(
            [KDE_THEME_CMD, "restore", name],
            status_message=f"Restoring theme from '{name}'…",
        )

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
        self.run_cmd(
            [KDE_THEME_CMD, "restore-layout", name],
            status_message=f"Restoring layout from '{name}'…",
        )

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
        self.run_cmd(
            [KDE_THEME_CMD, "restore-all", name],
            status_message=f"Restoring theme + layout from '{name}'…",
        )

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

    def import_backup(self):
        start_dir = str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import backup archive",
            start_dir,
            "KDE theme backups (*.tar.gz);;All files (*)",
        )
        if not file_path:
            return

        file_path = Path(file_path)
        name = file_path.stem

        ret = QMessageBox.question(
            self,
            "Import backup?",
            f"Import backup from archive:\n{file_path}\n\n"
            f"It will appear as '{name}' in your backup list.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        target_dir = BACKUP_DIR / name
        if target_dir.exists():
            ret2 = QMessageBox.question(
                self,
                "Overwrite existing backup?",
                f"A backup directory '{name}' already exists in {BACKUP_DIR}.\n\n"
                "Do you want to overwrite its contents with the imported archive?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ret2 != QMessageBox.StandardButton.Yes:
                return
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear existing backup: {e}")
                return

        def after_import(exit_code: int):
            if exit_code == 0:
                try:
                    dest_tar = BACKUP_DIR / file_path.name
                    if file_path.resolve() != dest_tar.resolve():
                        shutil.copy2(file_path, dest_tar)
                except Exception as e:
                    self.append_log(f"⚠️ Could not copy archive into backup dir: {e}")
                self.append_log(f"📥 Imported backup archive '{file_path.name}' as '{name}'.")
                self.load_backups()

        self._start_process(
            ["tar", "-xzf", str(file_path), "-C", str(BACKUP_DIR)],
            status_message=f"Importing backup from '{file_path.name}'…",
            on_finished=after_import,
        )

    def uninstall_app(self):
        if not UNINSTALLER_SCRIPT.exists():
            QMessageBox.critical(
                self,
                "Uninstaller not found",
                f"Could not find uninstaller script at:\n{UNINSTALLER_SCRIPT}\n\n"
                "If you installed via a .deb or package manager, you can also run:\n"
                "  sudo dpkg -r kde-theme-backup\n"
                "or:\n"
                "  sudo kde-theme uninstall (if supported by your version).",
            )
            return

        ret = QMessageBox.question(
            self,
            "Uninstall application?",
            "This will remove the KDE Theme Backup CLI and GUI from this system.\n\n"
            "You may need to enter your password. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        pkexec_path = shutil.which("pkexec")
        if pkexec_path is None:
            QMessageBox.warning(
                self,
                "pkexec not found",
                "Could not find 'pkexec' for graphical privilege elevation.\n"
                "The uninstaller may not work from the GUI.\n\n"
                "You can run this manually in a terminal instead:\n"
                f"  sudo {UNINSTALLER_SCRIPT}",
            )
            return

        def after_uninstall(exit_code: int):
            if exit_code == 0:
                self.append_log("✅ Uninstall complete.")
                QMessageBox.information(
                    self,
                    "Uninstalled",
                    "KDE Theme Backup & Switcher has been uninstalled.\n"
                    "This window will now close.",
                )
                QApplication.instance().quit()

        self._start_process(
            [pkexec_path, str(UNINSTALLER_SCRIPT)],
            status_message="Uninstalling application…",
            on_finished=after_uninstall,
        )


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
