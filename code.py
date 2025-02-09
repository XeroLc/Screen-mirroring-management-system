import sys
import os
from PyQt6.QtCore import Qt, QUrl, QPoint
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QFrame,
    QLabel,
    QVBoxLayout,
    QComboBox,
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QInputDialog
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

CONFIG_FILE = "config.ini"


def read_urls_from_config():
    """从配置文件中读取并去重网址"""
    urls = []
    if os.path.exists(CONFIG_FILE):
        seen = set()
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            for line in file:
                url = line.strip()
                if url and url not in seen:
                    urls.append(url)
                    seen.add(url)
    return urls


def write_url_to_config(url):
    """将新网址写入配置文件（不重复）"""
    urls = read_urls_from_config()
    if url not in urls:
        with open(CONFIG_FILE, "a", encoding="utf-8") as file:
            file.write(url + "\n")


class DragResizeWidget(QFrame):
    """可拖拽和调整大小的窗口基类"""

    def __init__(self, parent=None, border_style="1px solid black"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"background: white; border: {border_style};")
        self.resize(800, 600)
        self.dragging = False
        self.resizing = False
        self.drag_position = QPoint()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_on_border(event.pos()):
                self.resizing = True
            else:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            delta = event.globalPosition().toPoint() - self.drag_position
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.drag_position = event.globalPosition().toPoint()
        elif self.resizing:
            new_width = max(100, event.pos().x())
            new_height = max(100, event.pos().y())
            self.resize(new_width, new_height)
            self.update_content_geometry()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False
        self.resizing = False
        event.accept()

    def is_on_border(self, pos):
        """检测是否在右下角边框区域"""
        margin = 10
        return (pos.x() >= self.width() - margin and 
                pos.y() >= self.height() - margin)

    def update_content_geometry(self):
        """更新内容布局，子类必须实现"""
        raise NotImplementedError


class BrowserWidget(DragResizeWidget):
    """浏览器窗口"""

    def __init__(self, parent=None, url=None):
        super().__init__(parent, border_style="0px solid black")
        self.browser = QWebEngineView(self)
        self.browser.setUrl(QUrl(url) if url else QUrl("https://www.google.com"))
        self.update_content_geometry()

    def update_content_geometry(self):
        self.browser.setGeometry(5, 5, self.width()-10, self.height()-10)


class ImageWidget(DragResizeWidget):
    """图片窗口"""

    def __init__(self, parent=None, image_path=None):
        super().__init__(parent, border_style="1px solid black")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnBottomHint)
        self.label = QLabel(self)
        self.label.setScaledContents(True)
        if image_path:
            self.load_image(image_path)
        self.update_content_geometry()

    def load_image(self, path):
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                raise ValueError("Invalid image file")
            self.label.setPixmap(pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")

    def update_content_geometry(self):
        self.label.setGeometry(5, 5, self.width()-10, self.height()-10)


class VideoWidget(DragResizeWidget):
    """视频窗口"""

    def __init__(self, parent=None, video_path=None):
        super().__init__(parent, border_style="1px solid black")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnBottomHint)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.video_widget.lower()
        self.video_widget.setGeometry(5, 5, self.width()-10, self.height()-10)
        
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self.handle_error)
        
        if video_path:
            self.load_video(video_path)
            
        self.player.mediaStatusChanged.connect(self.handle_media_status)

    def load_video(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def handle_error(self, error, error_msg):
        print(f"Media error: {error_msg}")

    def update_content_geometry(self):
        self.video_widget.setGeometry(5, 5, self.width()-10, self.height()-10)

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)


class UrlSelectionDialog(QDialog):
    """网址选择对话框（优化去重逻辑）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("选择网址")
        self.setFixedSize(300, 200)
        self.urls = read_urls_from_config()
        
        self.url_combobox = QComboBox()
        self.url_combobox.addItems(self.urls)
        
        self.add_button = QPushButton("添加网址")
        self.add_button.clicked.connect(self.add_url)
        
        layout = QVBoxLayout()
        layout.addWidget(self.url_combobox)
        layout.addWidget(self.add_button)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

    def add_url(self):
        new_url, ok = QInputDialog.getText(self, "输入网址", "请输入网址:")
        if ok and new_url:
            write_url_to_config(new_url)
            if new_url not in self.urls:
                self.urls.append(new_url)
                self.url_combobox.addItem(new_url)


class FullScreenApp(QMainWindow):
    """主应用（优化初始化逻辑）"""

    def __init__(self):
        super().__init__()
        self.setup_window()
        self.media_window = self.setup_media()
        self.browser_window = self.setup_browser()
        self.adjust_window_stack()

    def setup_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()

    def setup_media(self):
        file_filter = "Media Files (*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mkv)"
        path, _ = QFileDialog.getOpenFileName(None, "选择背景文件", "", file_filter)
        if not path:
            return None
            
        ext = os.path.splitext(path)[1].lower()
        if ext in {".png", ".jpg", ".jpeg", ".bmp"}:
            widget = ImageWidget(self, path)
        elif ext in {".mp4", ".avi", ".mkv"}:
            widget = VideoWidget(self, path)
        else:
            return None
            
        widget.move(50, 50)
        widget.show()
        return widget

    def setup_browser(self):
        dialog = UrlSelectionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
            
        url = dialog.url_combobox.currentText()
        browser = BrowserWidget(self, url)
        browser.move(150, 150)
        browser.show()
        return browser

    def adjust_window_stack(self):
        if self.media_window and self.browser_window:
            self.media_window.stackUnder(self.browser_window)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F12:
            self.close()
        elif event.key() == Qt.Key.Key_F5 and self.browser_window:
            self.browser_window.browser.reload()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FullScreenApp()
    window.show()
    sys.exit(app.exec())
