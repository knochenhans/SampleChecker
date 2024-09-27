import os
import subprocess
import sys

from PySide6.QtCore import QMimeDatabase, QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DirectoryTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["", "Files"])
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cellClicked.connect(self.play_file)
        self.cellDoubleClicked.connect(self.open_file_explorer)

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.mime_db = QMimeDatabase()

        # Set the icon column width to a fixed size
        self.setColumnWidth(0, 32)  # Adjust the width as needed

        # Set up context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        # Set up key press event
        self.keyPressEvent = self.handle_key_press

        # Hide grid lines
        self.setShowGrid(False)

    def update_table(self, directory):
        if os.path.isdir(directory):
            files = sorted(os.listdir(directory))  # Sort files by name
            self.setRowCount(len(files) + 1)  # Add one for the ".." entry

            # Add ".." entry to go to the parent directory
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            icon_item = QTableWidgetItem()
            icon_item.setIcon(icon)
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(0, 0, icon_item)

            item = QTableWidgetItem("..")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.UserRole, os.path.dirname(directory))
            self.setItem(0, 1, item)

            for row, file_name in enumerate(files, start=1):
                file_path = os.path.join(directory, file_name)

                # Set file or directory icon using mime type
                mime_type = self.mime_db.mimeTypeForFile(file_path)
                icon = QIcon.fromTheme(mime_type.iconName())
                if icon.isNull():
                    if os.path.isfile(file_path):
                        if mime_type.name().startswith("audio/"):
                            icon = self.style().standardIcon(
                                QStyle.StandardPixmap.SP_MediaPlay
                            )
                        elif mime_type.name().startswith("video/"):
                            icon = self.style().standardIcon(
                                QStyle.StandardPixmap.SP_MediaPlay
                            )
                        elif mime_type.name().startswith("image/"):
                            icon = self.style().standardIcon(
                                QStyle.StandardPixmap.SP_FileIcon
                            )
                        else:
                            icon = self.style().standardIcon(
                                QStyle.StandardPixmap.SP_FileIcon
                            )
                    else:
                        icon = self.style().standardIcon(
                            QStyle.StandardPixmap.SP_DirIcon
                        )
                icon_item = QTableWidgetItem()
                icon_item.setIcon(icon)
                icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.setItem(row, 0, icon_item)

                # Set file name
                item = QTableWidgetItem(file_name)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(
                    Qt.ItemDataRole.UserRole, file_path
                )  # Save full path as user data
                self.setItem(row, 1, item)
        else:
            self.setRowCount(0)

    def play_file(self, row, column):
        item = self.item(row, 1)  # Get the file name item
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path:
                self.media_player.setSource(file_path)
                self.media_player.play()

    def open_file_explorer(self, row, column):
        item = self.item(row, 1)  # Get the file name item
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isdir(file_path):
                self.update_table(file_path)
            # elif file_path:
            #     if sys.platform == "win32":
            #         os.startfile(file_path)
            #     elif sys.platform == "darwin":
            #         subprocess.run(["open", "-R", file_path])
            #     else:
            #         subprocess.run(["xdg-open", os.path.dirname(file_path)])

    def open_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        action = menu.exec(self.viewport().mapToGlobal(position))
        if action == delete_action:
            self.delete_file()

    def delete_file(self):
        selected_items = self.selectedItems()
        if selected_items:
            for item in selected_items:
                if item.column() == 1:
                    file_path = item.data(Qt.ItemDataRole.UserRole)
                    if file_path and os.path.isfile(file_path):
                        os.remove(file_path)
                        self.update_table(os.path.dirname(file_path))
                    elif file_path and os.path.isdir(file_path):
                        QMessageBox.warning(
                            self,
                            "Delete Error",
                            f"'{file_path}' is a directory and cannot be deleted.",
                        )

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_file()
        else:
            super().keyPressEvent(event)


class DirectoryDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sample Checker")
        self.setGeometry(100, 100, 1024, 800)

        self.settings = QSettings("Strukt Studio", "SampleChecker")

        self.main_layout = QVBoxLayout()

        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText(
            "Enter directory path or click 'Browse' to select"
        )
        last_directory = self.settings.value("last_directory", os.path.expanduser("~"))

        if isinstance(last_directory, str):
            self.path_edit.setText(last_directory)
        self.main_layout.addWidget(self.path_edit)

        self.button_layout = QHBoxLayout()

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_directory)
        self.button_layout.addWidget(self.browse_button)

        self.open_button = QPushButton("File Explorer", self)
        self.open_button.clicked.connect(self.open_directory)
        self.button_layout.addWidget(self.open_button)

        self.main_layout.addLayout(self.button_layout)

        self.table_widget = DirectoryTable(self)
        self.main_layout.addWidget(self.table_widget)

        self.path_edit.returnPressed.connect(self.update_table)

        self.setLayout(self.main_layout)
        self.update_table()

        # Set focus to the path_edit
        self.browse_button.clearFocus()

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory", os.path.expanduser("~")
        )
        if directory:
            self.path_edit.setText(directory)
            self.settings.setValue("last_directory", directory)
            self.update_table()

    def open_directory(self):
        directory = self.path_edit.text()
        if directory and os.path.isdir(directory):
            if sys.platform == "win32":
                os.startfile(directory)
            elif sys.platform == "darwin":
                subprocess.run(["open", directory])
            else:
                subprocess.run(["xdg-open", directory])

    def update_table(self):
        directory = self.path_edit.text()
        self.table_widget.update_table(directory)
        self.settings.setValue("last_directory", directory)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DirectoryDialog()
    dialog.show()
    sys.exit(app.exec())
