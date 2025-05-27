# main.py
import json
import os
import re
import shutil
import sys
import webbrowser
from datetime import datetime

import qdarktheme
import send2trash  # pip install send2trash
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

# Importy z naszych modułów
import config_manager
import gallery_generator
import scanner_logic


# --- Klasy ScannerWorker i GalleryWorker pozostają bez zmian ---
class ScannerWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, root_folder):
        super().__init__()
        self.root_folder = root_folder
        self.is_cancelled = False

    def run(self):
        try:
            scanner_logic.start_scanning(self.root_folder, self.emit_progress)
        except Exception as e:
            self.progress_signal.emit(f"Wystąpił krytyczny błąd skanowania: {e}")
        finally:
            if not self.is_cancelled:
                self.finished_signal.emit()

    def emit_progress(self, message):
        if not self.is_cancelled:
            self.progress_signal.emit(message)

    def cancel(self):
        self.is_cancelled = True
        self.progress_signal.emit("Anulowano skanowanie.")


class GalleryWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)  # Emits path to root HTML or None if failed

    def __init__(self, scanned_root_path, gallery_cache_root):
        super().__init__()
        self.scanned_root_path = scanned_root_path
        self.gallery_cache_root = gallery_cache_root
        self.is_cancelled = False

    def run(self):
        root_html_path = None
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.join(script_dir, "templates")

            if not os.path.isdir(template_dir):
                alt_template_dir = "templates"
                if os.path.isdir(alt_template_dir):
                    template_dir = alt_template_dir
                else:
                    self.progress_signal.emit(
                        f"Błąd krytyczny: Nie znaleziono folderu szablonów ('templates') w {script_dir} ani w bieżącym katalogu."
                    )
                    self.finished_signal.emit(None)
                    return

            env = gallery_generator.Environment(
                loader=gallery_generator.FileSystemLoader(template_dir)
            )

            sanitized_folder_name = gallery_generator.sanitize_path_for_foldername(
                self.scanned_root_path
            )
            gallery_output_base_path = os.path.join(
                self.gallery_cache_root, sanitized_folder_name
            )
            os.makedirs(gallery_output_base_path, exist_ok=True)

            css_src_path = os.path.join(template_dir, "gallery_styles.css")
            css_dest_path = os.path.join(gallery_output_base_path, "gallery_styles.css")
            if os.path.exists(css_src_path):
                shutil.copy2(css_src_path, css_dest_path)
            else:
                self.progress_signal.emit(
                    f"Ostrzeżenie: Plik gallery_styles.css nie znaleziony w {template_dir}"
                )

            for dirpath, _, filenames in os.walk(self.scanned_root_path):
                if self.is_cancelled:
                    self.progress_signal.emit("Anulowano generowanie galerii.")
                    break
                if "index.json" in filenames:
                    index_json_file = os.path.join(dirpath, "index.json")
                    generated_html = gallery_generator.process_single_index_json(
                        index_json_file,
                        self.scanned_root_path,
                        gallery_output_base_path,
                        env,
                        self.emit_progress,
                    )
                    if dirpath == self.scanned_root_path and generated_html:
                        root_html_path = generated_html

            if not self.is_cancelled:
                if root_html_path:
                    self.progress_signal.emit(
                        f"Generowanie galerii zakończone. Główny plik: {root_html_path}"
                    )
                else:
                    self.progress_signal.emit(
                        "Nie udało się wygenerować głównego pliku galerii lub brak index.json w folderze głównym."
                    )

        except Exception as e:
            self.progress_signal.emit(
                f"Wystąpił krytyczny błąd podczas generowania galerii: {e}"
            )
            import traceback

            self.progress_signal.emit(traceback.format_exc())
        finally:
            if not self.is_cancelled:
                self.finished_signal.emit(root_html_path)

    def emit_progress(self, message):
        if not self.is_cancelled:
            self.progress_signal.emit(message)

    def cancel(self):
        self.is_cancelled = True
        self.progress_signal.emit("Próba anulowania generowania galerii.")


# Niestandardowa strona QWebEnginePage do obsługi linków
class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        """Obsługuje żądania nawigacji w przeglądarce.

        Args:
            url: URL do którego nastąpi nawigacja
            type: Typ nawigacji (QWebEnginePage.NavigationTypeLinkClicked)
            isMainFrame: True jeśli nawigacja jest dla głównej ramki
        """
        scheme = url.scheme()

        # Jeśli to link do lokalnego pliku HTML (nasza galeria)
        if scheme == "file" and url.path().endswith(".html"):
            return super().acceptNavigationRequest(url, type, isMainFrame)
        elif scheme == "file":  # Inne pliki lokalne (np. archiwa)
            QDesktopServices.openUrl(url)
            return False
        elif scheme in ["http", "https"]:
            QDesktopServices.openUrl(url)
            return False

        return super().acceptNavigationRequest(url, type, isMainFrame)


