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
          <div class="gallery-item">
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
            <li>
              <div class="file-item">
                <input type="checkbox" class="file-checkbox" data-file="{{ file.name }}" data-path="{{ file.path_absolute }}" data-type="archive">
                <a href="{{ file.archive_link }}" title="Otwórz: {{ file.name }}"
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
                <input type="checkbox" class="file-checkbox" data-file="{{ image.name }}" data-path="{{ image.path_absolute }}" data-type="image">
                
                  href="{{ image.file_link }}"
                  title="Otwórz: {{ image.name }}"
                  data-preview-src="{{ image.image_relative_path }}"
                  class="preview-link"
                  >{{ image.name }}</a
                >
                <span class="file-info"> — {{ image.size_readable }}</span>
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
            const archiveChecked = Array.from(checkboxes).filter(cb => 
              cb.checked && cb.dataset.type === 'archive'
            );
            const imageChecked = Array.from(checkboxes).filter(cb => 
              cb.checked && cb.dataset.type === 'image'
            );
            
            // Aktywuj przycisk gdy dokładnie 1 archiwum i 1 obraz jest zaznaczony
            matchBtn.disabled = !(archiveChecked.length === 1 && imageChecked.length === 1);
            
            if (matchBtn.disabled) {
              matchStatus.textContent = '';
            } else {
              matchStatus.textContent = `Gotowy do dopasowania: ${archiveChecked[0].dataset.file} ↔ ${imageChecked[0].dataset.file}`;
            }
          }

          // Nasłuchuj zmian w checkboxach
          checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
              // Jeśli zaznaczono checkbox, odznacz inne w tej samej kategorii
              if (this.checked) {
                checkboxes.forEach(otherCheckbox => {
                  if (otherCheckbox !== this && otherCheckbox.dataset.type === this.dataset.type) {
                    otherCheckbox.checked = false;
                  }
                });
              }
              updateMatchButton();
            });
          });

          // Obsługa kliknięcia przycisku dopasowania
          matchBtn.addEventListener('click', function() {
            const archiveChecked = Array.from(checkboxes).find(cb => 
              cb.checked && cb.dataset.type === 'archive'
            );
            const imageChecked = Array.from(checkboxes).find(cb => 
              cb.checked && cb.dataset.type === 'image'
            );

            if (archiveChecked && imageChecked) {
              // Wyślij żądanie do backend (będzie implementowane w main.py)
              const matchData = {
                archiveFile: archiveChecked.dataset.file,
                archivePath: archiveChecked.dataset.path,
                imageFile: imageChecked.dataset.file,
                imagePath: imageChecked.dataset.path,
                currentPath: window.location.pathname
              };

              // Wyślij informację o dopasowaniu do aplikacji PyQt
              if (window.pyqtbridge) {
                window.pyqtbridge.learnMatch(JSON.stringify(matchData));
              } else {
                // Fallback - zapisz do localStorage dla PyQt
                localStorage.setItem('pendingMatch', JSON.stringify(matchData));
                matchStatus.textContent = '✅ Dopasowanie zapisane - zostanie zastosowane przy następnym skanowaniu';
                
                // Wyczyść checkboxy
                archiveChecked.checked = false;
                imageChecked.checked = false;
                updateMatchButton();
              }
            }
          });
        }
      });
    </script>
  </body>
</html>
Zmiany w pliku templates/gallery_styles.css
css/* ... existing CSS ... */

/* NOWE STYLE DLA FUNKCJI UCZENIA */
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-checkbox {
  min-width: 16px;
  height: 16px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--accent);
}

.learning-section {
  margin-top: 32px;
  padding: 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  text-align: center;
}

.match-preview-btn {
  background: var(--accent);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  transition: var(--transition);
  min-width: 180px;
}

