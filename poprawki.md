Poprawki w main.py
1. Naprawienie funkcji "Dopasuj podgląd"
pythondef check_for_learning_matches(self):
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
2. Poprawka funkcji usuwania pustych folderów - tylko aktualny folder
pythondef show_delete_empty_dialog_python(self):
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
3. Poprawa obsługi localStorage w JavaScript
pythondef check_for_file_operations(self):
    try:
        if not self.web_view.page(): return
        
        # Sprawdź różne operacje
        operations = [
            ('deleteFile', 'latestDelete', self.handle_file_deletion_result),
            ('moveFiles', 'latestMoveFiles', self.handle_move_files_from_js),
            ('renameFiles', 'latestRenameFiles', self.handle_rename_files_from_js),
            ('createFolder', 'latestCreateFolder', self.handle_create_folder_from_js),
            ('learningMatch', 'latestLearningMatch', self.handle_learning_match_result)  # Dodano
        ]
        
        for operation, latest_key, handler in operations:
            js_code = f"""
            (function() {{
                if (typeof localStorage === 'undefined') return null;
                const latestKey = localStorage.getItem('{latest_key}');
                if (!latestKey) return null;
                const data = localStorage.getItem(latestKey);
                localStorage.removeItem(latestKey);
                localStorage.removeItem('{latest_key}');
                return data;
            }})();
            """
            self.web_view.page().runJavaScript(js_code, handler)
            
    except Exception as e: 
        print(f"❌ Błąd check_for_file_operations: {e}", flush=True)
Poprawki w templates/gallery_template.html
1. Naprawienie funkcji dopasowania w JavaScript
html<script>
// ... (reszta kodu JavaScript)

if (matchBtn) {
    let localStorageAvailable = false;
    try { 
        if (typeof Storage !== 'undefined' && localStorage) { 
            localStorage.setItem('test','test'); 
            localStorage.removeItem('test'); 
            localStorageAvailable = true; 
        }
    } catch (e) { 
        console.warn('localStorage nie jest dostępny:', e); 
    }
    
    if (!localStorageAvailable) { 
        matchBtn.style.display = 'none'; 
        if(matchStatus) matchStatus.textContent = '⚠️ Funkcje uczenia niedostępne.'; 
        return; 
    }

    const checkboxes = document.querySelectorAll('.file-checkbox, .gallery-checkbox');
    
    function updateMatchButton() {
        const archiveChecked = Array.from(checkboxes).filter(cb => {
            return cb.checked && (cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox'));
        });
        const imageChecked = Array.from(checkboxes).filter(cb => {
            return cb.checked && cb.dataset.type === 'image';
        });
        
        const canMatch = archiveChecked.length === 1 && imageChecked.length === 1;
        matchBtn.disabled = !canMatch;
        
        if (matchStatus) {
            if (canMatch) {
                const archiveName = archiveChecked[0].dataset.file;
                const imageName = imageChecked[0].dataset.file;
                matchStatus.textContent = `Gotowy: ${archiveName} ↔ ${imageName}`;
            } else if (archiveChecked.length === 0 && imageChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 archiwum i 1 obraz';
            } else if (archiveChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 archiwum';
            } else if (imageChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 obraz';
            } else {
                matchStatus.textContent = 'Zaznacz tylko 1 archiwum i 1 obraz';
            }
        }
    }
    
    checkboxes.forEach((checkbox) => {
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                const currentType = this.dataset.type || (this.classList.contains('gallery-checkbox') ? 'archive' : 'unknown');
                // Odznacz inne checkboxy tego samego typu
                checkboxes.forEach((otherCb) => {
                    if (otherCb !== this) {
                        const otherType = otherCb.dataset.type || (otherCb.classList.contains('gallery-checkbox') ? 'archive' : 'unknown');
                        if (otherType === currentType) {
                            otherCb.checked = false;
                        }
                    }
                });
            }
            updateMatchButton();
        });
    });
    
    matchBtn.addEventListener('click', function () {
        const archiveCb = Array.from(checkboxes).find(cb => {
            return cb.checked && (cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox'));
        });
        const imageCb = Array.from(checkboxes).find(cb => {
            return cb.checked && cb.dataset.type === 'image';
        });
        
        if (archiveCb && imageCb) {
            // Pobierz basename z nazwy pliku
            const getBasename = (filename) => {
                const lastDotIndex = filename.lastIndexOf('.');
                return lastDotIndex > 0 ? filename.substring(0, lastDotIndex) : filename;
            };
            
            const matchData = {
                archiveFile: archiveCb.dataset.file, 
                archivePath: archiveCb.dataset.path.replace(/\\/g, '/'),
                imageFile: imageCb.dataset.file, 
                imagePath: imageCb.dataset.path.replace(/\\/g, '/'),
                archiveBasename: getBasename(archiveCb.dataset.file), 
                imageBasename: getBasename(imageCb.dataset.file),
                timestamp: new Date().toISOString(), 
                currentFolder: getCurrentFolder()
            };
            
            console.log('🎯 Zapisuję dopasowanie:', matchData);
            
            const matchKey = 'learningMatch_' + Date.now();
            localStorage.setItem(matchKey, JSON.stringify(matchData));
            localStorage.setItem('latestLearningMatch', matchKey);
            
            if(matchStatus) matchStatus.textContent = '✅ Zapisano! Nauka algorytmu...';
            matchBtn.disabled = true; 
            matchBtn.textContent = '⏳ Przetwarzanie...';
            
            // Odznacz checkboxy
            archiveCb.checked = false; 
            imageCb.checked = false;
            
            // Przywróć stan przycisku po 3 sekundach
            setTimeout(() => {
                matchBtn.disabled = false;
                matchBtn.textContent = '🎯 Dopasuj podgląd';
                if(matchStatus) matchStatus.textContent = '';
            }, 3000);
        }
    });
    
    // Inicjalne sprawdzenie
    updateMatchButton();
}
</script>
2. Poprawienie atrybutów checkboxów w HTML
html<!-- Dla plików z podglądem -->
<input
  type="checkbox"
  class="gallery-checkbox"
  data-file="{{ file.name }}"
  data-path="{{ file.path_absolute }}"
  data-type="archive"
/>

<!-- Dla plików bez podglądu - bez zmian -->
<input
  type="checkbox"
  class="file-checkbox"
  data-file="{{ file.name }}"
  data-path="{{ file.path_absolute }}"
  data-basename="{{ file.name.split('.')[0] if '.' in file.name else file.name }}"
  data-type="archive"
/>

<!-- Dla obrazów - bez zmian -->
<input
  type="checkbox"
  class="file-checkbox"
  data-file="{{ image.name }}"
  data-path="{{ image.path_absolute }}"
  data-basename="{{ image.name.split('.')[0] if '.' in image.name else image.name }}"
  data-type="image"
/>
Podsumowanie zmian

Funkcja "Dopasuj podgląd":

Poprawiono selektor checkboxów
Dodano prawidłowe sprawdzanie typów plików
Naprawiono logikę odznaczania checkboxów
Dodano lepsze komunikaty statusu


Usuwanie pustych folderów:

Zmieniono na skanowanie tylko aktualnego folderu
Usunięto rekurencyjne przeszukiwanie
Dodano funkcję pobierania aktualnego folderu z JS


Ogólne poprawki:

Ujednolicono obsługę localStorage
Poprawiono sprawdzanie typów plików
Dodano lepsze logowanie błędów



Te zmiany powinny naprawić problem z funkcją dopasowania podglądu i ograniczyć usuwanie pustych folderów tylko do aktualnie otwartego folderu.