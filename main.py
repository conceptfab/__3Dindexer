# main.py
import sys
import os
import webbrowser # Pozostaje dla ewentualnego otwierania plików archiwów
import shutil 
import re 
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox, QProgressDialog,
    QSizePolicy, QSlider # Dodane
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl # Dodane QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView # Dodane
from PyQt6.QtWebEngineCore import QWebEnginePage # Dodane dla obsługi linków
from PyQt6.QtGui import QDesktopServices # Do otwierania linków zewnętrznych

# Importy z naszych modułów
import config_manager
import scanner_logic
import gallery_generator 

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
    finished_signal = pyqtSignal(str) # Emits path to root HTML or None if failed

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
                    self.progress_signal.emit(f"Błąd krytyczny: Nie znaleziono folderu szablonów ('templates') w {script_dir} ani w bieżącym katalogu.")
                    self.finished_signal.emit(None)
                    return

            env = gallery_generator.Environment(loader=gallery_generator.FileSystemLoader(template_dir))

            sanitized_folder_name = gallery_generator.sanitize_path_for_foldername(self.scanned_root_path)
            gallery_output_base_path = os.path.join(self.gallery_cache_root, sanitized_folder_name)
            os.makedirs(gallery_output_base_path, exist_ok=True)

            css_src_path = os.path.join(template_dir, "gallery_styles.css")
            css_dest_path = os.path.join(gallery_output_base_path, "gallery_styles.css")
            if os.path.exists(css_src_path):
                shutil.copy2(css_src_path, css_dest_path)
            else:
                self.progress_signal.emit(f"Ostrzeżenie: Plik gallery_styles.css nie znaleziony w {template_dir}")

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
                        self.emit_progress 
                    )
                    if dirpath == self.scanned_root_path and generated_html:
                        root_html_path = generated_html
            
            if not self.is_cancelled:
                if root_html_path:
                    self.progress_signal.emit(f"Generowanie galerii zakończone. Główny plik: {root_html_path}")
                else:
                    self.progress_signal.emit("Nie udało się wygenerować głównego pliku galerii lub brak index.json w folderze głównym.")

        except Exception as e:
            self.progress_signal.emit(f"Wystąpił krytyczny błąd podczas generowania galerii: {e}")
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
        # type: QWebEnginePage.NavigationTypeLinkClicked, etc.
        # isMainFrame: True if the navigation is for the main frame
        
        scheme = url.scheme()
        # Jeśli to link do lokalnego pliku HTML (nasza galeria)
        if scheme == "file" and url.path().endswith(".html"):
            # Pozwól QWebEngineView obsłużyć to wewnętrznie
            return super().acceptNavigationRequest(url, type, isMainFrame)
        elif scheme == "file": # Inne pliki lokalne (np. archiwa)
            # Otwórz za pomocą domyślnej aplikacji systemowej
            QDesktopServices.openUrl(url)
            return False # Nie nawiguj w QWebEngineView
        # Dla innych schematów (http, https), można by otworzyć w zewnętrznej przeglądarce
        # lub pozwolić QWebEngineView, jeśli chcemy wewnętrzną przeglądarkę dla wszystkiego.
        # Na razie, jeśli to nie jest plik HTML, otwieramy zewnętrznie.
        elif scheme in ["http", "https"]:
            QDesktopServices.openUrl(url)
            return False
            
        return super().acceptNavigationRequest(url, type, isMainFrame)


