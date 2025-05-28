# main.py
import json
import os
# import re # Nie jest jawnie używany, ale może być w zależnościach
import shutil
import sys
# import webbrowser # Nie jest jawnie używany
from datetime import datetime

import qdarktheme # Importujemy tutaj
import send2trash
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings # Dodano QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar, # Poprawiony import, jeśli był z gallery_generator
    # QProgressDialog, # Nie jest używany
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
    QInputDialog
)

# Importy z naszych modułów
import config_manager
import gallery_generator
import scanner_logic


# --- Klasa ScannerWorker ---
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
            import traceback
            self.progress_signal.emit(f"Traceback (scan): {traceback.format_exc()}")
        finally:
            self.finished_signal.emit()

    def emit_progress(self, message):
        self.progress_signal.emit(message)

# --- Klasa GalleryWorker ---
class GalleryWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)

    def __init__(self, scanned_root_path, gallery_cache_root):
        super().__init__()
        self.scanned_root_path = scanned_root_path
        self.gallery_cache_root = gallery_cache_root
        print(f"GalleryWorker initialized for: {self.scanned_root_path}, cache: {self.gallery_cache_root}", flush=True)

    def run(self):
        root_html_path = None
        try:
            self.emit_progress(f"Rozpoczynam generowanie galerii dla: {self.scanned_root_path}")
            root_html_path = gallery_generator.generate_full_gallery(
                scanned_root_path=self.scanned_root_path,
                gallery_cache_root_dir=self.gallery_cache_root
            )
            if root_html_path and os.path.exists(root_html_path):
                self.emit_progress(f"Generowanie galerii zakończone. Główny plik: {root_html_path}")
            elif root_html_path:
                self.emit_progress(f"Funkcja generate_full_gallery zwróciła ścieżkę {root_html_path}, ale plik nie istnieje.")
                root_html_path = None
            else:
                self.emit_progress("Nie udało się wygenerować głównego pliku galerii.")
                root_html_path = None
        except Exception as e:
            self.emit_progress(f"Wystąpił krytyczny błąd podczas generowania galerii (GalleryWorker): {e}")
            import traceback
            self.emit_progress(f"Traceback (gallery): {traceback.format_exc()}")
            root_html_path = None
        finally:
            self.emit_progress(f"GalleryWorker finished. Root HTML: {root_html_path}")
            self.finished_signal.emit(root_html_path)

    def emit_progress(self, message):
        if hasattr(self, 'progress_signal') and self.progress_signal: # Bezpieczniejsze sprawdzenie
            self.progress_signal.emit(message)
        else:
            print(f"GalleryWorker Progress (no signal): {message}", flush=True)

# --- Klasa CustomWebEnginePage ---
class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Ustawienia dla localStorage
        profile = self.profile()
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        scheme = url.scheme()
        if scheme == "file" and url.path().endswith((".html", ".htm")):
            return super().acceptNavigationRequest(url, type, isMainFrame)
        elif scheme == "file":
            QDesktopServices.openUrl(url)
            return False
        elif scheme in ["http", "https"]:
            QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, type, isMainFrame)

