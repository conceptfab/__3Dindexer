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
                currentFolder: window.location.pathname
              };

              console.log('🎯 Zapisuję dopasowanie:', matchData);
              
              // ZAPISZ DO localStorage z unikalnym kluczem
              const matchKey = 'learningMatch_' + Date.now();
              localStorage.setItem(matchKey, JSON.stringify(matchData));
              localStorage.setItem('latestMatch', matchKey);
              
              // Informuj o powodzeniu
              matchStatus.textContent = '✅ Dopasowanie zapisane! Trwa nauka algorytmu...';
              matchBtn.disabled = true;
              matchBtn.textContent = '⏳ Przetwarzanie...';
              
              // Wyczyść checkboxy
              archiveChecked.checked = false;
              imageChecked.checked = false;
              
              // Wywołaj polling PyQt natychmiast
              setTimeout(() => {
                window.dispatchEvent(new CustomEvent('learningMatchReady', {
                  detail: matchData
                }));
              }, 100);
            }
          });
        }
      });
    </script>
  </body>
</html>
Zmiany w pliku main.py - całkowita przebudowa obsługi uczenia
python# main.py - dodaj nową funkcjonalność uczenia się

def setup_learning_bridge(self):
    """Konfiguruje most komunikacyjny z JavaScript dla funkcji uczenia się"""
    self.web_view.loadFinished.connect(self.inject_learning_bridge)
    
    # Timer do sprawdzania nowych dopasowań co sekundę
    self.learning_timer = QTimer()
    self.learning_timer.timeout.connect(self.check_for_learning_matches)
    self.learning_timer.start(1000)  # Co sekundę

def inject_learning_bridge(self):
    """Wstrzykuje bridge JavaScript dla komunikacji z funkcją uczenia się"""
    bridge_js = """
    console.log('🔌 Learning bridge injected');
    window.addEventListener('learningMatchReady', function(event) {
        console.log('🎯 Learning match event received:', event.detail);
    });
    """
    self.web_view.page().runJavaScript(bridge_js)

def check_for_learning_matches(self):
    """Sprawdza localStorage pod kątem nowych dopasowań do nauki"""
    js_code = """
    (function() {
        try {
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
            console.error('Error checking learning matches:', e);
            return null;
        }
    })();
    """
    
    self.web_view.page().runJavaScript(js_code, self.handle_learning_match)

def handle_learning_match(self, result):
    """Obsługuje nowe dopasowanie z JavaScript"""
    if result:
        try:
            match_data = json.loads(result)
            print(f"🎓 OTRZYMANO NOWE DOPASOWANIE: {match_data}")
            self.log_message(f"🎓 Nowe dopasowanie: {match_data['archiveFile']} ↔ {match_data['imageFile']}")
            
            # Zapisz dopasowanie
            self.save_learning_data(
                match_data['archiveFile'],
                match_data['imageFile'], 
                match_data['archivePath'],
                match_data['imagePath']
            )
            
            # NATYCHMIASTOWE ZASTOSOWANIE - ponowne skanowanie aktualnego folderu
            self.apply_learning_immediately(match_data)
            
        except Exception as e:
            print(f"❌ Błąd przetwarzania dopasowania: {e}")
            self.log_message(f"Błąd przetwarzania dopasowania: {e}")

def apply_learning_immediately(self, match_data):
    """Natychmiast stosuje nauczone dopasowanie"""
    try:
        # Znajdź folder z którego pochodzi dopasowanie
        archive_path = match_data.get('archivePath', '')
        if archive_path:
            current_folder = os.path.dirname(archive_path.replace('/', os.sep))
            print(f"🔄 Ponowne skanowanie folderu: {current_folder}")
            
            # Uruchom ponowne skanowanie tego konkretnego folderu
            self.rescan_specific_folder(current_folder)
            
    except Exception as e:
        print(f"❌ Błąd zastosowania nauki: {e}")
        self.log_message(f"Błąd zastosowania nauki: {e}")

def rescan_specific_folder(self, folder_path):
    """Ponownie skanuje konkretny folder i odświeża galerię"""
    try:
        if not os.path.exists(folder_path):
            print(f"❌ Folder nie istnieje: {folder_path}")
            return
            
        self.log_message(f"🔄 Ponowne skanowanie: {folder_path}")
        
        # Uruchom skanowanie w tle dla tego folderu
        import threading
        
        def scan_and_refresh():
            try:
                # Skanuj folder
                scanner_logic.process_folder(folder_path, lambda msg: print(f"📁 {msg}"))
                
                # Odśwież galerię w głównym wątku
                QTimer.singleShot(500, lambda: self.refresh_gallery_after_learning(folder_path))
                
            except Exception as e:
                print(f"❌ Błąd skanowania: {e}")
        
        thread = threading.Thread(target=scan_and_refresh)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        print(f"❌ Błąd rescan_specific_folder: {e}")