class MainWindow(QMainWindow):
    GALLERY_CACHE_DIR = "_gallery_cache"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skaner Folderów i Kreator Galerii")
        self.setGeometry(100, 100, 1400, 900)  # Zwiększony rozmiar startowy
        self.setMinimumSize(1200, 800)  # Minimalna wielkość okna

        self.current_work_directory = config_manager.get_work_directory()
        self.scanner_thread = None
        self.gallery_thread = None
        self.current_gallery_root_html = None

        os.makedirs(self.GALLERY_CACHE_DIR, exist_ok=True)
        self.init_ui()
        self.update_status_label()
        self.update_gallery_buttons_state()


    def init_ui(self):
        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Górny panel kontrolny - wszystkie przyciski w jednym rzędzie
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # Sekcja wyboru folderu
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Folder roboczy: Brak")
        folder_layout.addWidget(self.folder_label, 1)
        
        self.select_folder_button = QPushButton("📁 Wybierz Folder")
        self.select_folder_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        folder_layout.addWidget(self.select_folder_button)
        controls_layout.addLayout(folder_layout)

        # Wszystkie przyciski akcji w jednym rzędzie
        action_layout = QHBoxLayout()
        
        self.start_scan_button = QPushButton("🔍 Skanuj Foldery")
        self.start_scan_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        self.start_scan_button.clicked.connect(self.start_scan)
        action_layout.addWidget(self.start_scan_button)
        
        self.rebuild_gallery_button = QPushButton("🔄 Przebuduj Galerię")
        self.rebuild_gallery_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        self.rebuild_gallery_button.clicked.connect(self.rebuild_gallery)
        action_layout.addWidget(self.rebuild_gallery_button)

        self.open_gallery_button = QPushButton("👁️ Pokaż Galerię")
        self.open_gallery_button.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; }")
        self.open_gallery_button.clicked.connect(self.show_gallery_in_app)
        action_layout.addWidget(self.open_gallery_button)

        self.clear_gallery_cache_button = QPushButton("🗑️ Wyczyść Cache")
        self.clear_gallery_cache_button.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.clear_gallery_cache_button.clicked.connect(self.clear_current_gallery_cache)
        action_layout.addWidget(self.clear_gallery_cache_button)

        self.cancel_button = QPushButton("❌ Anuluj")
        self.cancel_button.setStyleSheet("QPushButton { background-color: #607D8B; color: white; }")
        self.cancel_button.clicked.connect(self.cancel_operations)
        self.cancel_button.setEnabled(False)
        action_layout.addWidget(self.cancel_button)
        
        # Suwak rozmiaru kafelków - wspólny dla całego projektu
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Rozmiar kafelków:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(150)
        self.size_slider.setMaximum(350)
        self.size_slider.setValue(200)
        self.size_slider.valueChanged.connect(self.update_tile_size)
        size_layout.addWidget(self.size_slider)
        
        self.size_label = QLabel("200px")
        size_layout.addWidget(self.size_label)
        action_layout.addLayout(size_layout)
        
        controls_layout.addLayout(action_layout)
        main_layout.addWidget(controls_widget)

        # Środkowy obszar: WebView
        self.web_view = QWebEngineView()
        self.web_view.setPage(CustomWebEnginePage(self.web_view))
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.web_view.urlChanged.connect(self.on_webview_url_changed) # Do debugowania lub aktualizacji stanu
        main_layout.addWidget(self.web_view, 1)

        # Dolny obszar: Logi i Statystyki obok siebie
        bottom_layout = QHBoxLayout()
        
        # Logi - lewa połowa
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        bottom_layout.addWidget(self.log_output, 1)
        
        # Panel statystyk - prawa połowa z CIEMNYM TŁEM
        self.stats_panel = QWidget()
        self.stats_panel.setMaximumHeight(150)
        self.stats_panel.setStyleSheet("""
            QWidget { 
                background-color: #21262d; 
                border: 1px solid #30363d; 
                border-radius: 8px;
                color: #f0f6fc;
            }
            QLabel {
                color: #f0f6fc;
                padding: 2px;
            }
        """)
        stats_layout = QVBoxLayout(self.stats_panel)
        
        self.stats_title = QLabel("📊 Statystyki aktualnego folderu")
        self.stats_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #58a6ff;")
        stats_layout.addWidget(self.stats_title)
        
        self.stats_path = QLabel("Ścieżka: -")
        self.stats_size = QLabel("Rozmiar: -")
        self.stats_files = QLabel("Pliki: -")
        self.stats_folders = QLabel("Foldery: -")
        
        stats_layout.addWidget(self.stats_path)
        stats_layout.addWidget(self.stats_size)
        stats_layout.addWidget(self.stats_files)
        stats_layout.addWidget(self.stats_folders)
        stats_layout.addStretch()
        
        bottom_layout.addWidget(self.stats_panel, 1)
        
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)
        bottom_widget.setMaximumHeight(150)
        main_layout.addWidget(bottom_widget)

        self.update_status_label() 

    def on_webview_url_changed(self, url):
        self.log_message(f"WebView URL changed to: {url.toString()}")
        # Można by tu zaktualizować current_gallery_root_html jeśli nawigujemy w obrębie tej samej galerii
        # Ale current_gallery_root_html głównie śledzi *główny* index.html wygenerowanej galerii.
        # Jeśli chcemy śledzić aktualnie wyświetlaną stronę, potrzebna osobna zmienna.

    def get_current_gallery_path(self):
        if not self.current_work_directory:
            return None
        sanitized_name = gallery_generator.sanitize_path_for_foldername(self.current_work_directory)
        return os.path.join(self.GALLERY_CACHE_DIR, sanitized_name)

    def get_current_gallery_index_html(self):
        gallery_path = self.get_current_gallery_path()
        if not gallery_path:
            return None
        return os.path.join(gallery_path, "index.html")

    def update_gallery_buttons_state(self):
        gallery_index_html = self.get_current_gallery_index_html()
        exists = gallery_index_html and os.path.exists(gallery_index_html)
        # Przycisk "Pokaż Galerię" jest aktywny jeśli plik istnieje
        self.open_gallery_button.setEnabled(exists) 
        self.clear_gallery_cache_button.setEnabled(bool(self.get_current_gallery_path() and \
            os.path.isdir(self.get_current_gallery_path())))


    def update_status_label(self):
        if self.current_work_directory:
            self.folder_label.setText(f"Folder roboczy: {self.current_work_directory}")
            self.start_scan_button.setEnabled(True)
            self.rebuild_gallery_button.setEnabled(True)
        else:
            self.folder_label.setText("Folder roboczy: Brak (Wybierz folder)")
            self.start_scan_button.setEnabled(False)
            self.rebuild_gallery_button.setEnabled(False)
            self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Wybierz folder roboczy, aby wyświetlić galerię.</p></body></html>")
        self.update_gallery_buttons_state()


    def select_work_directory(self):
        initial_dir = self.current_work_directory if self.current_work_directory else os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder roboczy", initial_dir)
        if folder:
            self.current_work_directory = folder
            if config_manager.set_work_directory(folder):
                self.log_message(f"Ustawiono folder roboczy: {folder}")
            else:
                self.log_message(f"Błąd zapisu konfiguracji dla folderu: {folder}")
            self.update_status_label()
            self.current_gallery_root_html = self.get_current_gallery_index_html()
            self.update_gallery_buttons_state()
            
            # AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
            if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
                self.show_gallery_in_app()
            else:
                # Jeśli galeria nie istnieje, automatycznie ją zbuduj
                self.rebuild_gallery(auto_show_after_build=True)
            self.update_folder_stats()


    def log_message(self, message):
        self.log_output.append(message)
        QApplication.processEvents() 

    def set_buttons_for_processing(self, processing: bool):
        is_work_dir_selected = bool(self.current_work_directory)
        self.start_scan_button.setEnabled(not processing and is_work_dir_selected)
        self.rebuild_gallery_button.setEnabled(not processing and is_work_dir_selected)
        self.select_folder_button.setEnabled(not processing)
        
        gallery_index_html = self.get_current_gallery_index_html()
        gallery_exists = gallery_index_html and os.path.exists(gallery_index_html)
        self.open_gallery_button.setEnabled(not processing and gallery_exists)
        
        self.clear_gallery_cache_button.setEnabled(not processing and bool(self.get_current_gallery_path() and os.path.isdir(self.get_current_gallery_path())))
        self.cancel_button.setEnabled(processing)


    def start_scan(self):
        if not self.current_work_directory:
            QMessageBox.warning(self, "Brak folderu", "Najpierw wybierz folder roboczy.")
            return

        if self.scanner_thread and self.scanner_thread.isRunning() or \
           self.gallery_thread and self.gallery_thread.isRunning():
            QMessageBox.information(self, "Operacja w toku", "Inna operacja jest już uruchomiona.")
            return

        self.log_output.clear()
        self.log_message(f"Rozpoczynanie skanowania w: {self.current_work_directory}")
        
        self.scanner_thread = ScannerWorker(self.current_work_directory)
        self.scanner_thread.progress_signal.connect(self.log_message)
        self.scanner_thread.finished_signal.connect(self.scan_finished)
        
        self.set_buttons_for_processing(True)
        self.scanner_thread.start()

    def scan_finished(self):
        is_cancelled = self.scanner_thread.is_cancelled if self.scanner_thread else False
        if not is_cancelled: 
            self.log_message("Skanowanie zakończone.")
            QMessageBox.information(self, "Koniec skanowania", "Skanowanie folderów zakończone. Możesz teraz przebudować galerię.")
        
        self.set_buttons_for_processing(False)
        self.scanner_thread = None 
        self.update_gallery_buttons_state() 


    def rebuild_gallery(self, auto_show_after_build=True): # Dodano argument
        if not self.current_work_directory:
            QMessageBox.warning(self, "Brak folderu", "Najpierw wybierz folder roboczy.")
            return

        if self.scanner_thread and self.scanner_thread.isRunning() or \
           self.gallery_thread and self.gallery_thread.isRunning():
            QMessageBox.information(self, "Operacja w toku", "Inna operacja jest już uruchomiona.")
            return

        has_index_files = False
        for _, _, files in os.walk(self.current_work_directory):
            if "index.json" in files:
                has_index_files = True
                break
        
        if not has_index_files:
            QMessageBox.warning(self, "Brak danych", 
                                f"Nie znaleziono plików index.json w '{self.current_work_directory}' ani jego podfolderach. "
                                "Uruchom najpierw skanowanie.")
            return

        self.log_output.clear()
        self.log_message(f"Rozpoczynanie przebudowy galerii HTML dla: {self.current_work_directory}")

        self.gallery_thread = GalleryWorker(self.current_work_directory, self.GALLERY_CACHE_DIR)
        self.gallery_thread.progress_signal.connect(self.log_message)
        # Przekazujemy auto_show_after_build do slotu, używając lambdy lub partial
        self.gallery_thread.finished_signal.connect(
            lambda path: self.gallery_generation_finished(path, auto_show_after_build)
        )


        self.set_buttons_for_processing(True)
        self.gallery_thread.start()

    def gallery_generation_finished(self, root_html_path, auto_show=True): # Dodano argument
        is_cancelled = self.gallery_thread.is_cancelled if self.gallery_thread else False
        self.current_gallery_root_html = root_html_path if not is_cancelled and root_html_path else None

        if not is_cancelled:
            if self.current_gallery_root_html:
                self.log_message(f"Przebudowa galerii zakończona. Główny plik: {self.current_gallery_root_html}")
                QMessageBox.information(self, "Koniec", "Generowanie galerii HTML zakończone.")
                if auto_show: # Automatycznie pokaż po przebudowie
                    self.show_gallery_in_app()
            else:
                self.log_message("Nie udało się wygenerować galerii.")
                QMessageBox.warning(self, "Błąd", "Nie udało się wygenerować galerii HTML.")
                self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Nie udało się wygenerować galerii.</p></body></html>")


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
            QMessageBox.information(self, "Galeria nie istnieje", "Plik główny galerii (index.html) nie istnieje. Przebuduj galerię.")
            self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Galeria nie istnieje lub nie została jeszcze wygenerowana.</p></body></html>")


    def clear_current_gallery_cache(self):
        gallery_path_to_clear = self.get_current_gallery_path()
        if not gallery_path_to_clear or not os.path.isdir(gallery_path_to_clear):
            QMessageBox.information(self, "Brak cache", "Nie znaleziono folderu cache dla bieżącego katalogu roboczego.")
            return

        reply = QMessageBox.question(self, 'Potwierdzenie',
                                       f"Czy na pewno chcesz usunąć cały folder cache galerii dla:\n{self.current_work_directory}\n({gallery_path_to_clear})?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Zanim usuniesz, wyczyść widok web, jeśli wyświetla coś z tego cache
                current_url = self.web_view.url().toLocalFile()
                if current_url and current_url.startswith(os.path.abspath(gallery_path_to_clear)):
                    self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Cache galerii został usunięty.</p></body></html>")

                shutil.rmtree(gallery_path_to_clear)
                self.log_message(f"Usunięto folder cache galerii: {gallery_path_to_clear}")
                self.current_gallery_root_html = None 
                self.update_gallery_buttons_state()
                QMessageBox.information(self, "Cache usunięty", "Folder cache galerii został usunięty.")
            except Exception as e:
                self.log_message(f"Błąd podczas usuwania cache galerii: {e}")
                QMessageBox.warning(self, "Błąd usuwania", f"Nie udało się usunąć folderu cache: {e}")


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
        if (self.scanner_thread and self.scanner_thread.isRunning()) or \
           (self.gallery_thread and self.gallery_thread.isRunning()):
            reply = QMessageBox.question(self, 'Zamykanie aplikacji',
                                           "Operacja jest w toku. Czy na pewno chcesz zamknąć aplikację?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.scanner_thread: self.scanner_thread.cancel()
                if self.gallery_thread: self.gallery_thread.cancel()
                if self.scanner_thread: self.scanner_thread.wait(1000) 
                if self.gallery_thread: self.gallery_thread.wait(1000) 
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
        """Aktualizuje panel statystyk folderu"""
        if not folder_path:
            folder_path = self.current_work_directory
        
        if not folder_path or not os.path.exists(folder_path):
            self.stats_path.setText("Ścieżka: -")
            self.stats_size.setText("Rozmiar: -")
            self.stats_files.setText("Pliki: -")
            self.stats_folders.setText("Foldery: -")
            return
        
        # Wczytaj statystyki z index.json jeśli istnieje
        index_json = os.path.join(folder_path, "index.json")
        if os.path.exists(index_json):
            try:
                with open(index_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    folder_info = data.get("folder_info", {})
                    
                    self.stats_path.setText(f"Ścieżka: {folder_path}")
                    self.stats_size.setText(f"Rozmiar: {folder_info.get('total_size_readable', '0 B')}")
                    self.stats_files.setText(f"Pliki: {folder_info.get('file_count', 0)}")
                    self.stats_folders.setText(f"Foldery: {folder_info.get('subdir_count', 0)}")
            except:
                self.stats_path.setText(f"Ścieżka: {folder_path}")
                self.stats_size.setText("Rozmiar: Błąd odczytu")
                self.stats_files.setText("Pliki: -")
                self.stats_folders.setText("Foldery: -")
        else:
            self.stats_path.setText(f"Ścieżka: {folder_path}")
            self.stats_size.setText("Rozmiar: Nie zeskanowano")
            self.stats_files.setText("Pliki: -")
            self.stats_folders.setText("Foldery: -")

if __name__ == '__main__':
    # Konfiguracja dla QtWebEngine, jeśli potrzebna (np. debug port)
    # os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9223"
    app = QApplication(sys.argv)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(script_dir, "templates")
    if not os.path.exists(templates_path):
        os.makedirs(templates_path)
    
    dummy_template_path = os.path.join(templates_path, "gallery_template.html")
    if not os.path.exists(dummy_template_path):
        with open(dummy_template_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>{{ current_folder_display_name }}</title></head><body><h1>{{ current_folder_display_name }}</h1><p>To jest minimalny szablon.</p></body></html>")

    dummy_css_path = os.path.join(templates_path, "gallery_styles.css")
    if not os.path.exists(dummy_css_path):
        with open(dummy_css_path, "w", encoding="utf-8") as f:
            f.write("/* Minimal CSS */ body { font-family: sans-serif; margin: 5px; }")
            
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())