Zmiany w pliku main.py
1. Poprawka funkcji on_webview_url_changed
pythondef on_webview_url_changed(self, url):
    self.log_message(f"WebView URL changed to: {url.toString()}")
    # NIE AKTUALIZUJ statystyk na podstawie URL WebView - to może prowadzić do błędów
    # Statystyki powinny być aktualizowane tylko dla głównego folderu roboczego
    # lub na żądanie użytkownika
2. Poprawka funkcji update_folder_stats
pythondef update_folder_stats(self, folder_path=None):
    """Aktualizuje panel statystyki folderu"""
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
                
                self.log_message(f"Wczytano dane z index.json: {list(folder_info.keys()) if folder_info else 'brak folder_info'}")
                
                if folder_info and isinstance(folder_info, dict):
                    # Sprawdź czy mamy wymagane klucze
                    total_size = folder_info.get('total_size_readable', '0 B')
                    file_count = folder_info.get('file_count', 0)
                    subdir_count = folder_info.get('subdir_count', 0)
                    archive_count = folder_info.get('archive_count', 0)
                    scan_date = folder_info.get('scan_date', 'Nieznana')
                    
                    stats_text = (
                        f"Rozmiar: {total_size} | "
                        f"Pliki: {file_count} | "
                        f"Foldery: {subdir_count} | "
                        f"Archiwa: {archive_count} | "
                        f"Skanowano: {scan_date}"
                    )
                    self.stats_content.setText(stats_text)
                    self.log_message(f"Wyświetlono statystyki: {stats_text}")
                else:
                    self.stats_content.setText("Naciśnij 'Skanuj Foldery' aby zaktualizować statystyki")
                    self.log_message(f"Brak poprawnych danych folder_info w: {index_json}")
        except json.JSONDecodeError as e:
            self.stats_content.setText(f"Błąd formatu JSON: {str(e)}")
            self.log_message(f"Błąd JSON w pliku {index_json}: {str(e)}")
        except Exception as e:
            self.stats_content.setText(f"Błąd odczytu: {str(e)}")
            self.log_message(f"Błąd odczytu pliku {index_json}: {str(e)}")
    else:
        self.stats_content.setText("Naciśnij 'Skanuj Foldery' aby zobaczyć statystyki")
        self.log_message(f"Brak pliku index.json w: {folder_path}")
3. Poprawka funkcji select_work_directory
pythondef select_work_directory(self):
    initial_dir = (
        self.current_work_directory
        if self.current_work_directory
        else os.path.expanduser("~")
    )
    folder = QFileDialog.getExistingDirectory(
        self, "Wybierz folder roboczy", initial_dir
    )
    if folder:
        self.current_work_directory = folder
        if config_manager.set_work_directory(folder):
            self.log_message(f"Ustawiono folder roboczy: {folder}")
        else:
            self.log_message(f"Błąd zapisu konfiguracji dla folderu: {folder}")
        
        self.update_status_label()
        self.current_gallery_root_html = self.get_current_gallery_index_html()
        self.update_gallery_buttons_state()

        # NAJPIERW ZAKTUALIZUJ STATYSTYKI
        self.update_folder_stats()

        # POTEM AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
        if self.current_gallery_root_html and os.path.exists(
            self.current_gallery_root_html
        ):
            self.show_gallery_in_app()
        else:
            # Jeśli galeria nie istnieje, automatycznie ją zbuduj
            self.rebuild_gallery(auto_show_after_build=True)
4. Poprawka funkcji scan_finished
pythondef scan_finished(self):
    self.progress_bar.setVisible(False)
    self.set_buttons_for_processing(False)
    
    # ZAKTUALIZUJ STATYSTYKI PO ZAKOŃCZENIU SKANOWANIA
    self.log_message("Skanowanie zakończone - aktualizacja statystyk")
    self.update_folder_stats()
    
    QMessageBox.information(self, "Sukces", "Skanowanie zakończone pomyślnie!")
