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

    def run(self):
        try:
            scanner_logic.start_scanning(self.root_folder, self.emit_progress)
        except Exception as e:
            self.progress_signal.emit(f"Wystąpił krytyczny błąd skanowania: {e}")
        finally:
            self.finished_signal.emit()

    def emit_progress(self, message):
        self.progress_signal.emit(message)


class GalleryWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)  # Emits path to root HTML or None if failed

    def __init__(self, scanned_root_path, gallery_cache_root):
        super().__init__()
        self.scanned_root_path = scanned_root_path
        self.gallery_cache_root = gallery_cache_root

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
            self.finished_signal.emit(root_html_path)

    def emit_progress(self, message):
        self.progress_signal.emit(message)


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
        self.learning_timer = None
        self.file_operations_timer = None

        # DEBUGGING
        print(f"🔍 INIT - current_work_directory: {self.current_work_directory}")

        os.makedirs(self.GALLERY_CACHE_DIR, exist_ok=True)
        self.init_ui()
        self.update_status_label()
        self.update_gallery_buttons_state()
        self.setup_learning_bridge()
        self.setup_file_operations_bridge()

        if self.current_work_directory:
            print(f"🔍 INIT - Sprawdzanie galerii dla: {self.current_work_directory}")
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            if self.current_gallery_root_html and os.path.exists(
                self.current_gallery_root_html
            ):
                self.show_gallery_in_app()
            # Sprawdź oczekujące dopasowania po załadowaniu galerii
            QTimer.singleShot(1000, self.check_for_learning_matches)

    def init_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Górny pasek z kontrolkami w jednej linii
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        # Przycisk wyboru folderu
        self.select_folder_button = QPushButton("📁 Wybierz Folder")
        self.select_folder_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """
        )
        self.select_folder_button.setMinimumWidth(90)
        self.select_folder_button.clicked.connect(self.select_work_directory)
        controls_layout.addWidget(self.select_folder_button)

        # Etykieta folderu roboczego
        self.folder_label = QLabel("Folder roboczy: Brak")
        self.folder_label.setStyleSheet("padding: 8px;")
        controls_layout.addWidget(self.folder_label, 1)  # 1 oznacza rozciągnięcie

        # Przyciski akcji
        self.start_scan_button = QPushButton("🔍 Skanuj Foldery")
        self.start_scan_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """
        )
        self.start_scan_button.setMinimumWidth(90)
        self.start_scan_button.clicked.connect(self.start_scan)
        controls_layout.addWidget(self.start_scan_button)

        self.rebuild_gallery_button = QPushButton("🔄 Przebuduj Galerię")
        self.rebuild_gallery_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """
        )
        self.rebuild_gallery_button.setMinimumWidth(90)
        self.rebuild_gallery_button.clicked.connect(lambda: self.rebuild_gallery(True))
        controls_layout.addWidget(self.rebuild_gallery_button)

        self.open_gallery_button = QPushButton("👁️ Pokaż Galerię")
        self.open_gallery_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """
        )
        self.open_gallery_button.setMinimumWidth(90)
        self.open_gallery_button.clicked.connect(self.show_gallery_in_app)
        controls_layout.addWidget(self.open_gallery_button)

        self.clear_gallery_cache_button = QPushButton("🗑️ Wyczyść Cache")
        self.clear_gallery_cache_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c62d42;
            }
        """
        )
        self.clear_gallery_cache_button.setMinimumWidth(90)
        self.clear_gallery_cache_button.clicked.connect(
            self.clear_current_gallery_cache
        )
        controls_layout.addWidget(self.clear_gallery_cache_button)

        main_layout.addWidget(controls_widget)

        # Pasek postępu
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
        main_layout.addWidget(self.progress_bar)

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
        size_control_layout = QHBoxLayout(size_control_widget)
        size_control_layout.setContentsMargins(0, 0, 0, 0)
        size_control_layout.setSpacing(10)

        # Lewa strona - suwak
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self.size_label = QLabel("Rozmiar kafelków: 200px")
        self.size_label.setStyleSheet(
            """
            color: #ffffff;
            font-weight: 500;
            padding: 0 10px;
        """
        )

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(100)
        self.size_slider.setMaximum(400)
        self.size_slider.setValue(200)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self.update_tile_size)
        self.size_slider.setFixedWidth(300)
        self.size_slider.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 5px;
                background: #2d2d2d;
                margin: 1px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3daee9;
                border: 1px solid #5c5c5c;
                width: 14px;
                margin: -2px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #4db8f0;
            }
            QSlider::sub-page:horizontal {
                background: #3daee9;
                border-radius: 2px;
            }
        """
        )

        left_layout.addWidget(self.size_label)
        left_layout.addWidget(self.size_slider)
        left_layout.addStretch()

        # Prawa strona - przyciski operacji na plikach
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Przyciski operacji na plikach (ikona + tekst, identyczny styl jak górne)
        file_operations = [
            (
                "📁➡️ Przenieś pliki",
                "Przenieś pliki",
                self.show_move_files_dialog_python,
            ),
            ("✏️ Zmień nazwy", "Zmień nazwy", self.show_rename_files_dialog_python),
            ("📁+ Nowy folder", "Nowy folder", self.show_create_folder_dialog_python),
            ("🗑️📁 Usuń puste", "Usuń puste", self.show_delete_empty_dialog_python),
            ("🔄 Odśwież", "Odśwież", self.force_refresh_gallery),
        ]

        for text, tooltip, handler in file_operations:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(
                """
                QPushButton {
                    padding: 8px 16px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #2d5aa0;
                }
            """
            )
            btn.setMinimumWidth(90)
            btn.clicked.connect(handler)
            right_layout.addWidget(btn)

        # Dodaj oba widgety do głównego layoutu
        size_control_layout.addWidget(left_widget)
        size_control_layout.addWidget(right_widget)
        main_layout.addWidget(size_control_widget)

        # Pasek statusu na dole
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

        # Pobierz folder z URL galerii
        local_path = url.toLocalFile()
        print(f"🔍 URL_CHANGED - local_path: {local_path}")

        if local_path and os.path.exists(local_path) and local_path.endswith(".html"):
            gallery_folder = os.path.dirname(local_path)
            print(f"🔍 URL_CHANGED - gallery_folder: {gallery_folder}")

            # Sprawdź czy to nasza galeria (folder w _gallery_cache)
            if "_gallery_cache" in gallery_folder:
                print(f"ℹ️ URL_CHANGED - Przejście do nowej strony galerii")

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

            # POTEM AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
            if self.current_gallery_root_html and os.path.exists(
                self.current_gallery_root_html
            ):
                self.show_gallery_in_app()
            else:
                # Jeśli galeria nie istnieje, automatycznie ją zbuduj
                self.rebuild_gallery(auto_show_after_build=True)

    def log_message(self, message):
        """Wyświetla komunikat na pasku statusu i w konsoli"""
        print(f"ℹ️ UI: {message}")  # Dodajemy prefix ℹ️ dla lepszej czytelności
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

    def gallery_generation_finished(self, root_html_path, auto_show=True):
        self.current_gallery_root_html = root_html_path if root_html_path else None

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
            QMessageBox.warning(self, "Błąd", "Nie udało się wygenerować galerii HTML.")
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

            # Używamy lambda żeby uniknąć wielokrotnego wywoływania
            self.web_view.loadFinished.connect(lambda ok: self.on_gallery_loaded(ok))
        else:
            self.log_message("❌ Nie znaleziono pliku galerii")

    def on_gallery_loaded(self, ok):
        if ok:
            self.inject_file_operations_bridge()
            self.update_tile_size()
            print("✅ Galeria załadowana, wtryknięto mostek operacji na plikach")

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

    def setup_learning_bridge(self):
        """Konfiguruje mostek do komunikacji z JavaScript dla uczenia"""
        self.learning_timer = QTimer()
        self.learning_timer.timeout.connect(self.check_for_learning_matches)
        self.learning_timer.start(500)  # Co pół sekundy

    def setup_file_operations_bridge(self):
        """Konfiguruje mostek do komunikacji z JavaScript dla operacji na plikach"""
        self.file_operations_timer = QTimer()
        self.file_operations_timer.timeout.connect(self.check_for_file_operations)
        self.file_operations_timer.start(500)  # Co pół sekundy

    def inject_learning_bridge(self):
        """Wstrzykuje kod JavaScript do obsługi uczenia"""
        js_code = """
        window.handleLearningMatch = function(matchData) {
            const matchKey = 'learningMatch_' + Date.now();
            localStorage.setItem(matchKey, JSON.stringify(matchData));
            localStorage.setItem('latestLearningMatch', matchKey);
        };
        """
        self.web_view.page().runJavaScript(js_code)

    def check_for_learning_matches(self):
        """Sprawdza czy są nowe dopasowania do nauki"""
        try:
            js_code = """
            (function() {
                const latestKey = localStorage.getItem('latestLearningMatch');
                if (!latestKey) return null;
                
                const matchData = localStorage.getItem(latestKey);
                localStorage.removeItem(latestKey);
                localStorage.removeItem('latestLearningMatch');
                return matchData;
            })();
            """

            self.web_view.page().runJavaScript(js_code, self.handle_learning_match)

        except Exception as e:
            print(f"❌ Błąd check_for_learning_matches: {e}")

    def handle_learning_match(self, result):
        """Obsługuje nowe dopasowanie do nauki"""
        try:
            if not result:
                return

            match_data = json.loads(result)
            if not match_data:
                return

            # Zapisz dane do nauki
            self.save_learning_data(
                match_data.get("archive_file"),
                match_data.get("image_file"),
                match_data.get("archive_path"),
                match_data.get("image_path"),
            )

            # Zastosuj dopasowanie
            self.apply_learning_immediately(match_data)

        except Exception as e:
            print(f"❌ Błąd handle_learning_match: {e}")

    def apply_learning_immediately(self, match_data):
        """Natychmiastowo stosuje dopasowanie"""
        try:
            archive_path = match_data.get("archive_path")
            if not archive_path or not os.path.exists(archive_path):
                return

            # Przeskanuj folder zawierający archiwum
            folder_path = os.path.dirname(archive_path)
            self.rescan_specific_folder(folder_path)

        except Exception as e:
            print(f"❌ Błąd apply_learning_immediately: {e}")

    def rescan_specific_folder(self, folder_path):
        """Przeskanowuje konkretny folder"""
        try:
            if not os.path.exists(folder_path):
                return

            def scan_and_refresh():
                try:
                    # Skanuj folder
                    scanner_logic.start_scanning(folder_path, lambda msg: None)

                    # Odśwież galerię
                    self.refresh_gallery_after_learning(folder_path)

                except Exception as e:
                    print(f"❌ Błąd w scan_and_refresh: {e}")

            # Uruchom w wątku
            QThread.create(scan_and_refresh)

        except Exception as e:
            print(f"❌ Błąd rescan_specific_folder: {e}")

    def refresh_gallery_after_learning(self, scanned_folder):
        """Odświeża galerię po nauce"""
        try:
            if not scanned_folder or not os.path.exists(scanned_folder):
                return

            # Znajdź główny folder galerii
            gallery_root = self.get_current_gallery_path()
            if not gallery_root:
                return

            # Znajdź folder w galerii odpowiadający przeskanowanemu folderowi
            relative_path = os.path.relpath(scanned_folder, self.current_work_directory)
            gallery_folder = os.path.join(gallery_root, relative_path)

            if not os.path.exists(gallery_folder):
                return

            # Odśwież galerię
            self.rebuild_gallery_silent()

        except Exception as e:
            print(f"❌ Błąd refresh_gallery_after_learning: {e}")

    def rebuild_gallery_silent(self):
        """Przebudowuje galerię bez pokazywania"""
        try:
            if not self.current_work_directory:
                return

            # Uruchom skanowanie w wątku
            self.scanner_thread = ScannerWorker(self.current_work_directory)
            self.scanner_thread.progress_signal.connect(self.log_message)
            self.scanner_thread.finished_signal.connect(
                lambda: self.gallery_rebuilt_silently(None)
            )
            self.scanner_thread.start()

        except Exception as e:
            print(f"❌ Błąd rebuild_gallery_silent: {e}")

    def gallery_rebuilt_silently(self, root_html_path):
        """Obsługuje zakończenie cichej przebudowy galerii"""
        try:
            # Po skanowaniu, uruchom generowanie galerii
            if self.current_work_directory:
                # Uruchom generator galerii
                self.gallery_thread = GalleryWorker(
                    self.current_work_directory, self.GALLERY_CACHE_DIR
                )
                self.gallery_thread.progress_signal.connect(self.log_message)
                self.gallery_thread.finished_signal.connect(
                    self.on_silent_gallery_finished
                )
                self.gallery_thread.start()

        except Exception as e:
            print(f"❌ Błąd gallery_rebuilt_silently: {e}")

    def on_silent_gallery_finished(self, root_html_path):
        """Obsługuje zakończenie cichej przebudowy galerii"""
        try:
            if root_html_path:
                self.current_gallery_root_html = root_html_path
                # Odśwież widok
                self.show_gallery_in_app()

        except Exception as e:
            print(f"❌ Błąd on_silent_gallery_finished: {e}")

    def save_learning_data(self, archive_file, image_file, archive_path, image_path):
        """Zapisuje dane do nauki"""
        try:
            if not all([archive_file, image_file, archive_path, image_path]):
                return

            # Zapisz do pliku JSON
            learning_file = "learning_data.json"
            learning_data = []

            if os.path.exists(learning_file):
                try:
                    with open(learning_file, "r", encoding="utf-8") as f:
                        learning_data = json.load(f)
                except:
                    pass

            # Dodaj nowe dopasowanie
            learning_data.append(
                {
                    "archive_file": archive_file,
                    "image_file": image_file,
                    "archive_path": archive_path,
                    "image_path": image_path,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Zapisz
            with open(learning_file, "w", encoding="utf-8") as f:
                json.dump(learning_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"❌ Błąd save_learning_data: {e}")

    def check_for_file_operations(self):
        """Sprawdza czy są nowe operacje na plikach do wykonania"""
        try:
            # Sprawdź usuwanie plików
            js_code_delete = """
            (function() {
                const latestKey = localStorage.getItem('latestDelete');
                if (!latestKey) return null;
                
                const deleteData = localStorage.getItem(latestKey);
                localStorage.removeItem(latestKey);
                localStorage.removeItem('latestDelete');
                return deleteData;
            })();
            """

            self.web_view.page().runJavaScript(
                js_code_delete, self.handle_file_deletion
            )

        except Exception as e:
            print(f"❌ Błąd check_for_file_operations: {e}")

    def handle_file_deletion(self, result):
        """Obsługuje żądanie usunięcia pliku"""
        try:
            if not result:
                return

            delete_data = json.loads(result)
            if not delete_data:
                return

            file_path = delete_data.get("filePath")
            file_name = delete_data.get("fileName")

            if not file_path or not os.path.exists(file_path):
                print(f"❌ Plik nie istnieje: {file_path}")
                return

            print(f"🗑️ Usuwanie pliku: {file_name} ({file_path})")

            # Usuń plik do kosza
            self.delete_file_to_trash(file_path)

        except Exception as e:
            print(f"❌ Błąd handle_file_deletion: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd usuwania pliku: {e}")

    def delete_file_to_trash(self, file_path):
        """Usuwa plik do kosza"""
        try:
            if not file_path or not os.path.exists(file_path):
                print(f"❌ Plik nie istnieje: {file_path}")
                return

            # Usuń do kosza
            send2trash.send2trash(file_path)

            file_name = os.path.basename(file_path)
            print(f"✅ Usunięto do kosza: {file_name}")
            self.log_message(f"✅ Usunięto do kosza: {file_name}")

            # Odśwież galerię po usunięciu
            folder_path = os.path.dirname(file_path)
            self.rescan_and_rebuild_after_deletion(folder_path)

        except Exception as e:
            print(f"❌ Błąd delete_file_to_trash: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd usuwania pliku do kosza: {e}")

    def rescan_and_rebuild_after_deletion(self, folder_path):
        """Przeskanowuje i przebudowuje galerię po usunięciu"""
        try:
            if not folder_path or not os.path.exists(folder_path):
                print(f"❌ Folder nie istnieje: {folder_path}")
                return

            print(f"🔄 Odświeżanie galerii po usunięciu z folderu: {folder_path}")

            def scan_and_rebuild():
                try:
                    # Skanuj folder
                    scanner_logic.start_scanning(
                        folder_path, lambda msg: print(f"📁 {msg}")
                    )

                    # Przebuduj galerię po skanowaniu
                    QTimer.singleShot(100, self.rebuild_gallery_after_deletion)

                except Exception as e:
                    print(f"❌ Błąd w scan_and_rebuild: {e}")

            # Uruchom w wątku z opóźnieniem
            QTimer.singleShot(500, scan_and_rebuild)

        except Exception as e:
            print(f"❌ Błąd rescan_and_rebuild_after_deletion: {e}")

    def rebuild_gallery_after_deletion(self):
        """Przebudowuje galerię po usunięciu"""
        try:
            if not self.current_work_directory:
                return

            print(f"🔄 Przebudowywanie galerii po usunięciu")

            # Sprawdź czy nie ma już działających wątków
            if (self.scanner_thread and self.scanner_thread.isRunning()) or (
                self.gallery_thread and self.gallery_thread.isRunning()
            ):
                print("⏳ Inne operacje w toku, pomijam przebudowę")
                return

            # Uruchom generator galerii
            self.gallery_thread = GalleryWorker(
                self.current_work_directory, self.GALLERY_CACHE_DIR
            )
            self.gallery_thread.progress_signal.connect(lambda msg: print(f"🏗️ {msg}"))
            self.gallery_thread.finished_signal.connect(
                self.on_gallery_rebuilt_after_deletion
            )
            self.gallery_thread.start()

        except Exception as e:
            print(f"❌ Błąd rebuild_gallery_after_deletion: {e}")

    def on_gallery_rebuilt_after_deletion(self, root_html_path):
        """Obsługuje zakończenie przebudowy galerii po usunięciu"""
        try:
            if root_html_path:
                self.current_gallery_root_html = root_html_path
                print(f"✅ Galeria przebudowana po usunięciu: {root_html_path}")

                # Odśwież widok po krótkim opóźnieniu
                QTimer.singleShot(1000, self.show_gallery_in_app)
            else:
                print("❌ Nie udało się przebudować galerii po usunięciu")

        except Exception as e:
            print(f"❌ Błąd on_gallery_rebuilt_after_deletion: {e}")

    def get_original_folder_from_gallery_path(self, gallery_path):
        """Konwertuje ścieżkę galerii na oryginalną ścieżkę folderu"""
        try:
            if not gallery_path or not os.path.exists(gallery_path):
                return None

            # Znajdź główny folder galerii
            gallery_root = self.get_current_gallery_path()
            if not gallery_root:
                return None

            # Konwertuj ścieżkę
            relative_path = os.path.relpath(gallery_path, gallery_root)
            original_path = os.path.join(self.current_work_directory, relative_path)

            if os.path.exists(original_path):
                return original_path

            return None

        except Exception as e:
            print(f"❌ Błąd get_original_folder_from_gallery_path: {e}")
            return None

    def force_refresh_gallery(self):
        """Wymusza odświeżenie galerii"""
        self.rebuild_gallery_silent()

    def handle_js_function_result(self, result):
        """Obsługuje wynik funkcji JavaScript"""
        try:
            if not result:
                return

            print(f"Wynik funkcji JS: {result}")

        except Exception as e:
            print(f"❌ Błąd handle_js_function_result: {e}")

    def inject_file_operations_bridge(self):
        """Wstrzykuje kod JavaScript do obsługi operacji na plikach"""
        js_code = """
        window.handleFileOperation = function(operationData) {
            const operationKey = 'fileOperation_' + Date.now();
            localStorage.setItem(operationKey, JSON.stringify(operationData));
            localStorage.setItem('latestFileOperation', operationKey);
        };
        """
        self.web_view.page().runJavaScript(js_code)

    def show_move_files_dialog_python(self):
        """Pokazuje dialog przenoszenia plików bezpośrednio w Pythonie"""
        try:
            if not self.current_work_directory:
                QMessageBox.warning(self, "Błąd", "Nie wybrano folderu roboczego")
                return

            # Pobierz zaznaczone pliki przez JavaScript
            js_code = """
            (function() {
                const selected = [];
                document.querySelectorAll('.gallery-checkbox:checked, .file-checkbox:checked').forEach(cb => {
                    const item = cb.closest('.gallery-item, li');
                    if (item) {
                        selected.push({
                            name: cb.dataset.file || 'unknown',
                            path: cb.dataset.path || '',
                            type: cb.dataset.type || 'unknown'
                        });
                    }
                });
                return JSON.stringify(selected);
            })();
            """

            self.web_view.page().runJavaScript(
                js_code, self.handle_move_files_selection
            )

        except Exception as e:
            print(f"❌ [CRITICAL] Błąd funkcji przenoszenia: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd funkcji przenoszenia: {e}")

    def handle_move_files_selection(self, result):
        """Obsługuje wynik wyboru plików do przeniesienia - ZAWSZE PARY PLIKÓW (archiwum + podgląd)"""
        try:
            if not result:
                print("ℹ️ [INFO] Nie zaznaczono żadnych plików")
                QMessageBox.information(
                    self, "Brak plików", "Nie zaznaczono żadnych plików"
                )
                return

            selected_files = json.loads(result)
            if not selected_files:
                print("ℹ️ [INFO] Nie zaznaczono żadnych plików")
                QMessageBox.information(
                    self, "Brak plików", "Nie zaznaczono żadnych plików"
                )
                return

            # Wybierz folder docelowy
            target_folder = QFileDialog.getExistingDirectory(
                self, "Wybierz folder docelowy", self.current_work_directory
            )
            if not target_folder:
                return

            files_to_move = set()
            learning_data = self.load_learning_data()
            archive_exts = [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2", ".xz"]
            image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

            for file_info in selected_files:
                source_path = file_info.get("path", "")
                if not source_path or not os.path.exists(source_path):
                    continue
                files_to_move.add(source_path)

                folder_path = os.path.dirname(source_path)
                basename = os.path.splitext(os.path.basename(source_path))[0]
                ext = os.path.splitext(source_path)[1].lower()

                # Szukaj pary niezależnie od typu pliku
                all_files = [
                    entry.path for entry in os.scandir(folder_path) if entry.is_file()
                ]
                pair_path = None
                import scanner_logic

                if ext in archive_exts:
                    # Szukaj podglądu
                    image_files = [
                        f
                        for f in all_files
                        if os.path.splitext(f)[1].lower() in image_exts
                    ]
                    pair_path = scanner_logic.find_matching_preview_for_file(
                        basename, image_files, learning_data
                    )
                elif ext in image_exts:
                    # Szukaj archiwum
                    archive_files = [
                        f
                        for f in all_files
                        if os.path.splitext(f)[1].lower() in archive_exts
                    ]
                    for arch_path in archive_files:
                        arch_base = os.path.splitext(os.path.basename(arch_path))[0]
                        if arch_base.lower() == basename.lower():
                            pair_path = arch_path
                            break
                if pair_path and os.path.exists(pair_path):
                    files_to_move.add(pair_path)
                    self.log_message(
                        f"🔗 Dodano parę do przeniesienia: {os.path.basename(pair_path)}"
                    )

            moved_count = 0
            errors = []
            for source_path in files_to_move:
                file_name = os.path.basename(source_path)
                target_path = os.path.join(target_folder, file_name)
                try:
                    if os.path.exists(target_path):
                        print(
                            f"⚠️ [WARNING] Plik {file_name} już istnieje w folderze docelowym."
                        )
                        reply = QMessageBox.question(
                            self,
                            "Plik istnieje",
                            f"Plik {file_name} już istnieje w folderze docelowym. Zastąpić?",
                            QMessageBox.StandardButton.Yes
                            | QMessageBox.StandardButton.No,
                        )
                        if reply != QMessageBox.StandardButton.Yes:
                            continue
                    shutil.move(source_path, target_path)
                    moved_count += 1
                    self.log_message(f"✅ Przeniesiono: {file_name}")
                except Exception as e:
                    errors.append(f"Błąd przenoszenia {file_name}: {str(e)}")
                    print(f"❌ [CRITICAL] Błąd przenoszenia {file_name}: {str(e)}")

            if moved_count > 0:
                print(
                    f"ℹ️ [INFO] Przeniesiono {moved_count} plików (w tym pary archiwum+podgląd)"
                )
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Przeniesiono {moved_count} plików (w tym pary archiwum+podgląd)",
                )
                self.rebuild_gallery_silent()
            if errors:
                print("⚠️ [WARNING] Wystąpiły błędy:\n" + "\n".join(errors))
                QMessageBox.warning(
                    self, "Błędy", f"Wystąpiły błędy:\n" + "\n".join(errors)
                )
        except Exception as e:
            print(f"❌ [CRITICAL] Błąd przenoszenia plików: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd przenoszenia plików: {e}")

    def show_rename_files_dialog_python(self):
        """Dialog zmiany nazw plików bezpośrednio w Pythonie"""
        try:
            # Pobierz zaznaczone pliki
            js_code = """
            (function() {
                const selected = [];
                document.querySelectorAll('.gallery-checkbox:checked, .file-checkbox:checked').forEach(cb => {
                    selected.push({
                        name: cb.dataset.file || 'unknown',
                        path: cb.dataset.path || '',
                        type: cb.dataset.type || 'unknown',
                        basename: cb.dataset.basename || ''
                    });
                });
                return JSON.stringify(selected);
            })();
            """

            self.web_view.page().runJavaScript(
                js_code, self.handle_rename_files_selection
            )

        except Exception as e:
            print(f"❌ [CRITICAL] Błąd funkcji zmiany nazw: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd funkcji zmiany nazw: {e}")

    def handle_rename_files_selection(self, result):
        """Obsługuje zmianę nazw wybranych plików - ZAWSZE PARY"""
        try:
            if not result:
                QMessageBox.information(
                    self, "Brak plików", "Nie zaznaczono żadnych plików"
                )
                return

            selected_files = json.loads(result)
            if not selected_files:
                QMessageBox.information(
                    self, "Brak plików", "Nie zaznaczono żadnych plików"
                )
                return

            # UPROSZCZONA LOGIKA: jeśli zaznaczono 1 plik, znajdź automatycznie parę
            if len(selected_files) == 1:
                selected_file = selected_files[0]
                source_path = selected_file.get("path", "")

                if not source_path or not os.path.exists(source_path):
                    QMessageBox.warning(self, "Błąd", "Wybrany plik nie istnieje")
                    return

                # Znajdź parę dla tego pliku
                folder_path = os.path.dirname(source_path)
                basename = os.path.splitext(os.path.basename(source_path))[0]

                # Wczytaj dane uczenia się
                learning_data = self.load_learning_data()

                # Znajdź wszystkie pliki w folderze
                all_files = []
                for entry in os.scandir(folder_path):
                    if entry.is_file():
                        all_files.append(entry.path)

                # Znajdź parę
                pair_file = None
                if any(
                    source_path.lower().endswith(ext)
                    for ext in [".rar", ".zip", ".7z", ".tar", ".gz"]
                ):
                    # To archiwum, znajdź obraz
                    image_files = [
                        f
                        for f in all_files
                        if any(
                            f.lower().endswith(ext)
                            for ext in [
                                ".jpg",
                                ".jpeg",
                                ".png",
                                ".gif",
                                ".bmp",
                                ".webp",
                            ]
                        )
                    ]
                    import scanner_logic

                    pair_file = scanner_logic.find_matching_preview_for_file(
                        basename, image_files, learning_data
                    )
                else:
                    # To obraz, znajdź archiwum
                    for file_path in all_files:
                        file_basename = os.path.splitext(os.path.basename(file_path))[0]
                        if (
                            file_basename.lower() == basename.lower()
                            and file_path != source_path
                        ):
                            pair_file = file_path
                            break

                # Pobierz nową nazwę
                from PyQt6.QtWidgets import QInputDialog

                current_name = basename
                new_name, ok = QInputDialog.getText(
                    self,
                    "Zmiana nazwy pary plików",
                    f"Nowa nazwa bazowa dla pary plików (bez rozszerzenia):\nAktualnie: {current_name}",
                    text=current_name,
                )

                if not ok or not new_name.strip():
                    return

                new_name = new_name.strip()

                # Zmień nazwy obu plików
                files_to_rename = [source_path]
                if pair_file and os.path.exists(pair_file):
                    files_to_rename.append(pair_file)

                renamed_count = 0
                errors = []

                for old_path in files_to_rename:
                    file_ext = os.path.splitext(old_path)[1]
                    new_path = os.path.join(
                        os.path.dirname(old_path), f"{new_name}{file_ext}"
                    )

                    try:
                        if os.path.exists(new_path) and new_path != old_path:
                            reply = QMessageBox.question(
                                self,
                                "Plik istnieje",
                                f"Plik {os.path.basename(new_path)} już istnieje. Zastąpić?",
                                QMessageBox.StandardButton.Yes
                                | QMessageBox.StandardButton.No,
                            )
                            if reply != QMessageBox.StandardButton.Yes:
                                continue

                        if old_path != new_path:  # Tylko jeśli nazwa się zmienia
                            os.rename(old_path, new_path)
                            renamed_count += 1
                            self.log_message(
                                f"✅ Zmieniono nazwę: {os.path.basename(old_path)} → {os.path.basename(new_path)}"
                            )

                    except Exception as e:
                        errors.append(
                            f"Błąd zmiany nazwy {os.path.basename(old_path)}: {str(e)}"
                        )

                # Pokaż wyniki i odśwież
                if renamed_count > 0:
                    QMessageBox.information(
                        self,
                        "Sukces",
                        f"Zmieniono nazwy {renamed_count} plików (para archiwum+podgląd)",
                    )
                    self.rebuild_gallery_silent()

                if errors:
                    QMessageBox.warning(
                        self, "Błędy", f"Wystąpiły błędy:\n" + "\n".join(errors)
                    )

            else:
                QMessageBox.information(
                    self,
                    "Nieprawidłowy wybór",
                    "Zaznacz dokładnie JEDEN plik - para zostanie znaleziona automatycznie",
                )

        except Exception as e:
            print(f"❌ [CRITICAL] Błąd zmiany nazw: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd zmiany nazw: {e}")

    def show_create_folder_dialog_python(self):
        """Dialog tworzenia folderu bezpośrednio w Pythonie"""
        try:
            from PyQt6.QtWidgets import QInputDialog

            folder_name, ok = QInputDialog.getText(
                self, "Nowy folder", "Podaj nazwę nowego folderu:"
            )

            if not ok or not folder_name.strip():
                return

            folder_name = folder_name.strip()

            # Walidacja nazwy
            invalid_chars = '<>:"/\\|?*'
            if any(char in folder_name for char in invalid_chars):
                QMessageBox.warning(
                    self,
                    "Błędna nazwa",
                    f"Nazwa folderu zawiera niedozwolone znaki: {invalid_chars}",
                )
                return

            # Utwórz folder w aktualnej lokalizacji
            current_folder = self.current_work_directory
            new_folder_path = os.path.join(current_folder, folder_name)

            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, "Błąd", "Folder o tej nazwie już istnieje")
                return

            try:
                os.makedirs(new_folder_path, exist_ok=True)
                QMessageBox.information(
                    self, "Sukces", f"Utworzono folder: {folder_name}"
                )
                self.log_message(f"✅ Utworzono folder: {folder_name}")

                # Odśwież galerię
                self.rebuild_gallery_silent()

            except Exception as e:
                print(f"❌ [CRITICAL] Nie można utworzyć folderu: {e}")
                QMessageBox.critical(self, "Błąd", f"Nie można utworzyć folderu: {e}")

        except Exception as e:
            print(f"❌ [CRITICAL] Błąd tworzenia folderu: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd tworzenia folderu: {e}")

    def show_delete_empty_dialog_python(self):
        """Dialog usuwania pustych folderów - DEFINICJA: folder który może zawierać index.json, ale NIE zawiera plików archiwum i podglądu"""
        try:
            if not self.current_work_directory:
                QMessageBox.warning(self, "Błąd", "Nie wybrano folderu roboczego")
                return

            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć wszystkie puste foldery w:\n{self.current_work_directory}?\n\n(Pusty folder = folder zawierający tylko index.json lub całkowicie pusty)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # NOWA DEFINICJA pustego folderu
            def is_empty_folder(folder_path):
                """
                Folder jest pusty jeśli:
                - Jest całkowicie pusty, LUB
                - Zawiera tylko plik index.json (bez plików archiwum i podglądu)
                """
                try:
                    items = os.listdir(folder_path)

                    # Całkowicie pusty
                    if not items:
                        return True

                    # Zawiera tylko index.json
                    if len(items) == 1 and items[0] == "index.json":
                        return True

                    # Zawiera index.json + inne pliki - sprawdź czy są to tylko metadane
                    content_files = [item for item in items if item != "index.json"]

                    # Jeśli nie ma innych plików oprócz index.json
                    if not content_files:
                        return True

                    # Sprawdź czy są pliki archiwum lub obrazy (content)
                    for item in content_files:
                        item_path = os.path.join(folder_path, item)
                        if os.path.isfile(item_path):
                            # Sprawdź czy to plik archiwalny lub obraz
                            ext = os.path.splitext(item)[1].lower()
                            archive_exts = [
                                ".rar",
                                ".zip",
                                ".7z",
                                ".tar",
                                ".gz",
                                ".bz2",
                                ".xz",
                            ]
                            image_exts = [
                                ".jpg",
                                ".jpeg",
                                ".png",
                                ".gif",
                                ".bmp",
                                ".webp",
                            ]

                            if ext in archive_exts or ext in image_exts:
                                return False  # Zawiera content, nie jest pusty

                    # Jeśli doszliśmy tutaj, folder ma tylko pliki pomocnicze/systemowe
                    return True

                except:
                    return False

            # Usuń puste foldery
            deleted_count = 0
            errors = []

            # Idź od najgłębszych folderów
            for root, dirs, files in os.walk(
                self.current_work_directory, topdown=False
            ):
                if root == self.current_work_directory:  # Nie usuwaj głównego folderu
                    continue

                try:
                    if is_empty_folder(root):
                        # Dodatkowo sprawdź czy folder nie zawiera podfolderów
                        if not os.listdir(root) or all(
                            item == "index.json"
                            or os.path.isfile(os.path.join(root, item))
                            for item in os.listdir(root)
                        ):
                            import send2trash

                            send2trash.send2trash(root)  # Użyj kosza zamiast os.rmdir
                            deleted_count += 1
                            self.log_message(
                                f"✅ Usunięto pusty folder: {os.path.basename(root)}"
                            )

                except Exception as e:
                    errors.append(f"Błąd usuwania {os.path.basename(root)}: {str(e)}")

            # Pokaż wyniki
            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Usunięto {deleted_count} pustych folderów do kosza",
                )
                self.rebuild_gallery_silent()
            else:
                QMessageBox.information(self, "Info", "Nie znaleziono pustych folderów")

            if errors:
                QMessageBox.warning(
                    self, "Błędy", f"Wystąpiły błędy:\n" + "\n".join(errors)
                )

        except Exception as e:
            print(f"❌ [CRITICAL] Błąd usuwania pustych folderów: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd usuwania pustych folderów: {e}")

    def load_learning_data(self):
        """Wczytuje dane uczenia się z pliku JSON"""
        try:
            learning_file = "learning_data.json"
            if os.path.exists(learning_file):
                with open(learning_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"❌ [CRITICAL] Błąd wczytywania danych uczenia się: {e}")
            return []


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