.match-preview-btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.match-preview-btn:disabled {
  background: var(--bg-primary);
  color: var(--text-secondary);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.match-status {
  margin-top: 12px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-style: italic;
}

/* Responsive dla sekcji uczenia */
@media (max-width: 768px) {
  .learning-section {
    margin-top: 20px;
    padding: 16px;
  }
  
  .match-preview-btn {
    min-width: 140px;
    padding: 10px 20px;
    font-size: 0.9rem;
  }
}
Zmiany w pliku main.py - dodanie obsługi uczenia się
python# main.py - dodaj na końcu klasy MainWindow

def setup_learning_bridge(self):
    """Konfiguruje most komunikacyjny z JavaScript dla funkcji uczenia się"""
    # Dodaj obsługę learning bridge w WebView
    self.web_view.loadFinished.connect(self.inject_learning_bridge)

def inject_learning_bridge(self):
    """Wstrzykuje bridge JavaScript dla komunikacji z funkcją uczenia się"""
    bridge_js = """
    window.pyqtbridge = {
        learnMatch: function(matchDataJson) {
            // Dane zostaną odebrane przez PyQt
            console.log('Learning match data:', matchDataJson);
            return matchDataJson;
        }
    };
    """
    self.web_view.page().runJavaScript(bridge_js)

def check_for_pending_matches(self):
    """Sprawdza czy są oczekujące dopasowania w localStorage"""
    js_code = """
    (function() {
        const pendingMatch = localStorage.getItem('pendingMatch');
        if (pendingMatch) {
            localStorage.removeItem('pendingMatch');
            return pendingMatch;
        }
        return null;
    })();
    """
    
    def handle_pending_match(result):
        if result:
            try:
                import json
                match_data = json.loads(result)
                self.process_learning_match(match_data)
            except Exception as e:
                self.log_message(f"Błąd przetwarzania dopasowania: {e}")
    
    self.web_view.page().runJavaScript(js_code, handle_pending_match)

def process_learning_match(self, match_data):
    """Przetwarza nowe dopasowanie i uczy algorytm"""
    try:
        archive_file = match_data.get('archiveFile', '')
        image_file = match_data.get('imageFile', '')
        archive_path = match_data.get('archivePath', '')
        image_path = match_data.get('imagePath', '')
        
        self.log_message(f"Nauczone dopasowanie: {archive_file} ↔ {image_file}")
        
        # Zapisz nowe dopasowanie do pliku uczenia się
        self.save_learning_data(archive_file, image_file, archive_path, image_path)
        
        # Opcjonalnie: natychmiastowe ponowne skanowanie folderu
        if self.current_work_directory:
            reply = QMessageBox.question(
                self,
                "Zastosować nauczone dopasowanie?",
                f"Czy chcesz natychmiast ponownie przeskanować folder, "
                f"aby zastosować nauczone dopasowanie?\n\n"
                f"Dopasowanie: {archive_file} ↔ {image_file}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.start_scan()
                
    except Exception as e:
        self.log_message(f"Błąd przetwarzania nauki: {e}")
        QMessageBox.warning(self, "Błąd", f"Nie udało się przetworzyć dopasowania: {e}")

def save_learning_data(self, archive_file, image_file, archive_path, image_path):
    """Zapisuje dane uczenia się do pliku JSON"""
    try:
        learning_file = "learning_data.json"
        learning_data = []
        
        # Wczytaj istniejące dane
        if os.path.exists(learning_file):
            with open(learning_file, 'r', encoding='utf-8') as f:
                learning_data = json.load(f)
        
        # Dodaj nowe dopasowanie
        new_match = {
            "archive_file": archive_file,
            "image_file": image_file,
            "archive_path": archive_path,
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "archive_basename": os.path.splitext(archive_file)[0],
            "image_basename": os.path.splitext(image_file)[0]
        }
        
        learning_data.append(new_match)
        
        # Zapisz zaktualizowane dane
        with open(learning_file, 'w', encoding='utf-8') as f:
            json.dump(learning_data, f, indent=2, ensure_ascii=False)
            
        self.log_message(f"Zapisano dane uczenia się: {len(learning_data)} dopasowań")
        
    except Exception as e:
        self.log_message(f"Błąd zapisu danych uczenia się: {e}")

# Dodaj wywołanie w __init__ klasy MainWindow (na końcu)
def __init__(self):
    # ... existing code ...
    
    # Dodaj na końcu __init__
    self.setup_learning_bridge()
    
    if self.current_work_directory:
        # ... existing code ...
        # Sprawdź oczekujące dopasowania po załadowaniu galerii
        QTimer.singleShot(1000, self.check_for_pending_matches)
Zmiany w pliku scanner_logic.py - integracja z danymi uczenia się
python# scanner_logic.py - dodaj na początku pliku po importach

def load_learning_data():
    """Wczytuje dane uczenia się z pliku JSON"""
    try:
        learning_file = "learning_data.json"
        if os.path.exists(learning_file):
            with open(learning_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Błąd wczytywania danych uczenia się: {e}")
        return []

def find_learned_match(archive_basename, learning_data):
    """Sprawdza czy istnieje nauczone dopasowanie dla danego pliku archiwum"""
    for match in learning_data:
        if match.get('archive_basename', '').lower() == archive_basename.lower():
            return match.get('image_basename', '')
    return None

# Zaktualizuj funkcję find_matching_preview_for_file
def find_matching_preview_for_file(base_filename, image_files_in_folder, learning_data=None):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    NOWA FUNKCJONALNOŚĆ: Najpierw sprawdza nauczone dopasowania!
    """
    if not base_filename:
        return None

    # PIERWSZEŃSTWO: Sprawdź nauczone dopasowania
    if learning_data:
        learned_image = find_learned_match(base_filename, learning_data)
        if learned_image:
            # Szukaj dokładnego dopasowania nazwy z nauki
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    if img_base.lower() == learned_image.lower():
                        logger.info(f"🎓 NAUCZONE dopasowanie: '{base_filename}' ↔ '{img_name}'")
                        return img_path

    # FALLBACK: Użyj standardowego algorytmu jeśli nie ma nauki
    base_name = base_filename.lower().strip()
    
    # ... reszta funkcji pozostaje bez zmian ...
    # (cały kod z poprzedniej wersji)

# Zaktualizuj funkcję process_folder
def process_folder(folder_path, progress_callback=None):
    """
    Przetwarza pojedynczy folder: zbiera informacje i generuje index.json.
    NOWA FUNKCJONALNOŚĆ: Używa danych uczenia się.
    """
    logger.info(f"Rozpoczęcie przetwarzania folderu: {folder_path}")

    if progress_callback:
        progress_callback(f"Przetwarzanie folderu: {folder_path}")

    # WCZYTAJ DANE UCZENIA SIĘ
    learning_data = load_learning_data()
    if learning_data:
        logger.info(f"Wczytano {len(learning_data)} nauczonych dopasowań")
        if progress_callback:
            progress_callback(f"Zastosowano {len(learning_data)} nauczonych dopasowań")

    # ... reszta kodu process_folder do momentu przetwarzania plików ...

    for file_name in other_filenames:
        file_path = os.path.join(folder_path, file_name)
        file_basename, _ = os.path.splitext(file_name)

        try:
            file_size_bytes = os.path.getsize(file_path)
        except OSError:
            file_size_bytes = 0

        file_info = {
            "name": file_name,
            "path_absolute": os.path.abspath(file_path),
            "size_bytes": file_size_bytes,
            "size_readable": get_file_size_readable(file_size_bytes),
        }

        # ULEPSZONE dopasowywanie z NAUKĄ
        preview_file_path = find_matching_preview_for_file(
            file_basename, full_path_image_files, learning_data
        )

        if preview_file_path:
            file_info["preview_found"] = True
            file_info["preview_name"] = os.path.basename(preview_file_path)
            file_info["preview_path_absolute"] = os.path.abspath(preview_file_path)
            index_data["files_with_previews"].append(file_info)
            found_previews_paths.add(preview_file_path)
            logger.info(f"✅ Dopasowano: '{file_name}' ↔ '{os.path.basename(preview_file_path)}'")
        else:
            file_info["preview_found"] = False
            index_data["files_without_previews"].append(file_info)
            logger.debug(f"❌ Brak podglądu dla: '{file_name}'")

    # ... reszta funkcji pozostaje bez zmian ...
Dodatkowe importy w main.py
python# main.py - dodaj na górze pliku
from datetime import datetime
from PyQt6.QtCore import QTimer
import json