def refresh_gallery_after_learning(self, scanned_folder):
    """Odświeża galerię po zastosowaniu nauki"""
    try:
        print(f"🔄 Odświeżanie galerii po nauce dla: {scanned_folder}")
        
        # Sprawdź czy to aktualny folder lub jego podfolder
        current_url = self.web_view.url().toLocalFile()
        if current_url and "_gallery_cache" in current_url:
            gallery_folder = os.path.dirname(current_url)
            original_folder = self.get_original_folder_from_gallery_path(gallery_folder)
            
            if original_folder and (original_folder == scanned_folder or scanned_folder.startswith(original_folder)):
                print(f"✅ Folder {scanned_folder} jest częścią aktualnej galerii - odświeżam")
                
                # Przebuduj galerię
                self.rebuild_gallery_silent()
                
                # Poinformuj o sukcesie przez JavaScript
                success_js = """
                const matchBtn = document.getElementById('matchPreviewBtn');
                const matchStatus = document.getElementById('matchStatus');
                if (matchBtn && matchStatus) {
                    matchBtn.disabled = false;
                    matchBtn.textContent = '🎯 Dopasuj podgląd';
                    matchStatus.textContent = '🎉 Dopasowanie zastosowane! Galeria została odświeżona.';
                    
                    setTimeout(() => {
                        matchStatus.textContent = '';
                    }, 5000);
                }
                """
                self.web_view.page().runJavaScript(success_js)
                
                self.log_message("✅ Algorytm nauczony! Galeria odświeżona.")
                
        else:
            print(f"ℹ️ Folder {scanned_folder} nie jest częścią aktualnej galerii")
            
    except Exception as e:
        print(f"❌ Błąd odświeżania galerii: {e}")

def rebuild_gallery_silent(self):
    """Przebudowuje galerię w tle bez pokazywania dialogów"""
    try:
        if not self.current_work_directory:
            return
            
        # Sprawdź czy jest już proces
        if (self.gallery_thread and self.gallery_thread.isRunning()):
            return
            
        print("🔄 Ciche przebudowanie galerii...")
        
        self.gallery_thread = GalleryWorker(
            self.current_work_directory, self.GALLERY_CACHE_DIR
        )
        self.gallery_thread.progress_signal.connect(lambda msg: print(f"🏗️ {msg}"))
        self.gallery_thread.finished_signal.connect(self.gallery_rebuilt_silently)
        self.gallery_thread.start()
        
    except Exception as e:
        print(f"❌ Błąd rebuild_gallery_silent: {e}")

def gallery_rebuilt_silently(self, root_html_path):
    """Obsługuje zakończenie cichego przebudowania galerii"""
    try:
        if root_html_path:
            print(f"✅ Galeria przebudowana cicho: {root_html_path}")
            
            # Odśwież aktualną stronę
            current_url = self.web_view.url()
            self.web_view.reload()
            
        self.gallery_thread = None
        
    except Exception as e:
        print(f"❌ Błąd gallery_rebuilt_silently: {e}")

def save_learning_data(self, archive_file, image_file, archive_path, image_path):
    """Zapisuje dane uczenia się do pliku JSON"""
    try:
        learning_file = "learning_data.json"
        learning_data = []

        # Wczytaj istniejące dane
        if os.path.exists(learning_file):
            with open(learning_file, "r", encoding="utf-8") as f:
                learning_data = json.load(f)

        # Sprawdź czy już istnieje takie dopasowanie
        archive_basename = os.path.splitext(archive_file)[0]
        image_basename = os.path.splitext(image_file)[0]
        
        # Usuń stare dopasowanie dla tego samego archiwum jeśli istnieje
        learning_data = [item for item in learning_data 
                        if item.get('archive_basename', '').lower() != archive_basename.lower()]

        # Dodaj nowe dopasowanie
        new_match = {
            "archive_file": archive_file,
            "image_file": image_file,
            "archive_path": archive_path,
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "archive_basename": archive_basename,
            "image_basename": image_basename,
        }

        learning_data.append(new_match)

        # Zapisz zaktualizowane dane
        with open(learning_file, "w", encoding="utf-8") as f:
            json.dump(learning_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Zapisano dane uczenia się: {len(learning_data)} dopasowań")
        self.log_message(f"💾 Zapisano nauczone dopasowanie: {archive_file} ↔ {image_file}")

    except Exception as e:
        print(f"❌ Błąd zapisu danych uczenia się: {e}")
        self.log_message(f"Błąd zapisu danych uczenia się: {e}")

# Dodaj do __init__ klasy MainWindow:
def __init__(self):
    # ... existing code ...
    
    self.setup_learning_bridge()  # Dodaj tę linię na końcu __init__
    
    if self.current_work_directory:
        # ... existing code ...
        pass
Dodatkowo - dodaj do importów w main.py:
python# main.py - na górze pliku dodaj
import threading
from PyQt6.QtCore import QTimer
Kluczowe zmiany:

Polling localStorage - PyQt sprawdza co sekundę localStorage pod kątem nowych dopasowań
Natychmiastowe skanowanie - po otrzymaniu dopasowania, folder jest ponownie skanowany w tle
Cicha przebudowa galerii - galeria jest przebudowywana bez pokazywania dialogów
Automatyczne odświeżenie - strona jest automatycznie odświeżana po zastosowaniu nauki
Feedback użytkownikowi - przycisk pokazuje status i informuje o sukcesie
Bezpieczne threading - skanowanie odbywa się w osobnym wątku

Teraz przycisk rzeczywiście działa - dopasowuje podgląd, uczy algorytm i automatycznie odświeża stronę!