class MainWindow(QMainWindow):
    GALLERY_CACHE_DIR = "_gallery_cache"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skaner Folderów i Kreator Galerii")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        self.current_work_directory = config_manager.get_work_directory()
        self.scanner_thread = None
        self.gallery_thread = None
        self.current_gallery_root_html = None

        # DEBUGGING
        print(f"🔍 INIT - current_work_directory: {self.current_work_directory}")

        os.makedirs(self.GALLERY_CACHE_DIR, exist_ok=True)
        self.init_ui()
        self.update_status_label()
        self.update_gallery_buttons_state()
        self.setup_theme_menu()
        self.setup_learning_bridge()

        if self.current_work_directory:
            print(f"🔍 INIT - Sprawdzanie galerii dla: {self.current_work_directory}")
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            if self.current_gallery_root_html and os.path.exists(
                self.current_gallery_root_html
            ):
                self.show_gallery_in_app()
            # TUTAJ ZAWSZE WYWOŁAJ AKTUALIZACJĘ STATYSTYK
            print(f"🔍 INIT - Wywołuję update_folder_stats()")
            self.update_folder_stats()
            # Sprawdź oczekujące dopasowania po załadowaniu galerii
            QTimer.singleShot(1000, self.check_for_learning_matches)

    def setup_theme_menu(self):
        """Dodaje menu przełączania motywów."""
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("Motyw")

        dark_action = theme_menu.addAction("Ciemny")
        light_action = theme_menu.addAction("Jasny")

        dark_action.triggered.connect(lambda: self.change_theme("dark"))
        light_action.triggered.connect(lambda: self.change_theme("light"))

    def change_theme(self, theme):
        """Zmienia motyw aplikacji."""
        if theme not in ["dark", "light"]:
            theme = "dark"  # Domyślny motyw
        QApplication.instance().setStyleSheet(qdarktheme.load_stylesheet(theme))
        config_manager.set_config_value("ui.theme", theme)

    def init_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)

        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Folder roboczy: Brak")
        folder_layout.addWidget(self.folder_label, 1)

        self.select_folder_button = QPushButton("📁 Wybierz Folder")
        self.select_folder_button.setStyleSheet(
            """
            QPushButton {
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """
        )
        self.select_folder_button.clicked.connect(self.select_work_directory)
        folder_layout.addWidget(self.select_folder_button)
        controls_layout.addLayout(folder_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: #3daee9;
            }
        """
        )
        controls_layout.addWidget(self.progress_bar)

        action_layout = QHBoxLayout()

        self.start_scan_button = QPushButton("🔍 Skanuj Foldery")
        self.start_scan_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """
        )
        self.start_scan_button.clicked.connect(self.start_scan)
        action_layout.addWidget(self.start_scan_button)

        self.rebuild_gallery_button = QPushButton("🔄 Przebuduj Galerię")
        self.rebuild_gallery_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """
        )
        self.rebuild_gallery_button.clicked.connect(lambda: self.rebuild_gallery(True))
        action_layout.addWidget(self.rebuild_gallery_button)

        self.open_gallery_button = QPushButton("👁️ Pokaż Galerię")
        self.open_gallery_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """
        )
        self.open_gallery_button.clicked.connect(self.show_gallery_in_app)
        action_layout.addWidget(self.open_gallery_button)

        self.clear_gallery_cache_button = QPushButton("🗑️ Wyczyść Cache")
        self.clear_gallery_cache_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c62d42;
            }
        """
        )
        self.clear_gallery_cache_button.clicked.connect(
            self.clear_current_gallery_cache
        )
        action_layout.addWidget(self.clear_gallery_cache_button)

        self.cancel_button = QPushButton("❌ Anuluj")
        self.cancel_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """
        )
        self.cancel_button.clicked.connect(self.cancel_operations)
        action_layout.addWidget(self.cancel_button)

        controls_layout.addLayout(action_layout)
        main_layout.addWidget(controls_widget)

        # Panel statystyk
        self.stats_panel = QWidget()
        self.stats_panel.setStyleSheet(
            """
            QWidget { 
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
            }
            QLabel {
                color: #ffffff;
                padding: 4px;
                background: transparent;
            }
        """
        )
        stats_layout = QVBoxLayout(self.stats_panel)

        stats_header_layout = QHBoxLayout()

        self.stats_title = QLabel("Statystyki folderu")
        self.stats_title.setStyleSheet(
            """
            font-weight: bold; 
            font-size: 14px; 
            color: #3daee9;
            background: transparent;
        """
        )
        stats_header_layout.addWidget(self.stats_title)

        # Dodaj przycisk odświeżania statystyk
        self.refresh_stats_button = QPushButton("🔄")
        self.refresh_stats_button.setToolTip("Odśwież statystyki")
        self.refresh_stats_button.setFixedSize(24, 24)
        self.refresh_stats_button.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: transparent;
                font-size: 12px;
                padding: 2px;
                border-radius: 12px;
            }
            QPushButton:hover {
                background: rgba(61, 174, 233, 0.2);
            }
        """
        )
        self.refresh_stats_button.clicked.connect(self.debug_refresh_stats)
        stats_header_layout.addWidget(self.refresh_stats_button)

        stats_layout.addLayout(stats_header_layout)

        self.stats_content = QLabel("Brak danych")
        stats_layout.addWidget(self.stats_content)
        main_layout.addWidget(self.stats_panel)

        # Środkowy obszar: WebView
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.web_view.urlChanged.connect(self.on_webview_url_changed)
        main_layout.addWidget(self.web_view, 1)

        # Kontrolka rozmiaru kafelków na dole
        size_control_widget = QWidget()
        size_control_widget.setStyleSheet(
            """
            QWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
            }
        """
        )
        size_control_layout = QHBoxLayout(size_control_widget)

        self.size_label = QLabel("Rozmiar kafelków: 200px")
        self.size_label.setStyleSheet(
            """
            color: #ffffff;
            font-weight: 500;
        """
        )

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(100)
        self.size_slider.setMaximum(400)
        self.size_slider.setValue(200)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self.update_tile_size)
        self.size_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #2d2d2d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3daee9;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #4db8f0;
            }
            QSlider::sub-page:horizontal {
                background: #3daee9;
                border-radius: 4px;
            }
        """
        )

        size_control_layout.addWidget(self.size_label)
        size_control_layout.addWidget(self.size_slider)
        main_layout.addWidget(size_control_widget)

        # Dodaj pasek statusu na dole
        self.statusBar = QLabel()
        self.statusBar.setStyleSheet(
            """
            QLabel {
                background-color: rgba(0, 0, 0, 0.7);
                color: #ffffff;
                padding: 5px;
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: #3daee9;
                selection-color: #ffffff;
            }
        """
        )
        self.statusBar.setMinimumHeight(25)
        self.statusBar.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        main_layout.addWidget(self.statusBar)

        self.update_status_label()

    def on_webview_url_changed(self, url):
        self.log_message(f"WebView URL changed to: {url.toString()}")

        # AKTUALIZUJ STATYSTYKI DLA AKTUALNEGO FOLDERU W GALERII
        local_path = url.toLocalFile()
        print(f"🔍 URL_CHANGED - local_path: {local_path}")

        if local_path and os.path.exists(local_path) and local_path.endswith(".html"):
            # Pobierz folder z URL galerii
            gallery_folder = os.path.dirname(local_path)
            print(f"🔍 URL_CHANGED - gallery_folder: {gallery_folder}")

            # Sprawdź czy to nasza galeria (folder w _gallery_cache)
            if "_gallery_cache" in gallery_folder:
                # Znajdź odpowiadający oryginalny folder
                original_folder = self.get_original_folder_from_gallery_path(
                    gallery_folder
                )
                print(f"🔍 URL_CHANGED - original_folder: {original_folder}")

                if original_folder:
                    print(
                        f"🔍 URL_CHANGED - Aktualizuję statystyki dla: {original_folder}"
                    )
                    self.update_folder_stats(original_folder)
                else:
                    print(
                        f"❌ URL_CHANGED - Nie znaleziono oryginalnego folderu dla: {gallery_folder}"
                    )

    def get_current_gallery_path(self):
        if not self.current_work_directory:
            return None
        sanitized_name = gallery_generator.sanitize_path_for_foldername(
            self.current_work_directory
        )
        return os.path.join(self.GALLERY_CACHE_DIR, sanitized_name)

    def get_current_gallery_index_html(self):
        gallery_path = self.get_current_gallery_path()
        if not gallery_path:
            return None
        return os.path.join(gallery_path, "index.html")

    def update_gallery_buttons_state(self):
        gallery_index_html = self.get_current_gallery_index_html()
        exists = bool(gallery_index_html and os.path.exists(gallery_index_html))
        # Przycisk "Pokaż Galerię" jest aktywny jeśli plik istnieje
        self.open_gallery_button.setEnabled(exists)
        self.clear_gallery_cache_button.setEnabled(
            bool(
                self.get_current_gallery_path()
                and os.path.isdir(self.get_current_gallery_path())
            )
        )

    def update_status_label(self):
        if self.current_work_directory:
            self.folder_label.setText(f"Folder roboczy: {self.current_work_directory}")
            self.start_scan_button.setEnabled(True)
            self.rebuild_gallery_button.setEnabled(True)
        else:
            self.folder_label.setText("Folder roboczy: Brak (Wybierz folder)")
            self.start_scan_button.setEnabled(False)
            self.rebuild_gallery_button.setEnabled(False)
            self.web_view.setHtml(
                "<html><body><p style='text-align:center; padding-top:50px;'>Wybierz folder roboczy, aby wyświetlić galerię.</p></body></html>"
            )
        self.update_gallery_buttons_state()

    def select_work_directory(self):
        initial_dir = (
            self.current_work_directory
            if self.current_work_directory
            else os.path.expanduser("~")
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder roboczy", initial_dir
        )
        if folder:
            print(f"🔍 SELECT - Wybrano folder: {folder}")
            self.current_work_directory = folder
            if config_manager.set_work_directory(folder):
                self.log_message(f"Ustawiono folder roboczy: {folder}")
            else:
                self.log_message(f"Błąd zapisu konfiguracji dla folderu: {folder}")

            self.update_status_label()
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            self.update_gallery_buttons_state()

            # DEBUGGING I AKTUALIZACJA STATYSTYK - zawsze dla głównego folderu
            print(
                f"🔍 SELECT - Wywołuję update_folder_stats() dla GŁÓWNEGO folderu: {folder}"
            )
            self.update_folder_stats(folder)  # Przekaż konkretną ścieżkę

            # POTEM AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
            if self.current_gallery_root_html and os.path.exists(
                self.current_gallery_root_html
            ):
                self.show_gallery_in_app()
            else:
                # Jeśli galeria nie istnieje, automatycznie ją zbuduj
                self.rebuild_gallery(auto_show_after_build=True)

    def log_message(self, message):
        """Wyświetla komunikat na pasku statusu"""
        self.statusBar.setText(message)
        QApplication.processEvents()

    def set_buttons_for_processing(self, processing: bool):
        is_work_dir_selected = bool(self.current_work_directory)
        self.start_scan_button.setEnabled(not processing and is_work_dir_selected)
        self.rebuild_gallery_button.setEnabled(not processing and is_work_dir_selected)
        self.select_folder_button.setEnabled(not processing)

        gallery_index_html = self.get_current_gallery_index_html()
        gallery_exists = gallery_index_html and os.path.exists(gallery_index_html)
        self.open_gallery_button.setEnabled(not processing and gallery_exists)

        self.clear_gallery_cache_button.setEnabled(
            not processing
            and bool(
                self.get_current_gallery_path()
                and os.path.isdir(self.get_current_gallery_path())
            )
        )
        self.cancel_button.setEnabled(processing)

    def start_scan(self):
        if not self.current_work_directory:
            QMessageBox.warning(self, "Błąd", "Najpierw wybierz folder roboczy!")
            return

        if self.scanner_thread and self.scanner_thread.isRunning():
            QMessageBox.warning(self, "Błąd", "Skanowanie już trwa!")
            return

        # Pokazuj postęp
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.scanner_thread = ScannerWorker(self.current_work_directory)
        self.scanner_thread.progress_signal.connect(self.log_message)
        self.scanner_thread.finished_signal.connect(self.scan_finished)
        self.scanner_thread.start()

        self.set_buttons_for_processing(True)

    def scan_finished(self):
        self.progress_bar.setVisible(False)
        self.set_buttons_for_processing(False)

        # DEBUGGING I AKTUALIZACJA STATYSTYK PO ZAKOŃCZENIU SKANOWANIA - główny folder
        print(
            f"🔍 SCAN_FINISHED - Wywołuję update_folder_stats() dla GŁÓWNEGO folderu: {self.current_work_directory}"
        )
        self.log_message("Skanowanie zakończone - aktualizacja statystyk")
        self.update_folder_stats(
            self.current_work_directory
        )  # Przekaż konkretną ścieżkę

        QMessageBox.information(self, "Sukces", "Skanowanie zakończone pomyślnie!")

    def rebuild_gallery(self, auto_show_after_build=True):  # Dodano argument
        if not self.current_work_directory:
            QMessageBox.warning(
                self, "Brak folderu", "Najpierw wybierz folder roboczy."
            )
            return

        if (
            self.scanner_thread
            and self.scanner_thread.isRunning()
            or self.gallery_thread
            and self.gallery_thread.isRunning()
        ):
            QMessageBox.information(
                self, "Operacja w toku", "Inna operacja jest już uruchomiona."
            )
            return

        has_index_files = False
        for _, _, files in os.walk(self.current_work_directory):
            if "index.json" in files:
                has_index_files = True
                break

        if not has_index_files:
            QMessageBox.warning(
                self,
                "Brak danych",
                f"Nie znaleziono plików index.json w '{self.current_work_directory}' ani jego podfolderach. "
                "Uruchom najpierw skanowanie.",
            )
            return

        self.log_message(
            f"Rozpoczynanie przebudowy galerii HTML dla: {self.current_work_directory}"
        )

        self.gallery_thread = GalleryWorker(
            self.current_work_directory, self.GALLERY_CACHE_DIR
        )
        self.gallery_thread.progress_signal.connect(self.log_message)
        # Przekazujemy auto_show_after_build do slotu, używając lambdy lub partial
        self.gallery_thread.finished_signal.connect(
            lambda path: self.gallery_generation_finished(path, auto_show_after_build)
        )

        self.set_buttons_for_processing(True)
        self.gallery_thread.start()

    def gallery_generation_finished(
        self, root_html_path, auto_show=True
    ):  # Dodano argument
        is_cancelled = (
            self.gallery_thread.is_cancelled if self.gallery_thread else False
        )
        self.current_gallery_root_html = (
            root_html_path if not is_cancelled and root_html_path else None
        )

        if not is_cancelled:
            if self.current_gallery_root_html:
                self.log_message(
                    f"Przebudowa galerii zakończona. Główny plik: {self.current_gallery_root_html}"
                )
                QMessageBox.information(
                    self, "Koniec", "Generowanie galerii HTML zakończone."
                )
                if auto_show:  # Automatycznie pokaż po przebudowie
                    self.show_gallery_in_app()
            else:
                self.log_message("Nie udało się wygenerować galerii.")
                QMessageBox.warning(
                    self, "Błąd", "Nie udało się wygenerować galerii HTML."
                )
                self.web_view.setHtml(
                    "<html><body><p style='text-align:center; padding-top:50px;'>Nie udało się wygenerować galerii.</p></body></html>"
                )

        self.set_buttons_for_processing(False)
        self.gallery_thread = None
        self.update_gallery_buttons_state()

    def show_gallery_in_app(self):
        gallery_index_html = self.get_current_gallery_index_html()
        if gallery_index_html and os.path.exists(gallery_index_html):
            abs_path = os.path.abspath(gallery_index_html)
            self.web_view.setUrl(QUrl.fromLocalFile(abs_path))
            self.log_message(f"Ładowanie galerii do widoku: {abs_path}")

            # Ustaw rozmiar kafelków po załadowaniu
            def apply_tile_size():
                self.update_tile_size()

            # Opóźnienie aby strona się załadowała
            QApplication.processEvents()
            self.web_view.loadFinished.connect(lambda: self.update_tile_size())

        else:
            self.log_message("Plik główny galerii nie istnieje. Przebuduj galerię.")
            QMessageBox.information(
                self,
                "Galeria nie istnieje",
                "Plik główny galerii (index.html) nie istnieje. Przebuduj galerię.",
            )
            self.web_view.setHtml(
                "<html><body><p style='text-align:center; padding-top:50px;'>Galeria nie istnieje lub nie została jeszcze wygenerowana.</p></body></html>"
            )

    def clear_current_gallery_cache(self):
        gallery_path_to_clear = self.get_current_gallery_path()
        if not gallery_path_to_clear or not os.path.isdir(gallery_path_to_clear):
            QMessageBox.information(
                self,
                "Brak cache",
                "Nie znaleziono folderu cache dla bieżącego katalogu roboczego.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć cały folder cache galerii dla:\n{self.current_work_directory}\n({gallery_path_to_clear})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Zanim usuniesz, wyczyść widok web, jeśli wyświetla coś z tego cache
                current_url = self.web_view.url().toLocalFile()
                if current_url and current_url.startswith(
                    os.path.abspath(gallery_path_to_clear)
                ):
                    self.web_view.setHtml(
                        "<html><body><p style='text-align:center; padding-top:50px;'>Cache galerii został usunięty.</p></body></html>"
                    )

                shutil.rmtree(gallery_path_to_clear)
                self.log_message(
                    f"Usunięto folder cache galerii: {gallery_path_to_clear}"
                )
                self.current_gallery_root_html = None
                self.update_gallery_buttons_state()
                QMessageBox.information(
                    self, "Cache usunięty", "Folder cache galerii został usunięty."
                )
            except Exception as e:
                self.log_message(f"Błąd podczas usuwania cache galerii: {e}")
                QMessageBox.warning(
                    self, "Błąd usuwania", f"Nie udało się usunąć folderu cache: {e}"
                )

    def cancel_operations(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.cancel()
            self.log_message("Próba anulowania skanowania...")
        elif self.gallery_thread and self.gallery_thread.isRunning():
            self.gallery_thread.cancel()
            self.log_message("Próba anulowania generowania galerii...")
        else:
            self.log_message("Brak aktywnej operacji do anulowania.")

    def closeEvent(self, event):
        if (self.scanner_thread and self.scanner_thread.isRunning()) or (
            self.gallery_thread and self.gallery_thread.isRunning()
        ):
            reply = QMessageBox.question(
                self,
                "Zamykanie aplikacji",
                "Operacja jest w toku. Czy na pewno chcesz zamknąć aplikację?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.scanner_thread:
                    self.scanner_thread.cancel()
                if self.gallery_thread:
                    self.gallery_thread.cancel()
                if self.scanner_thread:
                    self.scanner_thread.wait(1000)
                if self.gallery_thread:
                    self.gallery_thread.wait(1000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def update_tile_size(self):
        """Aktualizuje rozmiar kafelków w galerii poprzez JavaScript"""
        size = self.size_slider.value()
        self.size_label.setText(f"{size}px")

        # Wyślij JavaScript do WebView aby zaktualizować CSS
        js_code = f"""
        var galleries = document.querySelectorAll('.gallery');
        galleries.forEach(function(gallery) {{
            gallery.style.gridTemplateColumns = 'repeat(auto-fill, minmax({size}px, 1fr))';
        }});
        
        // Zapisz ustawienie do localStorage
        localStorage.setItem('galleryTileSize', '{size}');
        """
        self.web_view.page().runJavaScript(js_code)

    def update_folder_stats(self, folder_path=None):
        """Aktualizuje panel statystyki folderu"""
        # Jeśli nie podano ścieżki, użyj głównego folderu roboczego
        if not folder_path:
            folder_path = self.current_work_directory

        if not folder_path or not os.path.exists(folder_path):
            self.stats_content.setText("Brak danych")
            self.log_message("Brak folderu do sprawdzenia statystyk")
            return

        # Wczytaj statystyki z index.json jeśli istnieje
        index_json = os.path.join(folder_path, "index.json")
        self.log_message(f"Sprawdzanie pliku index.json: {index_json}")

        if os.path.exists(index_json):
            try:
                with open(index_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    folder_info = data.get("folder_info", {})

                    self.log_message(
                        f"Wczytano dane z index.json: {list(folder_info.keys()) if folder_info else 'brak folder_info'}"
                    )

                    if folder_info and isinstance(folder_info, dict):
                        # Sprawdź czy mamy wymagane klucze
                        total_size = folder_info.get("total_size_readable", "0 B")
                        file_count = folder_info.get("file_count", 0)
                        subdir_count = folder_info.get("subdir_count", 0)
                        archive_count = folder_info.get("archive_count", 0)
                        scan_date = folder_info.get("scan_date", "Nieznana")

                        # Dodaj nazwę aktualnego folderu do statystyk
                        folder_name = os.path.basename(folder_path)
                        stats_text = (
                            f"📁 {folder_name} | "
                            f"Rozmiar: {total_size} | "
                            f"Pliki: {file_count} | "
                            f"Foldery: {subdir_count} | "
                            f"Archiwa: {archive_count} | "
                            f"Skanowano: {scan_date}"
                        )
                        self.stats_content.setText(stats_text)
                        self.log_message(
                            f"✅ SUKCES - Wyświetlono statystyki dla {folder_name}: {stats_text}"
                        )
                    else:
                        self.stats_content.setText(
                            "Dane folder_info są puste - uruchom skanowanie"
                        )
                        self.log_message(
                            f"❌ BŁĄD - Brak poprawnych danych folder_info w: {index_json}"
                        )
            except json.JSONDecodeError as e:
                self.stats_content.setText(f"Błąd formatu JSON: {str(e)}")
                self.log_message(f"❌ BŁĄD JSON w pliku {index_json}: {str(e)}")
            except Exception as e:
                self.stats_content.setText(f"Błąd odczytu: {str(e)}")
                self.log_message(f"❌ BŁĄD odczytu pliku {index_json}: {str(e)}")
        else:
            folder_name = os.path.basename(folder_path)
            self.stats_content.setText(
                f"📁 {folder_name} - Naciśnij 'Skanuj Foldery' aby zobaczyć statystyki"
            )
            self.log_message(f"❌ BRAK pliku index.json w: {folder_path}")

    def debug_refresh_stats(self):
        """Debugowa funkcja odświeżania statystyk"""
        # Sprawdź czy jesteśmy w galerii i pobierz aktualny folder
        current_url = self.web_view.url().toLocalFile()
        if current_url and "_gallery_cache" in current_url:
            gallery_folder = os.path.dirname(current_url)
            original_folder = self.get_original_folder_from_gallery_path(gallery_folder)
            if original_folder:
                print(
                    f"🔍 REFRESH - Ręczne odświeżenie statystyk dla aktualnego folderu: {original_folder}"
                )
                self.log_message(
                    f"Ręczne odświeżenie statystyk dla: {os.path.basename(original_folder)}"
                )
                self.update_folder_stats(original_folder)
                return

        # Fallback - główny folder roboczy
        print(
            f"🔍 REFRESH - Ręczne odświeżenie statystyk dla głównego folderu: {self.current_work_directory}"
        )
        self.log_message(f"Ręczne odświeżenie statystyk dla głównego folderu")
        self.update_folder_stats()

    def get_original_folder_from_gallery_path(self, gallery_path):
        """Mapuje ścieżkę galerii na oryginalną ścieżkę folderu"""
        try:
            if not self.current_work_directory:
                print("❌ get_original_folder - Brak current_work_directory")
                return None

            # Pobierz sanitized name głównego folderu
            sanitized_main = gallery_generator.sanitize_path_for_foldername(
                self.current_work_directory
            )
            print(f"🔍 get_original_folder - sanitized_main: {sanitized_main}")

            # Znajdź względną ścieżkę w galerii
            gallery_cache_path = os.path.join(self.GALLERY_CACHE_DIR, sanitized_main)
            print(f"🔍 get_original_folder - gallery_cache_path: {gallery_cache_path}")
            print(f"🔍 get_original_folder - gallery_path: {gallery_path}")

            if gallery_path.startswith(gallery_cache_path):
                # Pobierz względną ścieżkę od głównego folderu galerii
                relative_path = os.path.relpath(gallery_path, gallery_cache_path)
                print(f"🔍 get_original_folder - relative_path: {relative_path}")

                if relative_path == ".":
                    # To główny folder
                    print(
                        f"🔍 get_original_folder - To główny folder: {self.current_work_directory}"
                    )
                    return self.current_work_directory
                else:
                    # To podfolder
                    original_path = os.path.join(
                        self.current_work_directory, relative_path
                    )
                    print(
                        f"🔍 get_original_folder - Sprawdzam podfolder: {original_path}"
                    )
                    if os.path.exists(original_path):
                        print(
                            f"✅ get_original_folder - Znaleziono podfolder: {original_path}"
                        )
                        return original_path
                    else:
                        print(
                            f"❌ get_original_folder - Podfolder nie istnieje: {original_path}"
                        )
            else:
                print(
                    f"❌ get_original_folder - gallery_path nie zaczyna się od gallery_cache_path"
                )

            return None
        except Exception as e:
            print(f"❌ Błąd mapowania ścieżki galerii: {e}")
            return None

    def setup_learning_bridge(self):
        """Konfiguruje most komunikacyjny z JavaScript dla funkcji uczenia się"""
        self.web_view.loadFinished.connect(self.inject_learning_bridge)

        # Timer do sprawdzania nowych dopasowań co sekundę
        self.learning_timer = QTimer()
        self.learning_timer.timeout.connect(self.check_for_learning_matches)
        self.learning_timer.start(1000)  # Co sekundę

        # Timer do sprawdzania usuwania plików
        self.delete_timer = QTimer()
        self.delete_timer.timeout.connect(self.check_for_file_deletions)
        self.delete_timer.start(1000)  # Co sekundę

    def inject_learning_bridge(self):
        """Wstrzykuje bridge JavaScript dla komunikacji z funkcją uczenia się"""
        bridge_js = """
        console.log('🔌 Learning bridge injected');
        window.addEventListener('learningMatchReady', function(event) {
            console.log('🎯 Learning match event received:', event.detail);
        });
        """
        self.web_view.page().runJavaScript(bridge_js)

    def check_for_learning_matches(self):
        """Sprawdza localStorage pod kątem nowych dopasowań do nauki"""
        js_code = """
        (function() {
            try {
                // Sprawdź czy localStorage jest dostępny
                if (typeof(Storage) === "undefined" || !localStorage) {
                    console.log('localStorage nie jest dostępny');
                    return null;
                }
                
                const latestMatchKey = localStorage.getItem('latestMatch');
                if (latestMatchKey) {
                    const matchData = localStorage.getItem(latestMatchKey);
                    if (matchData) {
                        // Usuń z localStorage
                        localStorage.removeItem(latestMatchKey);
                        localStorage.removeItem('latestMatch');
                        console.log('🔍 Found learning match:', matchData);
                        return matchData;
                    }
                }
                return null;
            } catch(e) {
                console.error('Error checking learning matches:', e.name + ': ' + e.message);
                return null;
            }
        })();
        """

        self.web_view.page().runJavaScript(js_code, self.handle_learning_match)

    def handle_learning_match(self, result):
        """Obsługuje nowe dopasowanie z JavaScript"""
        if result:
            try:
                match_data = json.loads(result)
                print(f"🎓 OTRZYMANO NOWE DOPASOWANIE: {match_data}")
                self.log_message(
                    f"🎓 Nowe dopasowanie: {match_data['archiveFile']} ↔ {match_data['imageFile']}"
                )

                # Zapisz dopasowanie
                self.save_learning_data(
                    match_data["archiveFile"],
                    match_data["imageFile"],
                    match_data["archivePath"],
                    match_data["imagePath"],
                )

                # NATYCHMIASTOWE ZASTOSOWANIE - ponowne skanowanie aktualnego folderu
                self.apply_learning_immediately(match_data)

            except Exception as e:
                print(f"❌ Błąd przetwarzania dopasowania: {e}")
                self.log_message(f"Błąd przetwarzania dopasowania: {e}")

    def apply_learning_immediately(self, match_data):
        """Natychmiast stosuje nauczone dopasowanie"""
        try:
            # Znajdź folder z którego pochodzi dopasowanie
            archive_path = match_data.get("archivePath", "")
            if archive_path:
                current_folder = os.path.dirname(archive_path.replace("/", os.sep))
                print(f"🔄 Ponowne skanowanie folderu: {current_folder}")

                # Uruchom ponowne skanowanie tego konkretnego folderu
                self.rescan_specific_folder(current_folder)

        except Exception as e:
            print(f"❌ Błąd zastosowania nauki: {e}")
            self.log_message(f"Błąd zastosowania nauki: {e}")

    def rescan_specific_folder(self, folder_path):
        """Ponownie skanuje konkretny folder i odświeża galerię"""
        try:
            if not os.path.exists(folder_path):
                print(f"❌ Folder nie istnieje: {folder_path}")
                return

            self.log_message(f"🔄 Ponowne skanowanie: {folder_path}")

            # Uruchom skanowanie w tle dla tego folderu
            import threading

            def scan_and_refresh():
                try:
                    # Skanuj folder
                    scanner_logic.process_folder(
                        folder_path, lambda msg: print(f"📁 {msg}")
                    )

                    # Odśwież galerię w głównym wątku
                    QTimer.singleShot(
                        500, lambda: self.refresh_gallery_after_learning(folder_path)
                    )

                except Exception as e:
                    print(f"❌ Błąd skanowania: {e}")

            thread = threading.Thread(target=scan_and_refresh)
            thread.daemon = True
            thread.start()

        except Exception as e:
            print(f"❌ Błąd rescan_specific_folder: {e}")

    def refresh_gallery_after_learning(self, scanned_folder):
        """Odświeża galerię po zastosowaniu nauki"""
        try:
            print(f"🔄 Odświeżanie galerii po nauce dla: {scanned_folder}")

            # Sprawdź czy to aktualny folder lub jego podfolder
            current_url = self.web_view.url().toLocalFile()
            if current_url and "_gallery_cache" in current_url:
                gallery_folder = os.path.dirname(current_url)
                original_folder = self.get_original_folder_from_gallery_path(
                    gallery_folder
                )

                if original_folder and (
                    original_folder == scanned_folder
                    or scanned_folder.startswith(original_folder)
                ):
                    print(
                        f"✅ Folder {scanned_folder} jest częścią aktualnej galerii - odświeżam"
                    )

                    # Przebuduj galerię
                    self.rebuild_gallery_silent()

                    # Poinformuj o sukcesie przez JavaScript
                    success_js = """
                    const matchBtn = document.getElementById('matchPreviewBtn');
                    const matchStatus = document.getElementById('matchStatus');
                    if (matchBtn && matchStatus) {
                        matchBtn.disabled = false;
                        matchBtn.textContent = '🎯 Dopasuj podgląd';
                        matchStatus.textContent = '🎉 Dopasowanie zastosowane! Galeria została odświeżona.';
                        
                        setTimeout(() => {
                            matchStatus.textContent = '';
                        }, 5000);
                    }
                    """
                    self.web_view.page().runJavaScript(success_js)

                    self.log_message("✅ Algorytm nauczony! Galeria odświeżona.")

            else:
                print(f"ℹ️ Folder {scanned_folder} nie jest częścią aktualnej galerii")

        except Exception as e:
            print(f"❌ Błąd odświeżania galerii: {e}")

    def rebuild_gallery_silent(self):
        """Przebudowuje galerię w tle bez pokazywania dialogów"""
        try:
            if not self.current_work_directory:
                return

            # Sprawdź czy jest już proces
            if self.gallery_thread and self.gallery_thread.isRunning():
                return

            print("🔄 Ciche przebudowanie galerii...")

            self.gallery_thread = GalleryWorker(
                self.current_work_directory, self.GALLERY_CACHE_DIR
            )
            self.gallery_thread.progress_signal.connect(lambda msg: print(f"🏗️ {msg}"))
            self.gallery_thread.finished_signal.connect(self.gallery_rebuilt_silently)
            self.gallery_thread.start()

        except Exception as e:
            print(f"❌ Błąd rebuild_gallery_silent: {e}")

    def gallery_rebuilt_silently(self, root_html_path):
        """Obsługuje zakończenie cichego przebudowania galerii"""
        try:
            if root_html_path:
                print(f"✅ Galeria przebudowana cicho: {root_html_path}")

                # Odśwież aktualną stronę
                current_url = self.web_view.url()
                self.web_view.reload()

            self.gallery_thread = None

        except Exception as e:
            print(f"❌ Błąd gallery_rebuilt_silently: {e}")

    def save_learning_data(self, archive_file, image_file, archive_path, image_path):
        """Zapisuje dane uczenia się do pliku JSON"""
        try:
            learning_file = "learning_data.json"
            learning_data = []

            # Wczytaj istniejące dane
            if os.path.exists(learning_file):
                with open(learning_file, "r", encoding="utf-8") as f:
                    learning_data = json.load(f)

            # Sprawdź czy już istnieje takie dopasowanie
            archive_basename = os.path.splitext(archive_file)[0]
            image_basename = os.path.splitext(image_file)[0]

            # Usuń stare dopasowanie dla tego samego archiwum jeśli istnieje
            learning_data = [
                item
                for item in learning_data
                if item.get("archive_basename", "").lower() != archive_basename.lower()
            ]

            # Dodaj nowe dopasowanie
            new_match = {
                "archive_file": archive_file,
                "image_file": image_file,
                "archive_path": archive_path,
                "image_path": image_path,
                "timestamp": datetime.now().isoformat(),
                "archive_basename": archive_basename,
                "image_basename": image_basename,
            }

            learning_data.append(new_match)

            # Zapisz zaktualizowane dane
            with open(learning_file, "w", encoding="utf-8") as f:
                json.dump(learning_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Zapisano dane uczenia się: {len(learning_data)} dopasowań")
            self.log_message(
                f"💾 Zapisano nauczone dopasowanie: {archive_file} ↔ {image_file}"
            )

        except Exception as e:
            print(f"❌ Błąd zapisu danych uczenia się: {e}")
            self.log_message(f"Błąd zapisu danych uczenia się: {e}")

    def check_for_file_deletions(self):
        """Sprawdza localStorage pod kątem żądań usunięcia plików"""
        js_code = """
        (function() {
            try {
                // Sprawdź czy localStorage jest dostępny
                if (typeof(Storage) === "undefined" || !localStorage) {
                    console.log('localStorage nie jest dostępny');
                    return null;
                }
                
                const latestDeleteKey = localStorage.getItem('latestDelete');
                if (latestDeleteKey) {
                    const deleteData = localStorage.getItem(latestDeleteKey);
                    if (deleteData) {
                        // Usuń z localStorage
                        localStorage.removeItem(latestDeleteKey);
                        localStorage.removeItem('latestDelete');
                        console.log('🗑️ Found delete request:', deleteData);
                        return deleteData;
                    }
                }
                return null;
            } catch(e) {
                console.error('Error checking delete requests:', e.name + ': ' + e.message);
                return null;
            }
        })();
        """

        self.web_view.page().runJavaScript(js_code, self.handle_file_deletion)

    def handle_file_deletion(self, result):
        """Obsługuje żądanie usunięcia pliku"""
        if result:
            try:
                delete_data = json.loads(result)
                file_path = delete_data.get("filePath", "")
                file_name = delete_data.get("fileName", "")

                print(f"🗑️ ŻĄDANIE USUNIĘCIA: {file_name} -> {file_path}")
                self.log_message(f"🗑️ Usuwanie do kosza: {file_name}")

                # Usuń plik do kosza
                success = self.delete_file_to_trash(file_path)

                if success:
                    self.log_message(f"✅ Plik usunięty do kosza: {file_name}")

                    # NATYCHMIASTOWE ODŚWIEŻENIE - reskanuj folder i przebuduj galerię
                    current_url = self.web_view.url().toLocalFile()
                    if current_url and "_gallery_cache" in current_url:
                        gallery_folder = os.path.dirname(current_url)
                        original_folder = self.get_original_folder_from_gallery_path(
                            gallery_folder
                        )

                        if original_folder:
                            print(
                                f"🔄 Ponowne skanowanie po usunięciu: {original_folder}"
                            )
                            # Reskanuj folder natychmiast
                            QTimer.singleShot(
                                100,
                                lambda: self.rescan_and_rebuild_after_deletion(
                                    original_folder
                                ),
                            )

                else:
                    self.log_message(f"❌ Błąd usuwania pliku: {file_name}")
                    # Przywróć element w JavaScript
                    restore_js = f"""
                    const deleteKey = 'deleteFile_restore_' + Date.now();
                    localStorage.setItem(deleteKey, JSON.stringify({{
                        action: 'restoreFile',
                        fileName: '{file_name}',
                        error: 'Nie udało się usunąć pliku'
                    }}));
                    localStorage.setItem('latestRestore', deleteKey);
                    """
                    self.web_view.page().runJavaScript(restore_js)

            except Exception as e:
                print(f"❌ Błąd przetwarzania usuwania: {e}")
                self.log_message(f"Błąd usuwania pliku: {e}")

    def delete_file_to_trash(self, file_path):
        """Usuwa plik do kosza systemowego"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ Plik nie istnieje: {file_path}")
                return False

            send2trash.send2trash(file_path)
            print(f"✅ Plik usunięty do kosza: {file_path}")
            return True

        except ImportError:
            print("❌ Brak biblioteki send2trash - instaluj: pip install send2trash")
            try:
                # Fallback - usuń na stałe (niebezpieczne!)
                os.remove(file_path)
                print(f"⚠️ Plik usunięty na stałe: {file_path}")
                return True
            except Exception as e:
                print(f"❌ Błąd usuwania pliku: {e}")
                return False
        except Exception as e:
            print(f"❌ Błąd usuwania do kosza: {e}")
            return False

    def rescan_and_rebuild_after_deletion(self, folder_path):
        """Ponownie skanuje folder i przebudowuje galerię po usunięciu pliku"""
        try:
            import threading

            self.log_message(f"🔄 Aktualizacja po usunięciu pliku...")

            def scan_and_rebuild():
                try:
                    # 1. Ponownie przeskanuj folder (aktualizuj index.json)
                    scanner_logic.process_folder(
                        folder_path, lambda msg: print(f"📁 RESCAN: {msg}")
                    )

                    # 2. Przebuduj galerię w głównym wątku
                    QTimer.singleShot(200, self.rebuild_gallery_after_deletion)

                except Exception as e:
                    print(f"❌ Błąd ponownego skanowania: {e}")
                    QTimer.singleShot(
                        100, lambda: self.log_message(f"Błąd aktualizacji: {e}")
                    )

            # Uruchom w osobnym wątku
            thread = threading.Thread(target=scan_and_rebuild)
            thread.daemon = True
            thread.start()

        except Exception as e:
            print(f"❌ Błąd rescan_and_rebuild_after_deletion: {e}")
            self.log_message(f"Błąd aktualizacji po usunięciu: {e}")

    def rebuild_gallery_after_deletion(self):
        """Przebudowuje galerię po usunięciu pliku"""
        try:
            if not self.current_work_directory:
                return

            # Sprawdź czy jest już proces
            if self.gallery_thread and self.gallery_thread.isRunning():
                return

            print("🔄 Przebudowa galerii po usunięciu pliku...")
            self.log_message("🔄 Aktualizacja galerii...")

            self.gallery_thread = GalleryWorker(
                self.current_work_directory, self.GALLERY_CACHE_DIR
            )
            self.gallery_thread.progress_signal.connect(lambda msg: print(f"🏗️ {msg}"))
            self.gallery_thread.finished_signal.connect(
                self.gallery_rebuilt_after_deletion
            )
            self.gallery_thread.start()

        except Exception as e:
            print(f"❌ Błąd rebuild_gallery_after_deletion: {e}")

    def gallery_rebuilt_after_deletion(self, root_html_path):
        """Obsługuje zakończenie przebudowy galerii po usunięciu"""
        try:
            if root_html_path:
                print(f"✅ Galeria przebudowana po usunięciu: {root_html_path}")

                # Odśwież aktualną stronę
                current_url = self.web_view.url()
                self.web_view.reload()

                # Komunikat o sukcesie
                self.log_message("✅ Galeria zaktualizowana po usunięciu pliku")

                # Opcjonalnie: pokaż komunikat w JavaScript
                success_js = """
                setTimeout(() => {
                    if (typeof localStorage !== 'undefined') {
                        const notification = document.createElement('div');
                        notification.style.cssText = `
                            position: fixed; top: 20px; right: 20px; z-index: 9999;
                            background: var(--success); color: white; padding: 12px 20px;
                            border-radius: 8px; font-weight: 500; box-shadow: var(--shadow);
                        `;
                        notification.textContent = '✅ Plik usunięty, galeria zaktualizowana';
                        document.body.appendChild(notification);
                        
                        setTimeout(() => {
                            if (notification.parentNode) {
                                notification.parentNode.removeChild(notification);
                            }
                        }, 3000);
                    }
                }, 500);
                """
                self.web_view.page().runJavaScript(success_js)

            self.gallery_thread = None

        except Exception as e:
            print(f"❌ Błąd gallery_rebuilt_after_deletion: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ZASTOSUJ CIEMNY MOTYW
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))

    # Opcjonalnie: konfiguracja dla lepszego wyglądu
    app.setStyle("Fusion")  # Lepszy styl bazowy

    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(script_dir, "templates")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