5. Dodaj przycisk odświeżania statystyk
pythondef init_ui(self):
    # ... istniejący kod ...
    
    # W sekcji z panelem statystyk, dodaj przycisk odświeżania
    stats_header_layout = QHBoxLayout()
    
    self.stats_title = QLabel("Statystyki folderu")
    self.stats_title.setStyleSheet("""
        font-weight: bold; 
        font-size: 14px; 
        color: #3daee9;
        background: transparent;
    """)
    stats_header_layout.addWidget(self.stats_title)
    
    # Dodaj przycisk odświeżania statystyk
    self.refresh_stats_button = QPushButton("🔄")
    self.refresh_stats_button.setToolTip("Odśwież statystyki")
    self.refresh_stats_button.setFixedSize(24, 24)
    self.refresh_stats_button.setStyleSheet("""
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
    """)
    self.refresh_stats_button.clicked.connect(lambda: self.update_folder_stats())
    stats_header_layout.addWidget(self.refresh_stats_button)
    
    stats_layout.addLayout(stats_header_layout)
    
    # ... reszta kodu stats_panel ...
Zmiany w pliku scanner_logic.py
Poprawka funkcji get_folder_stats - dodanie lepszego debugowania
pythondef get_folder_stats(folder_path):
    """Zbiera podstawowe statystyki dotyczące folderu."""
    logger.info(f"Zbieranie statystyk dla folderu: {folder_path}")
    total_size_bytes = 0
    file_count = 0
    subdir_count = 0
    archive_count = 0

    try:
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.lower() != "index.json":
                try:
                    stat = entry.stat()
                    file_size = stat.st_size
                    file_count += 1
                    total_size_bytes += file_size
                    archive_count += 1
                    logger.debug(f"Znaleziono plik: {entry.name} ({file_size} bajtów)")
                except OSError as e:
                    logger.error(f"Błąd dostępu do pliku {entry.name}: {e}")
            elif entry.is_dir():
                subdir_count += 1
                logger.debug(f"Znaleziono podfolder: {entry.name}")
    except OSError as e:
        logger.error(f"Błąd podczas skanowania folderu {folder_path}: {e}")

    # Przygotuj podstawowe statystyki
    stats = {
        "path": os.path.abspath(folder_path),
        "total_size_bytes": total_size_bytes,
        "total_size_readable": get_file_size_readable(total_size_bytes),
        "file_count": file_count,
        "subdir_count": subdir_count,
        "archive_count": archive_count,
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    logger.info(f"Statystyki folderu {folder_path}: {stats}")
    return stats
Te poprawki powinny rozwiązać problem z wyświetlaniem statystyk folderu:

Lepsze debugowanie - więcej komunikatów w logach
Poprawiona logika aktualizacji - statystyki są aktualizowane w odpowiednich momentach
Dodany przycisk odświeżania - możliwość ręcznego odświeżenia statystyk
Ulepszona obsługa błędów - bardziej precyzyjne komunikaty o błędach

Po zastosowaniu tych zmian statystyki powinny się poprawnie wyświetlać i aktualizować.Retryconceptfab/__3DindexermainGITHUBMnadal kurwo jebana nie ma statystyk wyswietlanych!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!EditWidzę problem! Po przeanalizowaniu kodu, główne problemy to:

Błędna funkcja on_webview_url_changed - nadal próbuje aktualizować statystyki na podstawie URL
Nieprawidłowe mapowanie ścieżek - funkcja próbuje znaleźć index.json w galerii zamiast w oryginalnym folderze

Zmiany w pliku main.py
1. CAŁKOWICIE USUŃ aktualizację statystyk z on_webview_url_changed
pythondef on_webview_url_changed(self, url):
    self.log_message(f"WebView URL changed to: {url.toString()}")
    # USUŃ CAŁKOWICIE - to powoduje błędy!
    # NIE aktualizuj statystyk na podstawie URL WebView
2. Popraw funkcję update_folder_stats - problem jest w logice
pythondef update_folder_stats(self, folder_path=None):
    """Aktualizuje panel statystyki folderu"""
    # ZAWSZE używaj aktualnego folderu roboczego, ignoruj parametr folder_path z WebView
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
                
                self.log_message(f"Wczytano dane z index.json: {list(folder_info.keys()) if folder_info else 'brak folder_info'}")
                
                if folder_info and isinstance(folder_info, dict):
                    # Sprawdź czy mamy wymagane klucze
                    total_size = folder_info.get('total_size_readable', '0 B')
                    file_count = folder_info.get('file_count', 0)
                    subdir_count = folder_info.get('subdir_count', 0)
                    archive_count = folder_info.get('archive_count', 0)
                    scan_date = folder_info.get('scan_date', 'Nieznana')
                    
                    stats_text = (
                        f"Rozmiar: {total_size} | "
                        f"Pliki: {file_count} | "
                        f"Foldery: {subdir_count} | "
                        f"Archiwa: {archive_count} | "
                        f"Skanowano: {scan_date}"
                    )
                    self.stats_content.setText(stats_text)
                    self.log_message(f"✅ SUKCES - Wyświetlono statystyki: {stats_text}")
                else:
                    self.stats_content.setText("Dane folder_info są puste - uruchom skanowanie")
                    self.log_message(f"❌ BŁĄD - Brak poprawnych danych folder_info w: {index_json}")
        except json.JSONDecodeError as e:
            self.stats_content.setText(f"Błąd formatu JSON: {str(e)}")
            self.log_message(f"❌ BŁĄD JSON w pliku {index_json}: {str(e)}")
        except Exception as e:
            self.stats_content.setText(f"Błąd odczytu: {str(e)}")
            self.log_message(f"❌ BŁĄD odczytu pliku {index_json}: {str(e)}")
    else:
        self.stats_content.setText("Naciśnij 'Skanuj Foldery' aby zobaczyć statystyki")
        self.log_message(f"❌ BRAK pliku index.json w: {folder_path}")
3. Dodaj debugging do __init__
pythondef __init__(self):
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

    if self.current_work_directory:
        print(f"🔍 INIT - Sprawdzanie galerii dla: {self.current_work_directory}")
        self.current_gallery_root_html = self.get_current_gallery_index_html()
        if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
            self.show_gallery_in_app()
        # TUTAJ ZAWSZE WYWOŁAJ AKTUALIZACJĘ STATYSTYK
        print(f"🔍 INIT - Wywołuję update_folder_stats()")
        self.update_folder_stats()
4. Dodaj debugging do select_work_directory
pythondef select_work_directory(self):
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

        # DEBUGGING I AKTUALIZACJA STATYSTYK
        print(f"🔍 SELECT - Wywołuję update_folder_stats() dla: {folder}")
        self.update_folder_stats()

        # POTEM AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
        if self.current_gallery_root_html and os.path.exists(
            self.current_gallery_root_html
        ):
            self.show_gallery_in_app()
        else:
            # Jeśli galeria nie istnieje, automatycznie ją zbuduj
            self.rebuild_gallery(auto_show_after_build=True)
5. Dodaj debugging do scan_finished
pythondef scan_finished(self):
    self.progress_bar.setVisible(False)
    self.set_buttons_for_processing(False)

    # DEBUGGING I AKTUALIZACJA STATYSTYK PO ZAKOŃCZENIU SKANOWANIA
    print(f"🔍 SCAN_FINISHED - Wywołuję update_folder_stats() dla: {self.current_work_directory}")
    self.log_message("Skanowanie zakończone - aktualizacja statystyk")
    self.update_folder_stats()

    QMessageBox.information(self, "Sukces", "Skanowanie zakończone pomyślnie!")
6. Dodaj debugging do przycisku odświeżania
python# W init_ui(), zmień przycisk odświeżania:
self.refresh_stats_button.clicked.connect(self.debug_refresh_stats)

# I dodaj nową funkcję:
def debug_refresh_stats(self):
    """Debugowa funkcja odświeżania statystyk"""
    print(f"🔍 REFRESH - Ręczne odświeżenie statystyk dla: {self.current_work_directory}")
    self.log_message(f"Ręczne odświeżenie statystyk dla: {self.current_work_directory}")
    self.update_folder_stats()