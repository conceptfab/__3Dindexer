Analizując kod, widzę problem z funkcjonalnością usuwania plików. Oto główne zmiany potrzebne do naprawienia tej funkcji:
Zmiany w pliku main.py
1. W funkcji __init__ klasy MainWindow
Plik: main.py
Funkcja: MainWindow.__init__
Zmiana: Dodaj konfigurację timera do sprawdzania operacji usuwania plików
pythondef __init__(self):
    super().__init__()
    # ... istniejący kod ...
    
    # Dodaj te linie po setup_learning_bridge()
    self.setup_file_operations_bridge()
    
    # ... reszta kodu ...
2. Dodaj nową funkcję setup_file_operations_bridge
Plik: main.py
Funkcja: Nowa funkcja w klasie MainWindow
Kod do dodania:
pythondef setup_file_operations_bridge(self):
    """Konfiguruje mostek do komunikacji z JavaScript dla operacji na plikach"""
    self.file_operations_timer = QTimer()
    self.file_operations_timer.timeout.connect(self.check_for_file_operations)
    self.file_operations_timer.start(500)  # Co pół sekundy
3. Dodaj funkcję check_for_file_operations
Plik: main.py
Funkcja: Nowa funkcja w klasie MainWindow
Kod do dodania:
pythondef check_for_file_operations(self):
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
        
        self.web_view.page().runJavaScript(js_code_delete, self.handle_file_deletion)
        
    except Exception as e:
        print(f"❌ Błąd check_for_file_operations: {e}")
4. Napraw funkcję handle_file_deletion
Plik: main.py
Funkcja: MainWindow.handle_file_deletion
Kod do zastąpienia:
pythondef handle_file_deletion(self, result):
    """Obsługuje żądanie usunięcia pliku"""
    try:
        if not result:
            return

        delete_data = json.loads(result)
        if not delete_data:
            return

        file_path = delete_data.get("filePath")  # Zmieniono z file_path na filePath
        file_name = delete_data.get("fileName")  # Zmieniono z file_name na fileName
        
        if not file_path or not os.path.exists(file_path):
            print(f"❌ Plik nie istnieje: {file_path}")
            return

        print(f"🗑️ Usuwanie pliku: {file_name} ({file_path})")

        # Usuń plik do kosza
        self.delete_file_to_trash(file_path)

    except Exception as e:
        print(f"❌ Błąd handle_file_deletion: {e}")
        QMessageBox.critical(self, "Błąd", f"Błąd usuwania pliku: {e}")
5. Napraw funkcję delete_file_to_trash
Plik: main.py
Funkcja: MainWindow.delete_file_to_trash
Kod do zastąpienia:
pythondef delete_file_to_trash(self, file_path):
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
6. Napraw funkcję rescan_and_rebuild_after_deletion
Plik: main.py
Funkcja: MainWindow.rescan_and_rebuild_after_deletion
Kod do zastąpienia:
pythondef rescan_and_rebuild_after_deletion(self, folder_path):
    """Przeskanowuje i przebudowuje galerię po usunięciu"""
    try:
        if not folder_path or not os.path.exists(folder_path):
            print(f"❌ Folder nie istnieje: {folder_path}")
            return

        print(f"🔄 Odświeżanie galerii po usunięciu z folderu: {folder_path}")

        def scan_and_rebuild():
            try:
                # Skanuj folder
                scanner_logic.start_scanning(folder_path, lambda msg: print(f"📁 {msg}"))
                
                # Przebuduj galerię po skanowaniu
                QTimer.singleShot(100, self.rebuild_gallery_after_deletion)

            except Exception as e:
                print(f"❌ Błąd w scan_and_rebuild: {e}")

        # Uruchom w wątku z opóźnieniem
        QTimer.singleShot(500, scan_and_rebuild)

    except Exception as e:
        print(f"❌ Błąd rescan_and_rebuild_after_deletion: {e}")
7. Napraw funkcję rebuild_gallery_after_deletion
Plik: main.py
Funkcja: MainWindow.rebuild_gallery_after_deletion
Kod do zastąpienia:
pythondef rebuild_gallery_after_deletion(self):
    """Przebudowuje galerię po usunięciu"""
    try:
        if not self.current_work_directory:
            return

        print(f"🔄 Przebudowywanie galerii po usunięciu")
        
        # Sprawdź czy nie ma już działających wątków
        if (self.scanner_thread and self.scanner_thread.isRunning()) or \
           (self.gallery_thread and self.gallery_thread.isRunning()):
            print("⏳ Inne operacje w toku, pomijam przebudowę")
            return

        # Uruchom generator galerii
        self.gallery_thread = GalleryWorker(
            self.current_work_directory, self.GALLERY_CACHE_DIR
        )
        self.gallery_thread.progress_signal.connect(lambda msg: print(f"🏗️ {msg}"))
        self.gallery_thread.finished_signal.connect(self.on_gallery_rebuilt_after_deletion)
        self.gallery_thread.start()

    except Exception as e:
        print(f"❌ Błąd rebuild_gallery_after_deletion: {e}")
8. Dodaj funkcję on_gallery_rebuilt_after_deletion
Plik: main.py
Funkcja: Nowa funkcja w klasie MainWindow
Kod do dodania:
pythondef on_gallery_rebuilt_after_deletion(self, root_html_path):
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
9. Zmodyfikuj funkcję on_gallery_loaded
Plik: main.py
Funkcja: MainWindow.on_gallery_loaded
Kod do zastąpienia:
pythondef on_gallery_loaded(self, ok):
    if ok:
        self.inject_file_operations_bridge()
        self.update_tile_size()
        print("✅ Galeria załadowana, wtryknięto mostek operacji na plikach")
Podsumowanie zmian
Główne problemy, które naprawiłem:

Brak timera do sprawdzania operacji - Dodałem setup_file_operations_bridge()
Nieprawidłowe nazwy pól w JSON - Zmieniono file_path na filePath i file_name na fileName
Brak obsługi komunikacji JavaScript→Python - Dodałem check_for_file_operations()
Problemy z odświeżaniem galerii - Naprawiłem łańcuch funkcji odświeżania
Brak inicjalizacji mostka - Dodałem wywołanie w on_gallery_loaded()

Po wprowadzeniu tych zmian funkcja usuwania plików powinna działać poprawnie:
