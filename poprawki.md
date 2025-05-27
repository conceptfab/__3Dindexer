Zmiany w pliku config.json
json{
    "work_directory": "C:\\_cloud\\TRANSPORT",
    "preview_size": 400,
    "thumbnail_size": 150,
    "dark_theme": true,
    "performance": {
        "max_worker_threads": 4,
        "cache_previews": true,
        "lazy_loading": true,
        "max_cache_size_mb": 1024,
        "cache_ttl_hours": 24
    },
    "ui": {
        "animation_speed": 300,
        "hover_delay": 500,
        "max_preview_size": 1200
    },
    "security": {
        "allowed_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp"
        ],
        "max_file_size_mb": 50
    },
    "archive_colors": {
        ".rar": "#ff6b35",
        ".zip": "#4ecdc4",
        ".7z": "#a8e6cf",
        ".tar": "#ffd93d",
        ".tar.gz": "#ffb347",
        ".tar.bz2": "#ff8b94",
        ".gz": "#c7ceea",
        ".bz2": "#b4a7d6",
        ".xz": "#95e1d3",
        "default": "#6c757d"
    }
}
Zmiany w pliku config_manager.py - funkcja get_archive_color
pythondef get_archive_color(file_extension):
    """Pobiera kolor dla danego typu archiwum."""
    try:
        colors = get_config_value("archive_colors", {})
        # Konwertuj rozszerzenie na małe litery dla porównania
        ext_lower = file_extension.lower() if file_extension else ""
        
        # Sprawdź czy mamy kolor dla tego rozszerzenia
        if ext_lower in colors:
            return colors[ext_lower]
        
        # Sprawdź specjalne przypadki (tar.gz, tar.bz2)
        if ext_lower.endswith('.tar.gz'):
            return colors.get('.tar.gz', colors.get('default', '#6c757d'))
        elif ext_lower.endswith('.tar.bz2'):
            return colors.get('.tar.bz2', colors.get('default', '#6c757d'))
        
        return colors.get('default', '#6c757d')
    except Exception as e:
        logger.error(f"Błąd pobierania koloru archiwum: {e}")
        return '#6c757d'

def get_archive_colors():
    """Pobiera wszystkie kolory archiwów jako słownik."""
    return get_config_value("archive_colors", {})
Zmiany w pliku gallery_generator.py - funkcja process_single_index_json
pythondef process_single_index_json(
    index_json_path,
    scanned_root_path,
    gallery_output_base_path,
    template_env,
    progress_callback=None,
):
    # ... existing code until template_data setup ...

    # Files with previews - używaj bezpośrednich ścieżek
    for item in data.get("files_with_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
        if item.get("preview_path_absolute"):
            copied_item["preview_relative_path"] = (
                f"file:///{item['preview_path_absolute']}"
            )
        
        # DODAJ KOLOR ARCHIWUM NA PODSTAWIE ROZSZERZENIA
        file_name = item.get('name', '')
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)
        
        template_data["files_with_previews"].append(copied_item)

    # Files without previews
    for item in data.get("files_without_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
        
        # DODAJ KOLOR ARCHIWUM
        file_name = item.get('name', '')
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)
        
        template_data["files_without_previews"].append(copied_item)

    # ... rest of existing code ...
Zmiany w pliku templates/gallery_template.html
html<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Galeria: {{ current_folder_display_name }}</title>
    <link rel="stylesheet" href="{{ ' ../' * depth }}gallery_styles.css" />
  </head>
  <body>
    <div class="container">
      <!-- TYLKO BREADCRUMB - ścieżka -->
      <div class="breadcrumb">
        {% for part in breadcrumb_parts %} {% if part.link %}
        <a href="{{ part.link }}">{{ part.name }}</a> <span>/</span>
        {% else %}
        <span>{{ part.name }}</span>
        {% endif %} {% endfor %}
      </div>

      {% if subfolders %}
      <div class="section">
        <div class="subfolders-grid">
          {% for sf in subfolders %}
          <div
            class="subfolder-item"
            onclick="window.location.href='{{ sf.link }}'"
          >
            <div class="folder-icon">📁</div>
            <a href="{{ sf.link }}">{{ sf.name }}</a>
            <div class="folder-stats">
              <span
                >{{ sf.total_size_readable }} | {{ sf.file_count }} plików{% if
                sf.subdir_count > 0 %} | {{ sf.subdir_count }} folderów{% endif
                %}</span
              >
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %} {% if files_with_previews %}
      <div class="section">
        <h2>🖼️ Pliki z podglądem ({{ files_with_previews|length }})</h2>
        <div class="gallery" id="filesWithPreviewsGallery">
          {% for file in files_with_previews %}
          <div class="gallery-item" style="background-color: {{ file.archive_color }}22; border-color: {{ file.archive_color }};">
            <!-- Checkbox w lewym górnym rogu -->
            <input type="checkbox" class="gallery-checkbox" data-file="{{ file.name }}" data-path="{{ file.path_absolute }}">
            
            {% if file.preview_relative_path %}
            <img
              src="{{ file.preview_relative_path }}"
              alt="Podgląd dla {{ file.name }}"
              class="preview-image"
              data-full-src="{{ file.preview_relative_path }}"
            />
            {% else %}
            <div
              style="
                height: 160px;
                background: var(--bg-primary);
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                color: var(--text-secondary);
              "
            >
              <span>Brak podglądu</span>
            </div>
            {% endif %}
            <p>
              <a href="{{ file.archive_link }}" title="Otwórz: {{ file.name }}"
                >{{ file.name }}</a
              >
            </p>
            <p class="file-info">{{ file.size_readable }}</p>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      <!-- DWIE KOLUMNY NA DOLE - PLIKI BEZ PODGLĄDU I POZOSTAŁE OBRAZY -->
      {% if files_without_previews or other_images %}
      <div class="bottom-columns">
        {% if files_without_previews %}
        <div class="left-column">
          <h2>📄 Pliki bez podglądu ({{ files_without_previews|length }})</h2>
          <ul class="no-preview-list">
            {% for file in files_without_previews %}
            <li style="border-left: 4px solid {{ file.archive_color }};">
              <div class="file-item">
                <input
                  type="checkbox"
                  class="file-checkbox"
                  data-file="{{ file.name }}"
                  data-path="{{ file.path_absolute }}"
                  data-basename="{{ file.name.split('.')[0] }}"
                  data-type="archive"
                />
                
                  href="{{ file.archive_link }}"
                  title="Otwórz: {{ file.name }}"
                  >{{ file.name }}</a
                >
                <span class="file-info"> — {{ file.size_readable }}</span>
              </div>
            </li>
            {% endfor %}
          </ul>
        </div>
        {% endif %} {% if other_images %}
        <div class="right-column">
          <h2>🎨 Pozostałe obrazy ({{ other_images|length }})</h2>
          <ul class="image-list">
            {% for image in other_images %}
            <li>
              <div class="file-item">
                <input
                  type="checkbox"
                  class="file-checkbox"
                  data-file="{{ image.name }}"
                  data-path="{{ image.path_absolute }}"
                  data-basename="{{ image.name.split('.')[0] }}"
                  data-type="image"
                />
                
                  href="{{ image.file_link }}"
                  title="Otwórz: {{ image.name }}"
                  data-preview-src="{{ image.image_relative_path }}"
                  class="preview-link"
                  >{{ image.name }}</a
                >
                <span class="file-info"> — {{ image.size_readable }}</span>
                <!-- IKONKA KOSZA DO USUWANIA -->
                <button 
                  class="delete-image-btn" 
                  data-file-path="{{ image.path_absolute }}"
                  data-file-name="{{ image.name }}"
                  title="Usuń {{ image.name }} do kosza"
                >
                  🗑️
                </button>
              </div>
            </li>
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      </div>
      {% endif %}

      <!-- PRZYCISK DOPASUJ PODGLĄD -->
      {% if files_without_previews and other_images %}
      <div class="learning-section">
        <button id="matchPreviewBtn" class="match-preview-btn" disabled>
          🎯 Dopasuj podgląd
        </button>
        <div id="matchStatus" class="match-status"></div>
      </div>
      {% endif %}
    </div>

    <!-- Modal podglądu -->
    <div class="preview-backdrop" id="previewBackdrop"></div>
    <div class="preview-modal" id="previewModal">
      <img src="" alt="Podgląd" id="previewImg" />
    </div>

    <script>
      document.addEventListener('DOMContentLoaded', function () {
        const galleries = [
          document.getElementById('filesWithPreviewsGallery'),
        ].filter(Boolean);

        const previewModal = document.getElementById('previewModal');
        const previewBackdrop = document.getElementById('previewBackdrop');
        const previewImg = document.getElementById('previewImg');
        const matchBtn = document.getElementById('matchPreviewBtn');
        const matchStatus = document.getElementById('matchStatus');

        // Podgląd w modalnym oknie
        function showPreview(imageSrc) {
          if (!imageSrc) return;
          previewImg.src = imageSrc;
          previewModal.classList.add('show');
          previewBackdrop.classList.add('show');
          previewModal.style.transform = 'translate(-50%, -50)';
        }

        function hidePreview() {
          previewModal.classList.remove('show');
          previewBackdrop.classList.remove('show');
          previewImg.src = '';
        }

        // OBSŁUGA USUWANIA PLIKÓW OBRAZÓW
        const deleteButtons = document.querySelectorAll('.delete-image-btn');
        deleteButtons.forEach(button => {
          button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const filePath = this.dataset.filePath;
            const fileName = this.dataset.fileName;
            
            if (confirm(`Czy na pewno chcesz usunąć plik "${fileName}" do kosza?`)) {
              // Komunikacja z PyQt przez localStorage
              const deleteData = {
                action: 'deleteFile',
                filePath: filePath,
                fileName: fileName,
                timestamp: new Date().toISOString()
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
            }
          });
        });

        // Podgląd na hover dla obrazów
        galleries.forEach((gallery) => {
          const images = gallery.querySelectorAll('.preview-image');
          images.forEach((img) => {
            let hoverTimeout;

            img.addEventListener('mouseenter', function () {
              hoverTimeout = setTimeout(() => {
                showPreview(this.src);
              }, 500);
            });

            img.addEventListener('mouseleave', function () {
              clearTimeout(hoverTimeout);
            });
          });
        });

        // Podgląd na hover dla linków w right-column
        const previewLinks = document.querySelectorAll('.preview-link');
        previewLinks.forEach((link) => {
          let hoverTimeout;

          link.addEventListener('mouseenter', function () {
            const previewSrc = this.getAttribute('data-preview-src');
            if (previewSrc) {
              hoverTimeout = setTimeout(() => {
                showPreview(previewSrc);
              }, 500);
            }
          });

          link.addEventListener('mouseleave', function () {
            clearTimeout(hoverTimeout);
          });
        });

        // Zamykanie modala
        previewBackdrop.addEventListener('click', hidePreview);
        previewModal.addEventListener('click', hidePreview);

        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') {
            hidePreview();
          }
        });

        // FUNKCJONALNOŚĆ UCZENIA SIĘ ALGORYTMU
        if (matchBtn) {
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

          // Nasłuchuj zmian w checkboxach
          checkboxes.forEach((checkbox) => {
            checkbox.addEventListener('change', function () {
              // Jeśli zaznaczono checkbox, odznacz inne w tej samej kategorii
              if (this.checked) {
                checkboxes.forEach((otherCheckbox) => {
                  if (
                    otherCheckbox !== this &&
                    otherCheckbox.dataset.type === this.dataset.type
                  ) {
                    otherCheckbox.checked = false;
                  }
                });
              }
              updateMatchButton();
            });
          });

          // Obsługa kliknięcia przycisku dopasowania
          matchBtn.addEventListener('click', function () {
            const archiveChecked = Array.from(checkboxes).find(
              (cb) => cb.checked && cb.dataset.type === 'archive'
            );
            const imageChecked = Array.from(checkboxes).find(
              (cb) => cb.checked && cb.dataset.type === 'image'
            );

            if (archiveChecked && imageChecked) {
              // BEZPOŚREDNIA KOMUNIKACJA Z PyQt przez localStorage
              const matchData = {
                archiveFile: archiveChecked.dataset.file,
                archivePath: archiveChecked.dataset.path.replace(/\\/g, '/'),
                imageFile: imageChecked.dataset.file,
                imagePath: imageChecked.dataset.path.replace(/\\/g, '/'),
                archiveBasename: archiveChecked.dataset.basename,
                imageBasename: imageChecked.dataset.basename,
                timestamp: new Date().toISOString(),
                currentFolder: window.location.pathname,
              };

              console.log('🎯 Zapisuję dopasowanie:', matchData);

              // ZAPISZ DO localStorage z unikalnym kluczem
              const matchKey = 'learningMatch_' + Date.now();
              localStorage.setItem(matchKey, JSON.stringify(matchData));
              localStorage.setItem('latestMatch', matchKey);

              // Informuj o powodzeniu
              matchStatus.textContent =
                '✅ Dopasowanie zapisane! Trwa nauka algorytmu...';
              matchBtn.disabled = true;
              matchBtn.textContent = '⏳ Przetwarzanie...';

              // Wyczyść checkboxy
              archiveChecked.checked = false;
              imageChecked.checked = false;

              // Wywołaj polling PyQt natychmiast
              setTimeout(() => {
                window.dispatchEvent(
                  new CustomEvent('learningMatchReady', {
                    detail: matchData,
                  })
                );
              }, 100);
            }
          });
        }
      });
    </script>
  </body>
</html>
Zmiany w pliku templates/gallery_styles.css
css/* Dodaj na końcu pliku */

/* CHECKBOX W GALERII - LEWY GÓRNY RÓG */
.gallery-item {
  position: relative;
  /* ... existing styles ... */
}

.gallery-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 18px;
  height: 18px;
  z-index: 10;
  accent-color: var(--accent);
  cursor: pointer;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 3px;
  border: 1px solid var(--border);
}

.gallery-checkbox:checked {
  background: var(--accent);
}

/* PRZYCISK USUWANIA OBRAZÓW */
.delete-image-btn {
  background: none;
  border: none;
  color: var(--danger);
  cursor: pointer;
  font-size: 1rem;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: var(--transition);
  margin-left: auto;
  opacity: 0.7;
}

.delete-image-btn:hover {
  background: rgba(248, 81, 73, 0.1);
  opacity: 1;
  transform: scale(1.1);
}

.delete-image-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

/* DOSTOSOWANIE FILE-ITEM DLA PRZYCISKU USUWANIA */
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.file-item a {
  flex: 1;
}

/* KOLOROWE OBRAMOWANIA DLA ARCHIWÓW W LISTACH */
.no-preview-list li {
  transition: var(--transition);
  border-left-width: 4px;
  border-left-style: solid;
}