# --- Klasa MainWindow ---
class MainWindow(QMainWindow):
    GALLERY_CACHE_DIR_NAME = "_gallery_cache"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skaner Folderów i Kreator Galerii")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        self.current_work_directory = config_manager.get_work_directory()
        self.APP_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
        self.GLOBAL_GALLERY_CACHE_ROOT_DIR = os.path.join(self.APP_DATA_DIR, self.GALLERY_CACHE_DIR_NAME)
        os.makedirs(self.GLOBAL_GALLERY_CACHE_ROOT_DIR, exist_ok=True)
        print(f"GLOBAL_GALLERY_CACHE_ROOT_DIR ustawiony na: {self.GLOBAL_GALLERY_CACHE_ROOT_DIR}", flush=True)

        self.scanner_thread = None
        self.gallery_thread = None
        self.current_gallery_root_html = None
        self.learning_timer = None
        self.file_operations_timer = None

        print(f"🔍 INIT - current_work_directory: {self.current_work_directory}", flush=True)
        self.init_ui()
        self.update_status_label()
        self.setup_learning_bridge()
        self.setup_file_operations_bridge()

        if self.current_work_directory:
            print(f"🔍 INIT - Sprawdzanie galerii dla: {self.current_work_directory}", flush=True)
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
                self.show_gallery_in_app()
            else:
                print(f"🔍 INIT - Brak istniejącej galerii dla {self.current_work_directory}, HTML: {self.current_gallery_root_html}", flush=True)
            QTimer.singleShot(1000, self.check_for_learning_matches)

    def init_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0,0,0,0); controls_layout.setSpacing(10)
        self.select_folder_button = QPushButton("📁 Wybierz Folder"); self.select_folder_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #2d5aa0; }"); self.select_folder_button.setMinimumWidth(90); self.select_folder_button.clicked.connect(self.select_work_directory); controls_layout.addWidget(self.select_folder_button)
        self.folder_label = QLabel("Folder roboczy: Brak"); self.folder_label.setStyleSheet("padding: 8px;"); controls_layout.addWidget(self.folder_label, 1)
        self.start_scan_button = QPushButton("🔍 Skanuj Foldery"); self.start_scan_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #2d5aa0; }"); self.start_scan_button.setMinimumWidth(90); self.start_scan_button.clicked.connect(self.start_scan); controls_layout.addWidget(self.start_scan_button)
        self.rebuild_gallery_button = QPushButton("🔄 Przebuduj Galerię"); self.rebuild_gallery_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #2d5aa0; }"); self.rebuild_gallery_button.setMinimumWidth(90); self.rebuild_gallery_button.clicked.connect(lambda: self.rebuild_gallery(True)); controls_layout.addWidget(self.rebuild_gallery_button)
        self.open_gallery_button = QPushButton("👁️ Pokaż Galerię"); self.open_gallery_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #2d5aa0; }"); self.open_gallery_button.setMinimumWidth(90); self.open_gallery_button.clicked.connect(self.show_gallery_in_app); controls_layout.addWidget(self.open_gallery_button)
        self.clear_gallery_cache_button = QPushButton("🗑️ Wyczyść Cache"); self.clear_gallery_cache_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #c62d42; }"); self.clear_gallery_cache_button.setMinimumWidth(90); self.clear_gallery_cache_button.clicked.connect(self.clear_current_gallery_cache); controls_layout.addWidget(self.clear_gallery_cache_button)
        main_layout.addWidget(controls_widget)

        self.progress_bar = QProgressBar() # Poprawiony import
        self.progress_bar.setVisible(False); self.progress_bar.setStyleSheet("QProgressBar { border-radius: 4px; text-align: center; height: 20px; } QProgressBar::chunk { border-radius: 4px; background-color: #3daee9; }"); main_layout.addWidget(self.progress_bar)

        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view)) # Użyj CustomWebEnginePage
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); self.web_view.urlChanged.connect(self.on_webview_url_changed); main_layout.addWidget(self.web_view, 1)

        size_control_widget = QWidget(); size_control_layout = QHBoxLayout(size_control_widget); size_control_layout.setContentsMargins(0,0,0,0); size_control_layout.setSpacing(10)
        left_widget = QWidget(); left_layout = QHBoxLayout(left_widget); left_layout.setContentsMargins(0,0,0,0); left_layout.setSpacing(10)
        self.size_label = QLabel("Rozmiar: 200px"); self.size_label.setStyleSheet("color: #ffffff; font-weight: 500; padding: 0 10px;") # Zmieniony tekst
        self.size_slider = QSlider(Qt.Orientation.Horizontal); self.size_slider.setMinimum(100); self.size_slider.setMaximum(400); self.size_slider.setValue(200); self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow); self.size_slider.setTickInterval(50); self.size_slider.valueChanged.connect(self.update_tile_size); self.size_slider.setFixedWidth(300); self.size_slider.setStyleSheet("QSlider::groove:horizontal { border: 1px solid #999999; height: 5px; background: #2d2d2d; margin: 1px 0; border-radius: 2px; } QSlider::handle:horizontal { background: #3daee9; border: 1px solid #5c5c5c; width: 14px; margin: -2px 0; border-radius: 7px; } QSlider::handle:horizontal:hover { background: #4db8f0; } QSlider::sub-page:horizontal { background: #3daee9; border-radius: 2px; }")
        left_layout.addWidget(self.size_label); left_layout.addWidget(self.size_slider); left_layout.addStretch()
        right_widget = QWidget(); right_layout = QHBoxLayout(right_widget); right_layout.setContentsMargins(0,0,0,0); right_layout.setSpacing(10)
        file_operations = [("📁➡️ Przenieś pliki", "Przenieś pliki", self.show_move_files_dialog_python), ("✏️ Zmień nazwy", "Zmień nazwy", self.show_rename_files_dialog_python), ("📁+ Nowy folder", "Nowy folder", self.show_create_folder_dialog_python), ("🗑️📁 Usuń puste", "Usuń puste", self.show_delete_empty_dialog_python), ("🔄 Odśwież", "Odśwież", self.force_refresh_gallery)]
        for text, tooltip, handler in file_operations: btn = QPushButton(text); btn.setToolTip(tooltip); btn.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; } QPushButton:hover { background-color: #2d5aa0; }"); btn.setMinimumWidth(90); btn.clicked.connect(handler); right_layout.addWidget(btn)
        size_control_layout.addWidget(left_widget); size_control_layout.addWidget(right_widget); main_layout.addWidget(size_control_widget)
        self.statusBar = QLabel(); self.statusBar.setStyleSheet("QLabel { background-color: rgba(0, 0, 0, 0.7); color: #ffffff; padding: 5px; border-top: 1px solid rgba(255, 255, 255, 0.1); selection-background-color: #3daee9; selection-color: #ffffff; }"); self.statusBar.setMinimumHeight(25); self.statusBar.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard); main_layout.addWidget(self.statusBar)

    def on_webview_url_changed(self, url):
        self.log_message(f"WebView URL changed to: {url.toString()}")
        local_path = url.toLocalFile()
        if local_path and os.path.exists(local_path) and local_path.endswith((".html", ".htm")):
            gallery_folder = os.path.dirname(local_path)
            if self.GALLERY_CACHE_DIR_NAME in gallery_folder:
                pass

    def get_specific_gallery_output_path(self):
        if not self.current_work_directory: return None
        sanitized_name = gallery_generator.sanitize_path_for_foldername(self.current_work_directory)
        return os.path.join(self.GLOBAL_GALLERY_CACHE_ROOT_DIR, sanitized_name)

    def get_current_gallery_index_html(self):
        specific_gallery_output_path = self.get_specific_gallery_output_path()
        if not specific_gallery_output_path: return None
        return os.path.join(specific_gallery_output_path, "index.html")

    def update_gallery_buttons_state(self):
        gallery_index_html_path = self.get_current_gallery_index_html()
        gallery_html_exists = bool(gallery_index_html_path and os.path.exists(gallery_index_html_path))
        self.open_gallery_button.setEnabled(gallery_html_exists)
        specific_gallery_cache_path = self.get_specific_gallery_output_path()
        gallery_cache_dir_exists = bool(specific_gallery_cache_path and os.path.isdir(specific_gallery_cache_path))
        self.clear_gallery_cache_button.setEnabled(gallery_cache_dir_exists)

    def update_status_label(self):
        if self.current_work_directory:
            self.folder_label.setText(f"Folder roboczy: {self.current_work_directory}")
            self.start_scan_button.setEnabled(True); self.rebuild_gallery_button.setEnabled(True)
        else:
            self.folder_label.setText("Folder roboczy: Brak (Wybierz folder)")
            self.start_scan_button.setEnabled(False); self.rebuild_gallery_button.setEnabled(False)
            self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Wybierz folder roboczy.</p></body></html>")
        self.update_gallery_buttons_state()

    def select_work_directory(self):
        initial_dir = self.current_work_directory if self.current_work_directory else os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder roboczy", initial_dir)
        if folder:
            print(f"🔍 SELECT - Wybrano folder: {folder}", flush=True)
            self.current_work_directory = os.path.normpath(folder)
            if config_manager.set_work_directory(self.current_work_directory):
                self.log_message(f"Ustawiono folder roboczy: {self.current_work_directory}")
            else:
                self.log_message(f"Błąd zapisu konfiguracji dla folderu: {self.current_work_directory}")
            self.update_status_label()
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
                self.log_message(f"Znaleziono istniejącą galerię dla {self.current_work_directory}. Ładuję.")
                self.show_gallery_in_app()
            else:
                self.log_message(f"Brak istniejącej galerii dla {self.current_work_directory}. Proponuję przebudowę.")
                reply = QMessageBox.question(self, "Nowy folder roboczy",
                                           f"Nie znaleziono istniejącej galerii dla folderu:\n{self.current_work_directory}\n\nCzy chcesz ją teraz zbudować?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    self.rebuild_gallery(auto_show_after_build=True)
                else:
                    self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Galeria nie zbudowana.</p></body></html>")

    def log_message(self, message, level="INFO"): # Dodano level dla spójności
        print(f"ℹ️ UI ({level}): {message}", flush=True)
        self.statusBar.setText(f"[{level}] {message}" if level != "INFO" else message)
        QApplication.processEvents()

    def set_buttons_for_processing(self, processing: bool):
        is_work_dir_selected = bool(self.current_work_directory)
        self.start_scan_button.setEnabled(not processing and is_work_dir_selected)
        self.rebuild_gallery_button.setEnabled(not processing and is_work_dir_selected)
        self.select_folder_button.setEnabled(not processing)
        self.update_gallery_buttons_state()

    def start_scan(self):
        if not self.current_work_directory: QMessageBox.warning(self, "Błąd", "Najpierw wybierz folder roboczy!"); return
        if self.scanner_thread and self.scanner_thread.isRunning(): QMessageBox.warning(self, "Błąd", "Skanowanie już trwa!"); return
        self.progress_bar.setVisible(True); self.progress_bar.setRange(0, 0)
        self.scanner_thread = ScannerWorker(self.current_work_directory)
        self.scanner_thread.progress_signal.connect(self.log_message)
        self.scanner_thread.finished_signal.connect(self.scan_finished)
        self.scanner_thread.start()
        self.set_buttons_for_processing(True)

    def scan_finished(self):
        self.progress_bar.setVisible(False)
        self.set_buttons_for_processing(False)
        self.log_message("Skanowanie zakończone.") # Zamiast QMessageBox
        reply = QMessageBox.question(self, "Skanowanie zakończone", "Czy chcesz teraz przebudować galerię HTML?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self.rebuild_gallery(auto_show_after_build=True)

    def rebuild_gallery(self, auto_show_after_build=True):
        if not self.current_work_directory: QMessageBox.warning(self, "Brak folderu", "Najpierw wybierz folder roboczy."); return
        if (self.scanner_thread and self.scanner_thread.isRunning()) or \
           (self.gallery_thread and self.gallery_thread.isRunning()):
            QMessageBox.information(self, "Operacja w toku", "Inna operacja jest już uruchomiona."); return
        
        has_index_files = False
        for _, _, files in os.walk(self.current_work_directory):
            if "index.json" in files: has_index_files = True; break
        if not has_index_files:
            QMessageBox.warning(self, "Brak danych", f"Nie znaleziono plików index.json w '{self.current_work_directory}'. Uruchom skanowanie."); return

        self.log_message(f"Rozpoczynanie przebudowy galerii HTML dla: {self.current_work_directory}")
        self.progress_bar.setVisible(True); self.progress_bar.setRange(0,0)
        self.gallery_thread = GalleryWorker(self.current_work_directory, self.GLOBAL_GALLERY_CACHE_ROOT_DIR)
        self.gallery_thread.progress_signal.connect(self.log_message)
        self.gallery_thread.finished_signal.connect(lambda path: self.gallery_generation_finished(path, auto_show_after_build))
        self.set_buttons_for_processing(True)
        self.gallery_thread.start()

    def gallery_generation_finished(self, root_html_path, auto_show=True):
        self.progress_bar.setVisible(False)
        self.current_gallery_root_html = root_html_path if root_html_path and os.path.exists(root_html_path) else None
        if self.current_gallery_root_html:
            self.log_message(f"Przebudowa galerii zakończona. Główny plik: {self.current_gallery_root_html}")
            if auto_show: self.show_gallery_in_app()
        else:
            self.log_message("Nie udało się wygenerować galerii lub zwrócony plik nie istnieje.", level="ERROR")
            QMessageBox.warning(self, "Błąd", "Nie udało się wygenerować galerii HTML. Sprawdź logi konsoli.")
            self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Błąd generowania galerii.</p></body></html>")
        self.set_buttons_for_processing(False)
        self.update_gallery_buttons_state()

    def show_gallery_in_app(self):
        gallery_index_html_path = self.get_current_gallery_index_html()
        if gallery_index_html_path and os.path.exists(gallery_index_html_path):
            abs_path = os.path.abspath(gallery_index_html_path)
            self.web_view.setUrl(QUrl.fromLocalFile(abs_path)) # To wywoła loadStarted, a potem loadFinished
            self.log_message(f"Ładowanie galerii do widoku: {abs_path}")
            # Połączenie z loadFinished jest teraz jednorazowe w on_gallery_loaded
        else:
            self.log_message(f"❌ Nie znaleziono pliku galerii: {gallery_index_html_path}", level="WARNING")
            self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Plik galerii nie istnieje.</p></body></html>")

    _on_gallery_loaded_connected = False # Flaga do jednorazowego połączenia
    def on_gallery_loaded(self, ok):
        if self._on_gallery_loaded_connected: # Rozłącz po pierwszym wywołaniu
            try: self.web_view.loadFinished.disconnect(self.on_gallery_loaded)
            except TypeError: pass
            self._on_gallery_loaded_connected = False

        if ok:
            # inject_file_operations_bridge() nie jest potrzebne, jeśli JS jest w szablonie
            self.update_tile_size()
            print("✅ Galeria załadowana", flush=True)
            self.log_message("Galeria załadowana.")
        else:
            print("❌ Błąd ładowania strony galerii do WebView.", flush=True)
            self.log_message("Błąd ładowania strony galerii.", level="ERROR")

    def clear_current_gallery_cache(self):
        gallery_path_to_clear = self.get_specific_gallery_output_path()
        if not gallery_path_to_clear or not os.path.isdir(gallery_path_to_clear):
            QMessageBox.information(self, "Brak cache", "Nie znaleziono folderu cache."); return
        reply = QMessageBox.question(self, "Potwierdzenie",
                                   f"Usunąć cache dla:\n{self.current_work_directory}\n({gallery_path_to_clear})?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                current_url = self.web_view.url().toLocalFile()
                if current_url and current_url.startswith(os.path.abspath(gallery_path_to_clear)):
                    self.web_view.setHtml("<html><body><p>Cache usunięty.</p></body></html>")
                shutil.rmtree(gallery_path_to_clear)
                self.log_message(f"Usunięto folder cache galerii: {gallery_path_to_clear}")
                self.current_gallery_root_html = None
                self.update_gallery_buttons_state()
                QMessageBox.information(self, "Cache usunięty", "Folder cache galerii został usunięty.")
            except Exception as e:
                self.log_message(f"Błąd podczas usuwania cache galerii: {e}", level="ERROR")
                QMessageBox.warning(self, "Błąd usuwania", f"Nie udało się usunąć folderu cache: {e}")

    def closeEvent(self, event):
        # Zatrzymywanie wątków przy zamykaniu
        threads_running = False
        if self.scanner_thread and self.scanner_thread.isRunning():
            threads_running = True
            self.scanner_thread.quit() # Poproś o zakończenie
        if self.gallery_thread and self.gallery_thread.isRunning():
            threads_running = True
            self.gallery_thread.quit()

        if threads_running:
            # Daj wątkom chwilę na zakończenie
            if self.scanner_thread: self.scanner_thread.wait(500) 
            if self.gallery_thread: self.gallery_thread.wait(500)
            # Można dodać QMessageBox z pytaniem, czy na pewno zamknąć, jeśli wątki nadal działają
            # Na razie zakładamy, że się zakończą lub zostaną przerwane.
        event.accept()


    def update_tile_size(self):
        size = self.size_slider.value()
        self.size_label.setText(f"Rozmiar: {size}px")
        js_code = f"""
        try {{
            var galleries = document.querySelectorAll('.gallery');
            if (galleries.length > 0) {{
                galleries.forEach(function(gallery) {{
                    gallery.style.gridTemplateColumns = 'repeat(auto-fill, minmax({size}px, 1fr))';
                }});
                if (typeof localStorage !== 'undefined') localStorage.setItem('galleryTileSize', '{size}');
            }}
        }} catch (e) {{ console.error('JS Błąd w update_tile_size:', e); }}
        """
        if self.web_view.page(): self.web_view.page().runJavaScript(js_code)

    def setup_learning_bridge(self):
        self.learning_timer = QTimer(self)
        self.learning_timer.timeout.connect(self.check_for_learning_matches)
        self.learning_timer.start(700)

    def setup_file_operations_bridge(self):
        self.file_operations_timer = QTimer(self)
        self.file_operations_timer.timeout.connect(self.check_for_file_operations)
        self.file_operations_timer.start(700)

    def check_for_learning_matches(self):
        try:
            if not self.web_view.page(): return
            js_code = """
            (function() {
                if (typeof localStorage === 'undefined') return null;
                const latestKey = localStorage.getItem('latestLearningMatch');
                if (!latestKey) return null;
                const matchData = localStorage.getItem(latestKey);
                localStorage.removeItem(latestKey);
                localStorage.removeItem('latestLearningMatch');
                return matchData;
            })();
            """
            self.web_view.page().runJavaScript(js_code, self.handle_learning_match_result)
        except Exception as e: 
            print(f"❌ Błąd check_for_learning_matches: {e}", flush=True)

    def handle_learning_match_result(self, result):
        if not result: return
        try:
            match_data = json.loads(result)
            if not match_data: return
            self.log_message(f"Odebrano dopasowanie: {match_data.get('archiveFile')} <=> {match_data.get('imageFile')}")
            self.save_learning_data_generic(match_data, "learning_data.json")
            self.apply_learning_immediately(match_data)
        except json.JSONDecodeError: print(f"❌ Błąd JSON w handle_learning_match_result: '{result}'", flush=True)
        except Exception as e: print(f"❌ Błąd handle_learning_match_result: {e}", flush=True)

    def save_learning_data_generic(self, data_to_save, filename="learning_data.json"):
        try:
            full_path = os.path.join(self.APP_DATA_DIR, filename)
            existing_data = []
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f: existing_data = json.load(f)
                    if not isinstance(existing_data, list): existing_data = []
                except json.JSONDecodeError: existing_data = []
            existing_data.append(data_to_save)
            with open(full_path, "w", encoding="utf-8") as f: json.dump(existing_data, f, indent=2, ensure_ascii=False)
            self.log_message(f"Zapisano dane do {filename}")
        except Exception as e: print(f"❌ Błąd save_learning_data_generic ({filename}): {e}", flush=True)

    def apply_learning_immediately(self, match_data):
        archive_path_str = match_data.get("archivePath")
        if not archive_path_str: self.log_message("Brak archivePath w danych.", level="WARNING"); return
        normalized_archive_path = os.path.normpath(archive_path_str)
        if not os.path.exists(normalized_archive_path):
            self.log_message(f"Ścieżka {normalized_archive_path} nie istnieje.", level="ERROR"); return
        folder_to_rescan = os.path.dirname(normalized_archive_path)
        self.log_message(f"Stosuję naukę: Przeskanuję i przebuduję dla: {folder_to_rescan}")
        self.rescan_and_rebuild_specific_folder(folder_to_rescan)

    def rescan_and_rebuild_specific_folder(self, folder_path):
        if not os.path.isdir(folder_path):
            self.log_message(f"Folder {folder_path} nie istnieje.", level="ERROR"); return
        self.log_message(f"Skanowanie folderu: {folder_path}")
        try:
            scanner_logic.start_scanning(folder_path, lambda msg: self.log_message(f"Scan ({os.path.basename(folder_path)}): {msg}"))
            self.log_message(f"Skanowanie {folder_path} zakończone. Przebudowa całej galerii.")
            self.rebuild_gallery(auto_show_after_build=True)
        except Exception as e:
            self.log_message(f"Błąd rescan_and_rebuild_specific_folder dla {folder_path}: {e}", level="ERROR")

    def check_for_file_operations(self):
        try:
            if not self.web_view.page(): return
            js_get_localstorage_item = """
            (function(keyName, latestKeyName) {
                if (typeof localStorage === 'undefined') return null;
                const latestKey = localStorage.getItem(latestKeyName);
                if (!latestKey) return null;
                const data = localStorage.getItem(latestKey);
                localStorage.removeItem(latestKey);
                localStorage.removeItem(latestKeyName);
                return data;
            })
            """
            self.web_view.page().runJavaScript(js_get_localstorage_item + "('deleteFile', 'latestDelete');", self.handle_file_deletion_result)
            self.web_view.page().runJavaScript(js_get_localstorage_item + "('moveFiles', 'latestMoveFiles');", self.handle_move_files_from_js)
            self.web_view.page().runJavaScript(js_get_localstorage_item + "('renameFiles', 'latestRenameFiles');", self.handle_rename_files_from_js)
            self.web_view.page().runJavaScript(js_get_localstorage_item + "('createFolder', 'latestCreateFolder');", self.handle_create_folder_from_js)
        except Exception as e: print(f"❌ Błąd check_for_file_operations: {e}", flush=True)

    def handle_file_deletion_result(self, result):
        if not result: return
        try:
            delete_data = json.loads(result)
            if not delete_data: return
            file_path_str = delete_data.get("filePath"); file_name = delete_data.get("fileName")
            if not file_path_str: self.log_message("Brak filePath do usunięcia.", "WARNING"); return
            normalized_file_path = os.path.normpath(file_path_str)
            if not os.path.exists(normalized_file_path): self.log_message(f"Plik {normalized_file_path} nie istnieje.", "ERROR"); return
            self.log_message(f"Odebrano usunięcie: {file_name} ({normalized_file_path})")
            self.delete_file_to_trash(normalized_file_path)
        except json.JSONDecodeError: print(f"❌ Błąd JSON handle_file_deletion_result: '{result}'", flush=True)
        except Exception as e: print(f"❌ Błąd handle_file_deletion_result: {e}", flush=True); QMessageBox.critical(self, "Błąd", f"Błąd obsługi usuwania: {e}")

    def delete_file_to_trash(self, file_path_to_delete):
        try:
            if not os.path.exists(file_path_to_delete): self.log_message(f"Plik {file_path_to_delete} już nie istnieje.", "WARNING"); return
            file_name = os.path.basename(file_path_to_delete)
            send2trash.send2trash(file_path_to_delete)
            self.log_message(f"✅ Usunięto do kosza: {file_name} ({file_path_to_delete})")
            folder_affected = os.path.dirname(file_path_to_delete)
            self.rescan_and_rebuild_specific_folder(folder_affected)
        except Exception as e: self.log_message(f"Błąd usuwania {file_path_to_delete}: {e}", "ERROR"); QMessageBox.critical(self, "Błąd", f"Błąd usuwania: {e}")

    def handle_move_files_from_js(self, result):
        if not result: return
        try:
            move_data = json.loads(result); selected_files_js = move_data.get("files", [])
            if not selected_files_js: self.log_message("Brak plików do przeniesienia z JS.", "INFO"); return
            self.log_message(f"Odebrano przeniesienie dla {len(selected_files_js)} elementów (z JS).")
            self.process_move_files_python_logic(selected_files_js)
        except json.JSONDecodeError: print(f"❌ Błąd JSON handle_move_files_from_js: '{result}'", flush=True)
        except Exception as e: print(f"❌ Błąd handle_move_files_from_js: {e}", flush=True)

    def handle_rename_files_from_js(self, result):
        if not result: return
        try:
            rename_data = json.loads(result); selected_files_js = rename_data.get("files", []); new_base_name_js = rename_data.get("newBaseName")
            if not selected_files_js or not new_base_name_js: self.log_message("Niekompletne dane do zmiany nazwy z JS.", "WARNING"); return
            self.log_message(f"Odebrano zmianę nazwy dla {len(selected_files_js)} plików na '{new_base_name_js}' (z JS).")
            self.process_rename_files_python_logic(selected_files_js, new_base_name_js)
        except json.JSONDecodeError: print(f"❌ Błąd JSON handle_rename_files_from_js: '{result}'", flush=True)
        except Exception as e: print(f"❌ Błąd handle_rename_files_from_js: {e}", flush=True)

    def handle_create_folder_from_js(self, result):
        if not result: return
        try:
            create_data = json.loads(result); parent_folder_js = create_data.get("parentFolder"); folder_name_js = create_data.get("folderName")
            if not parent_folder_js or not folder_name_js: self.log_message("Niekompletne dane do tworzenia folderu z JS.", "WARNING"); return
            actual_parent_folder = os.path.normpath(parent_folder_js) # Zakładamy, że JS podaje poprawną ścieżkę
            if not os.path.isdir(actual_parent_folder): self.log_message(f"Folder nadrzędny '{actual_parent_folder}' z JS nie istnieje.", "ERROR"); return
            self.log_message(f"Odebrano utworzenie folderu '{folder_name_js}' w '{actual_parent_folder}' (z JS).")
            self.process_create_folder_python_logic(actual_parent_folder, folder_name_js)
        except json.JSONDecodeError: print(f"❌ Błąd JSON handle_create_folder_from_js: '{result}'", flush=True)
        except Exception as e: print(f"❌ Błąd handle_create_folder_from_js: {e}", flush=True)

    def process_move_files_python_logic(self, files_to_process_info: list):
        if not self.current_work_directory: QMessageBox.warning(self, "Błąd", "Nie wybrano folderu roboczego."); return
        if not files_to_process_info: QMessageBox.information(self, "Brak plików", "Nie wybrano plików do przeniesienia."); return
        target_folder = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy", self.current_work_directory)
        if not target_folder: return
        files_to_move_final = set(); moved_count = 0; errors = []; folders_affected = set()
        for file_info in files_to_process_info:
            source_path_str = file_info.get("path", ""); source_path = os.path.normpath(source_path_str)
            if not source_path_str or not os.path.exists(source_path): self.log_message(f"Plik {source_path} nie istnieje.", "WARNING"); continue
            files_to_move_final.add(source_path)
        for path_to_move in files_to_move_final:
            file_name = os.path.basename(path_to_move); target_file_path = os.path.join(target_folder, file_name)
            try:
                if os.path.exists(target_file_path):
                    reply = QMessageBox.question(self, "Plik istnieje", f"Plik {file_name} istnieje. Zastąpić?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply != QMessageBox.StandardButton.Yes: continue
                shutil.move(path_to_move, target_file_path); moved_count += 1
                folders_affected.add(os.path.dirname(path_to_move)); folders_affected.add(target_folder)
                self.log_message(f"✅ Przeniesiono: {file_name} do {target_folder}")
            except Exception as e: errors.append(f"Błąd przenoszenia {file_name}: {str(e)}")
        if moved_count > 0:
            QMessageBox.information(self, "Sukces", f"Przeniesiono {moved_count} plików.")
            for folder in folders_affected: self.rescan_and_rebuild_specific_folder(folder)
        if errors: QMessageBox.warning(self, "Błędy", "Błędy podczas przenoszenia:\n" + "\n".join(errors))

    def process_rename_files_python_logic(self, files_to_process_info: list, new_base_name: str):
        if not files_to_process_info or not new_base_name: QMessageBox.warning(self, "Brak danych", "Brak plików lub nowej nazwy."); return
        renamed_count = 0; errors = []; folders_affected = set()
        for file_info in files_to_process_info:
            old_path_str = file_info.get("path"); old_path = os.path.normpath(old_path_str)
            if not old_path_str or not os.path.exists(old_path): self.log_message(f"Plik {old_path} nie istnieje.", "WARNING"); continue
            file_ext = os.path.splitext(old_path)[1]; new_file_path = os.path.join(os.path.dirname(old_path), f"{new_base_name}{file_ext}")
            try:
                if os.path.exists(new_file_path) and new_file_path.lower() != old_path.lower():
                    reply = QMessageBox.question(self, "Plik istnieje", f"Plik {os.path.basename(new_file_path)} istnieje. Zastąpić?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply != QMessageBox.StandardButton.Yes: continue
                if old_path.lower() != new_file_path.lower():
                    os.rename(old_path, new_file_path); renamed_count += 1
                    folders_affected.add(os.path.dirname(old_path))
                    self.log_message(f"✅ Zmieniono nazwę: {os.path.basename(old_path)} → {os.path.basename(new_file_path)}")
            except Exception as e: errors.append(f"Błąd zmiany nazwy {os.path.basename(old_path)}: {str(e)}")
        if renamed_count > 0:
            QMessageBox.information(self, "Sukces", f"Zmieniono nazwy dla {renamed_count} plików.")
            for folder in folders_affected: self.rescan_and_rebuild_specific_folder(folder)
        if errors: QMessageBox.warning(self, "Błędy", "Błędy podczas zmiany nazw:\n" + "\n".join(errors))

    def process_create_folder_python_logic(self, parent_dir_path: str, new_folder_name: str):
        invalid_chars = '<>:"/\\|?*';
        if any(char in new_folder_name for char in invalid_chars): QMessageBox.warning(self, "Błędna nazwa", f"Nazwa zawiera niedozwolone znaki: {invalid_chars}"); return
        new_folder_full_path = os.path.join(parent_dir_path, new_folder_name)
        if os.path.exists(new_folder_full_path): QMessageBox.warning(self, "Błąd", f"Folder '{new_folder_name}' już istnieje."); return
        try:
            os.makedirs(new_folder_full_path); self.log_message(f"✅ Utworzono folder: {new_folder_full_path}")
            QMessageBox.information(self, "Sukces", f"Utworzono folder: {new_folder_name}")
            self.rescan_and_rebuild_specific_folder(parent_dir_path)
        except Exception as e: self.log_message(f"Nie można utworzyć folderu '{new_folder_full_path}': {e}", "ERROR"); QMessageBox.critical(self, "Błąd", f"Nie można utworzyć: {e}")

    def force_refresh_gallery(self):
        self.log_message("Wymuszanie odświeżenia galerii...")
        self.rebuild_gallery(auto_show_after_build=True)

    def show_move_files_dialog_python(self):
        if not self.current_work_directory: QMessageBox.warning(self, "Błąd", "Nie wybrano folderu."); return
        js_code = """(function() { const s=[]; document.querySelectorAll('.gallery-checkbox:checked, .file-checkbox:checked').forEach(c => s.push({name:c.dataset.file, path:c.dataset.path, type:c.dataset.type})); return JSON.stringify(s); })();"""
        if self.web_view.page(): self.web_view.page().runJavaScript(js_code, lambda r: self.process_move_files_python_logic(json.loads(r) if r else []))

    def show_rename_files_dialog_python(self):
        if not self.current_work_directory: QMessageBox.warning(self, "Błąd", "Nie wybrano folderu."); return
        js_code = """(function() { const s=[]; document.querySelectorAll('.gallery-checkbox:checked, .file-checkbox:checked').forEach(c => s.push({name:c.dataset.file, path:c.dataset.path, type:c.dataset.type})); return JSON.stringify(s); })();"""
        if self.web_view.page(): self.web_view.page().runJavaScript(js_code, self._handle_rename_for_python_button)

    def _handle_rename_for_python_button(self, result_str):
        selected_files = json.loads(result_str) if result_str else []
        if not selected_files: QMessageBox.information(self, "Info", "Nie zaznaczono plików."); return
        new_base_name, ok = QInputDialog.getText(self, "Zmiana nazwy", "Nowa nazwa bazowa (bez rozszerzenia):")
        if ok and new_base_name.strip(): self.process_rename_files_python_logic(selected_files, new_base_name.strip())
        else: self.log_message("Anulowano zmianę nazwy.")

    def show_create_folder_dialog_python(self):
        if not self.current_work_directory: QMessageBox.warning(self, "Błąd", "Nie wybrano folderu."); return
        # Domyślnie twórz w current_work_directory, chyba że JS dostarczy inną ścieżkę (co robi przez localStorage)
        parent_for_new_folder = self.current_work_directory 
        folder_name, ok = QInputDialog.getText(self, "Nowy folder", f"Nazwa nowego folderu (w {os.path.basename(parent_for_new_folder)}):")
        if ok and folder_name.strip(): self.process_create_folder_python_logic(parent_for_new_folder, folder_name.strip())

    def show_delete_empty_dialog_python(self):
        if not self.current_work_directory: 
            QMessageBox.warning(self, "Błąd", "Nie wybrano folderu."); return
        
        # Pobierz aktualny folder z galerii zamiast całego katalogu roboczego
        current_gallery_folder = self.get_current_gallery_folder_from_js()
        if not current_gallery_folder:
            current_gallery_folder = self.current_work_directory
        
        reply = QMessageBox.question(self, "Potwierdzenie", 
                                   f"Usunąć puste foldery w:\n{current_gallery_folder}?\n(Pusty = brak plików lub tylko index.json)",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                   QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        
        deleted_count = 0; errors = []
        
        # Skanuj tylko bezpośrednie podfoldery aktualnego folderu
        try:
            for entry in os.scandir(current_gallery_folder):
                if entry.is_dir(follow_symlinks=False):
                    try:
                        dir_content = os.listdir(entry.path)
                        is_empty = not dir_content or (len(dir_content) == 1 and dir_content[0] == "index.json")
                        if is_empty:
                            self.log_message(f"Usuwam pusty folder: {entry.path}")
                            send2trash.send2trash(entry.path)
                            deleted_count += 1
                    except Exception as e: 
                        errors.append(f"Błąd {entry.name}: {str(e)}")
        except Exception as e:
            errors.append(f"Błąd skanowania {current_gallery_folder}: {str(e)}")
        
        if deleted_count > 0: 
            QMessageBox.information(self, "Sukces", f"Usunięto {deleted_count} pustych folderów.")
            self.rebuild_gallery(auto_show_after_build=True)
        else: 
            QMessageBox.information(self, "Info", "Nie znaleziono pustych folderów.")
        if errors: 
            QMessageBox.warning(self, "Błędy", "Błędy podczas usuwania:\n" + "\n".join(errors))

    def get_current_gallery_folder_from_js(self):
        """Pobiera aktualny folder z JavaScript"""
        try:
            js_code = """
            (function() {
                if (window.galleryConfig && window.galleryConfig.currentFolderAbsPath) {
                    return window.galleryConfig.currentFolderAbsPath;
                }
                return null;
            })();
            """
            # Synchroniczne wywołanie - może nie działać we wszystkich przypadkach
            # Alternatywnie można użyć callback lub promise
            return None  # Fallback - użyj current_work_directory
        except:
            return None

    def load_learning_data(self):
        try:
            learning_file_path = os.path.join(self.APP_DATA_DIR, "learning_data.json")
            if os.path.exists(learning_file_path):
                with open(learning_file_path, "r", encoding="utf-8") as f: return json.load(f)
            return []
        except Exception as e: print(f"❌ Błąd wczytywania danych uczenia: {e}", flush=True); return []


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Użyj tej metody, jeśli setup_theme("dark") sprawia problemy
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    # Możesz też spróbować:
    # qdarktheme.setup_theme("dark") # Jeśli zaktualizowałeś i problem zniknął

    app.setStyle("Fusion")

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())