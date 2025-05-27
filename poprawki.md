Zmiany w pliku templates/gallery_styles.css
Przeniesienie checkboxa na dół kafelka:
css/* CHECKBOX W GALERII - PRAWY DOLNY RÓG */
.gallery-item {
  position: relative;
}

.gallery-checkbox {
  position: absolute;
  bottom: 8px;
  right: 8px;
  width: 18px;
  height: 18px;
  z-index: 10;
  accent-color: var(--accent);
  cursor: pointer;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 3px;
  border: 1px solid var(--border);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.gallery-checkbox:checked {
  background: var(--accent);
}

/* Responsive dla checkboxów */
@media (max-width: 768px) {
  .gallery-checkbox {
    width: 16px;
    height: 16px;
    bottom: 6px;
    right: 6px;
  }
}
Zmiany w pliku main.py
Poprawiona funkcja obsługi usuwania plików z odświeżaniem:
pythondef handle_file_deletion(self, result):
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
                    original_folder = self.get_original_folder_from_gallery_path(gallery_folder)
                    
                    if original_folder:
                        print(f"🔄 Ponowne skanowanie po usunięciu: {original_folder}")
                        # Reskanuj folder natychmiast
                        QTimer.singleShot(100, lambda: self.rescan_and_rebuild_after_deletion(original_folder))
                    
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

def rescan_and_rebuild_after_deletion(self, folder_path):
    """Ponownie skanuje folder i przebudowuje galerię po usunięciu pliku"""
    try:
        import threading
        
        self.log_message(f"🔄 Aktualizacja po usunięciu pliku...")
        
        def scan_and_rebuild():
            try:
                # 1. Ponownie przeskanuj folder (aktualizuj index.json)
                scanner_logic.process_folder(
                    folder_path, 
                    lambda msg: print(f"📁 RESCAN: {msg}")
                )
                
                # 2. Przebuduj galerię w głównym wątku
                QTimer.singleShot(200, self.rebuild_gallery_after_deletion)
                
            except Exception as e:
                print(f"❌ Błąd ponownego skanowania: {e}")
                QTimer.singleShot(100, lambda: self.log_message(f"Błąd aktualizacji: {e}"))
        
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
        self.gallery_thread.finished_signal.connect(self.gallery_rebuilt_after_deletion)
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
Zmiany w pliku templates/gallery_template.html
Zaktualizowany kod JavaScript dla lepszej obsługi usuwania:
javascript// OBSŁUGA USUWANIA PLIKÓW OBRAZÓW
const deleteButtons = document.querySelectorAll('.delete-image-btn');
deleteButtons.forEach((button) => {
  button.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();

    const filePath = this.dataset.filePath;
    const fileName = this.dataset.fileName;

    if (
      confirm(`Czy na pewno chcesz usunąć plik "${fileName}" do kosza?`)
    ) {
      try {
        // Sprawdź dostępność localStorage
        if (typeof Storage === 'undefined' || !localStorage) {
          alert('Funkcja usuwania nie jest dostępna w tym kontekście');
          return;
        }

        // Komunikacja z PyQt przez localStorage
        const deleteData = {
          action: 'deleteFile',
          filePath: filePath,
          fileName: fileName,
          timestamp: new Date().toISOString(),
        };

        console.log('🗑️ Usuwanie pliku:', deleteData);

        // Zapisz do localStorage
        const deleteKey = 'deleteFile_' + Date.now();
        localStorage.setItem(deleteKey, JSON.stringify(deleteData));
        localStorage.setItem('latestDelete', deleteKey);

        // Wyłącz przycisk i pokaż status
        this.textContent = '⏳';
        this.disabled = true;
        this.style.opacity = '0.5';
        
        // Pokaż komunikat o przetwarzaniu
        const statusDiv = document.createElement('div');
        statusDiv.style.cssText = `
          position: fixed; top: 20px; right: 20px; z-index: 9999;
          background: var(--warning); color: white; padding: 12px 20px;
          border-radius: 8px; font-weight: 500; box-shadow: var(--shadow);
        `;
        statusDiv.textContent = `⏳ Usuwanie "${fileName}"...`;
        document.body.appendChild(statusDiv);
        
        // Usuń komunikat po 5 sekundach
        setTimeout(() => {
          if (statusDiv.parentNode) {
            statusDiv.parentNode.removeChild(statusDiv);
          }
        }, 5000);

      } catch (e) {
        console.error('Błąd usuwania pliku:', e);
        alert('Wystąpił błąd podczas usuwania pliku');
      }
    }
  });
});
Zmiany w pliku scanner_logic.py
Dodaj funkcję do szybkiego ponownego skanowania:
pythondef quick_rescan_folder(folder_path, progress_callback=None):
    """Szybkie ponowne skanowanie folderu po modyfikacji plików"""
    logger.info(f"Szybkie ponowne skanowanie: {folder_path}")
    
    if progress_callback:
        progress_callback(f"Ponowne skanowanie: {folder_path}")
    
    # Wykorzystaj istniejącą funkcję process_folder
    return process_folder(folder_path, progress_callback)
Podsumowanie zmian
1. Przeniesienie checkboxów

Checkbox teraz znajduje się w prawym dolnym rogu kafelka
Dodano cień dla lepszej widoczności
Zachowano responsywność

2. Poprawiona obsługa usuwania

Po usunięciu pliku następuje natychmiastowe ponowne skanowanie folderu (rescan_and_rebuild_after_deletion)
Aktualizacja pliku index.json przez ponowne wywołanie scanner_logic.process_folder
Przebudowa galerii HTML z nową strukturą plików
Automatyczne odświeżenie widoku w przeglądarce

3. Lepsze komunikaty użytkownika

Powiadomienia o postępie usuwania
Komunikaty o sukcesie operacji
Obsługa błędów z możliwością przywrócenia stanu

4. Optymalizacja wydajności

Używanie QTimer dla operacji w głównym wątku
Threading dla operacji I/O
Sprawdzanie czy proces już nie jest uruchomiony

Te zmiany zapewnią, że po usunięciu pliku galeria zostanie automatycznie zaktualizowana z aktualną strukturą plików, a checkboxy będą umieszczone w prawym dolnym rogu kafelków.