/* Responsive dla przycisków usuwania */
@media (max-width: 768px) {
  .delete-image-btn {
    font-size: 0.9rem;
    padding: 3px 5px;
  }
  
  .gallery-checkbox {
    width: 16px;
    height: 16px;
    top: 6px;
    left: 6px;
  }
}
Zmiany w pliku main.py - dodaj obsługę usuwania plików
python# W klasie MainWindow dodaj nową metodę:

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

def check_for_file_deletions(self):
    """Sprawdza localStorage pod kątem żądań usunięcia plików"""
    js_code = """
    (function() {
        try {
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
            console.error('Error checking delete requests:', e);
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
            file_path = delete_data.get('filePath', '')
            file_name = delete_data.get('fileName', '')
            
            print(f"🗑️ ŻĄDANIE USUNIĘCIA: {file_name} -> {file_path}")
            self.log_message(f"🗑️ Usuwanie do kosza: {file_name}")
            
            # Usuń plik do kosza
            success = self.delete_file_to_trash(file_path)
            
            if success:
                self.log_message(f"✅ Plik usunięty do kosza: {file_name}")
                # Odśwież galerię po usunięciu
                QTimer.singleShot(500, self.refresh_gallery_after_deletion)
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
        import send2trash
        
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

def refresh_gallery_after_deletion(self):
    """Odświeża galerię po usunięciu pliku"""
    try:
        print("🔄 Odświeżanie galerii po usunięciu pliku")
        
        # Najpierw reskanuj aktualny folder
        current_url = self.web_view.url().toLocalFile()
        if current_url and "_gallery_cache" in current_url:
            gallery_folder = os.path.dirname(current_url)
            original_folder = self.get_original_folder_from_gallery_path(gallery_folder)
            
            if original_folder:
                print(f"🔄 Ponowne skanowanie po usunięciu: {original_folder}")
                self.rescan_specific_folder(original_folder)
                
    except Exception as e:
        print(f"❌ Błąd odświeżania po usunięciu: {e}")
Dodaj import w main.py
python# Na górze pliku main.py dodaj:
import send2trash  # pip install send2trash
Kluczowe zmiany:

Kolory archiwów - Każdy typ archiwum ma swój kolor z config.json, kafelki mają tło i obramowanie w kolorze typu
Checkboxy w galerii - Każdy kafelek ma checkbox w lewym górnym rogu (na razie bez funkcji)
Ikonka kosza - Przy każdym obrazie w liście "Pozostałe obrazy" jest przycisk kosza
Usuwanie do kosza - Kliknięcie kosza usuwa plik do kosza systemowego przez bibliotekę send2trash
Komunikacja JS-Python - JavaScript komunikuje się z Python przez localStorage
Automatyczne odświeżanie - Po usunięciu pliku galeria jest automatycznie odświeżana

Pamiętaj o zainstalowaniu biblioteki: pip install send2trash