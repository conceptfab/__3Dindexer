Zmiany w pliku main.py
Funkcja check_for_learning_matches - napraw błędy localStorage
pythondef check_for_learning_matches(self):
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
Funkcja check_for_file_deletions - napraw błędy localStorage
pythondef check_for_file_deletions(self):
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
Dodaj import w gallery_generator.py
python# Na początku pliku gallery_generator.py dodaj:
import config_manager
Napraw funkcję process_single_index_json w gallery_generator.py
pythondef process_single_index_json(
    index_json_path,
    scanned_root_path,
    gallery_output_base_path,
    template_env,
    progress_callback=None,
):
    if progress_callback:
        progress_callback(f"Generowanie galerii dla: {index_json_path}")

    try:
        with open(index_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if progress_callback:
            progress_callback(f"Błąd odczytu {index_json_path}: {e}")
        return None

    current_folder_abs_path = os.path.dirname(index_json_path)
    relative_path_from_scanned_root = os.path.relpath(
        current_folder_abs_path, scanned_root_path
    )

    current_gallery_html_dir = os.path.join(
        gallery_output_base_path,
        (
            relative_path_from_scanned_root
            if relative_path_from_scanned_root != "."
            else ""
        ),
    )
    os.makedirs(current_gallery_html_dir, exist_ok=True)

    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    # Użyj inteligentnego cachowania
    if os.path.exists(output_html_file) and not should_regenerate_gallery(
        index_json_path, output_html_file
    ):
        if progress_callback:
            progress_callback(f"Galeria {output_html_file} jest aktualna, pomijam.")
        return output_html_file

    template = template_env.get_template("gallery_template.html")

    template_data = {
        "folder_info": data.get("folder_info", {}),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "subfolders": [],
        "current_folder_display_name": (
            os.path.basename(current_folder_abs_path)
            if relative_path_from_scanned_root != "."
            else os.path.basename(scanned_root_path)
        ),
        "breadcrumb_parts": [],
        "depth": 0,
    }

    gallery_root_name = os.path.basename(scanned_root_path)
    template_data["breadcrumb_parts"], template_data["depth"] = generate_breadcrumb(
        relative_path_from_scanned_root, gallery_root_name
    )

    # Subfolders - dodaj statystyki
    for entry in os.scandir(current_folder_abs_path):
        if entry.is_dir():
            if os.path.exists(os.path.join(entry.path, "index.json")):
                # Wczytaj statystyki z index.json podfolderu
                try:
                    with open(
                        os.path.join(entry.path, "index.json"), "r", encoding="utf-8"
                    ) as f:
                        subfolder_data = json.load(f)
                        folder_info = subfolder_data.get("folder_info", {})
                        template_data["subfolders"].append(
                            {
                                "name": entry.name,
                                "link": f"{entry.name}/index.html",
                                "total_size_readable": folder_info.get(
                                    "total_size_readable", "0 B"
                                ),
                                "file_count": folder_info.get("file_count", 0),
                                "subdir_count": folder_info.get("subdir_count", 0),
                            }
                        )
                except:
                    template_data["subfolders"].append(
                        {
                            "name": entry.name,
                            "link": f"{entry.name}/index.html",
                            "total_size_readable": "0 B",
                            "file_count": 0,
                            "subdir_count": 0,
                        }
                    )

    # Files with previews - używaj bezpośrednich ścieżek
    for item in data.get("files_with_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
        if item.get("preview_path_absolute"):
            copied_item["preview_relative_path"] = (
                f"file:///{item['preview_path_absolute']}"
            )

        # DODAJ KOLOR ARCHIWUM NA PODSTAWIE ROZSZERZENIA
        file_name = item.get("name", "")
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

        template_data["files_with_previews"].append(copied_item)

    # Files without previews
    for item in data.get("files_without_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"

        # DODAJ KOLOR ARCHIWUM
        file_name = item.get("name", "")
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

        template_data["files_without_previews"].append(copied_item)

    # Other images - używaj bezpośrednich ścieżek
    for item in data.get("other_images", []):
        copied_item = item.copy()
        copied_item["file_link"] = f"file:///{item['path_absolute']}"
        if item.get("path_absolute"):
            copied_item["image_relative_path"] = f"file:///{item['path_absolute']}"
        template_data["other_images"].append(copied_item)

    try:
        html_content = template.render(template_data)
        with open(output_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        if progress_callback:
            progress_callback(f"Zapisano galerię: {output_html_file}")
    except Exception as e:
        if progress_callback:
            progress_callback(f"Błąd generowania HTML dla {index_json_path}: {e}")
        return None

    return output_html_file
Dodaj alternatywny mechanizm komunikacji w main.py
pythondef setup_learning_bridge(self):
    """Konfiguruje most komunikacyjny z JavaScript dla funkcji uczenia się"""
    self.web_view.loadFinished.connect(self.inject_learning_bridge)

    # Sprawdź czy localStorage działa, jeśli nie - wyłącz timery
    test_js = """
    (function() {
        try {
            if (typeof(Storage) !== "undefined" && localStorage) {
                localStorage.setItem('test', 'test');
                localStorage.removeItem('test');
                return true;
            }
            return false;
        } catch(e) {
            return false;
        }
    })();
    """
    
    def handle_storage_test(result):
        if result:
            print("✅ localStorage jest dostępny - uruchamiam timery")
            # Timer do sprawdzania nowych dopasowań co sekundę
            self.learning_timer = QTimer()
            self.learning_timer.timeout.connect(self.check_for_learning_matches)
            self.learning_timer.start(1000)  # Co sekundę

            # Timer do sprawdzania usuwania plików
            self.delete_timer = QTimer()
            self.delete_timer.timeout.connect(self.check_for_file_deletions)
            self.delete_timer.start(1000)  # Co sekundę
        else:
            print("❌ localStorage nie jest dostępny - funkcje uczenia wyłączone")
            self.log_message("⚠️ Funkcje uczenia się wyłączone (brak dostępu do localStorage)")
    
    self.web_view.page().runJavaScript(test_js, handle_storage_test)
Zaktualizuj template JavaScript w templates/gallery_template.html
javascript// W sekcji <script> zmień obsługę błędów localStorage:

// FUNKCJONALNOŚĆ UCZENIA SIĘ ALGORYTMU
if (matchBtn) {
  // Sprawdź dostępność localStorage
  let localStorageAvailable = false;
  try {
    if (typeof(Storage) !== "undefined" && localStorage) {
      localStorage.setItem('test', 'test');
      localStorage.removeItem('test');
      localStorageAvailable = true;
    }
  } catch(e) {
    console.warn('localStorage nie jest dostępny:', e);
  }

  if (!localStorageAvailable) {
    matchBtn.style.display = 'none';
    matchStatus.textContent = '⚠️ Funkcje uczenia się są niedostępne w tym kontekście';
    return;
  }

  const checkboxes = document.querySelectorAll('.file-checkbox');

  function updateMatchButton() {
    const archiveChecked = Array.from(checkboxes).filter(
      (cb) => cb.checked && cb.dataset.type === 'archive'
    );
    const imageChecked = Array.from(checkboxes).filter(
      (cb) => cb.checked && cb.dataset.type === 'image'
    );

    // Aktywuj przycisk gdy dokładnie 1 archiwum i 1 obraz jest zaznaczony
    matchBtn.disabled = !(
      archiveChecked.length === 1 && imageChecked.length === 1
    );

    if (matchBtn.disabled) {
      matchStatus.textContent = '';
    } else {
      matchStatus.textContent = `Gotowy do dopasowania: ${archiveChecked[0].dataset.file} ↔ ${imageChecked[0].dataset.file}`;
    }
  }

  // Reszta kodu bez zmian...
}

// OBSŁUGA USUWANIA PLIKÓW OBRAZÓW - dodaj sprawdzenie localStorage
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
        if (typeof(Storage) === "undefined" || !localStorage) {
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

        // Usuń element z listy natychmiast (optymistyczne usuwanie)
        const listItem = this.closest('li');
        if (listItem) {
          listItem.style.opacity = '0.5';
          listItem.style.pointerEvents = 'none';
          this.textContent = '⏳';
          this.disabled = true;
        }
      } catch(e) {
        console.error('Błąd usuwania pliku:', e);
        alert('Wystąpił błąd podczas usuwania pliku');
      }
    }
  });
});
Podsumowanie głównych problemów i rozwiązań:

DOMException w localStorage - Dodano sprawdzenie dostępności localStorage i obsługę błędów
Brak importu config_manager - Dodano import w gallery_generator.py
Lepsze komunikaty błędów - JavaScript teraz pokazuje konkretne błędy zamiast [object DOMException]
Fallback dla niedostępnego localStorage - Aplikacja działa nawet gdy localStorage nie jest dostępny
Testowanie dostępności - Sprawdzanie czy localStorage działa przed uruchomieniem timerów

Te zmiany powinny naprawić błędy JavaScript i przywrócić działanie generowania galerii.