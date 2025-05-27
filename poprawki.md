1. Przycisk "Wybierz Folder" nie działa
W pliku main.py w funkcji init_ui() brakuje połączenia sygnału:
pythonself.select_folder_button.clicked.connect(self.select_work_directory)
2. Biała strona przy pojedynczych plikach + automatyczne ładowanie
W pliku templates/gallery_template.html usuń linię z ścieżką która psuje layout:
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
      <div class="breadcrumb">
        {% for part in breadcrumb_parts %} {% if part.link %}
        <a href="{{ part.link }}">{{ part.name }}</a> <span>/</span>
        {% else %}
        <span>{{ part.name }}</span>
        {% endif %} {% endfor %}
      </div>

      <!-- TYLKO NAGŁÓWEK - USUNIĘTO ŚCIEŻKĘ KTÓRA PSUŁA LAYOUT -->
      <h1>{{ current_folder_display_name }}</h1>

      {% if subfolders %}
      <div class="section">
        <h2>📁 Podfoldery ({{ subfolders|length }})</h2>
        <div class="subfolders-grid">
          {% for sf in subfolders %}
          <div class="subfolder-item">
            <div class="folder-icon">📁</div>
            <a href="{{ sf.link }}">{{ sf.name }}</a>
            <div class="folder-stats">
              <span>{{ sf.total_size_readable }}</span>
              <span>{{ sf.file_count }} plików</span>
              <span>{{ sf.subdir_count }} folderów</span>
            </div>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      {% if files_with_previews %}
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

      {% if other_images %}
      <div class="section">
        <h2>🎨 Pozostałe obrazy ({{ other_images|length }})</h2>
        <div class="gallery" id="otherImagesGallery">
          {% for image in other_images %}
          <div class="gallery-item">
            {% if image.image_relative_path %}
            <img
              src="{{ image.image_relative_path }}"
              alt="{{ image.name }}"
              class="preview-image"
              data-full-src="{{ image.image_relative_path }}"
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
              <span>Błąd ładowania</span>
            </div>
            {% endif %}
            <p>
              <a href="{{ image.file_link }}" title="Otwórz: {{ image.name }}"
                >{{ image.name }}</a
              >
            </p>
            <p class="file-info">{{ image.size_readable }}</p>
          </div>
          {% endfor %}
        </div>
      </div>
      {% endif %}

      {% if files_without_previews %}
      <div class="section">
        <h2>📄 Pliki bez podglądu ({{ files_without_previews|length }})</h2>
        <ul class="no-preview-list">
          {% for file in files_without_previews %}
          <li>
            <a href="{{ file.archive_link }}" title="Otwórz: {{ file.name }}"
              >{{ file.name }}</a
            >
            <span class="file-info"> — {{ file.size_readable }}</span>
          </li>
          {% endfor %}
        </ul>
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
          document.getElementById('otherImagesGallery'),
        ].filter(Boolean);

        const previewModal = document.getElementById('previewModal');
        const previewBackdrop = document.getElementById('previewBackdrop');
        const previewImg = document.getElementById('previewImg');

        // Podgląd w modalnym oknie
        function showPreview(imageSrc) {
          previewImg.src = imageSrc;
          previewModal.classList.add('show');
          previewBackdrop.classList.add('show');
          previewModal.style.transform = 'translate(-50%, -50%)';
        }

        function hidePreview() {
          previewModal.classList.remove('show');
          previewBackdrop.classList.remove('show');
          previewImg.src = '';
        }

        // Podgląd na hover
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

        // Zamykanie modala
        previewBackdrop.addEventListener('click', hidePreview);
        previewModal.addEventListener('click', hidePreview);

        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape') {
            hidePreview();
          }
        });
      });
    </script>
  </body>
</html>
3. Automatyczne ładowanie galerii przy starcie
W pliku main.py dodaj automatyczne ładowanie w __init__():
pythondef __init__(self):
    super().__init__()
    self.setWindowTitle("Skaner Folderów i Kreator Galerii")
    self.setGeometry(100, 100, 1400, 900)
    self.setMinimumSize(1200, 800)

    self.current_work_directory = config_manager.get_work_directory()
    self.scanner_thread = None
    self.gallery_thread = None
    self.current_gallery_root_html = None

    os.makedirs(self.GALLERY_CACHE_DIR, exist_ok=True)
    self.init_ui()
    self.update_status_label()
    self.update_gallery_buttons_state()
    
    # AUTOMATYCZNE ŁADOWANIE GALERII PRZY STARCIE
    if self.current_work_directory:
        self.current_gallery_root_html = self.get_current_gallery_index_html()
        if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
            self.show_gallery_in_app()
        self.update_folder_stats()
4. Zawieszanie przy skanowaniu - dodaj timeout i obsługę błędów
W pliku scanner_logic.py popraw funkcję process_folder():
pythondef process_folder(folder_path, progress_callback=None):
    """
    Przetwarza pojedynczy folder: zbiera informacje i generuje index.json.
    Rekursywnie wywołuje się dla podfolderów.
    """
    if progress_callback:
        progress_callback(f"Przetwarzanie folderu: {folder_path}")

    # ZABEZPIECZENIE PRZED ZAWIESZENIEM
    try:
        # Sprawdź czy folder jest dostępny w rozsądnym czasie
        if not os.path.exists(folder_path):
            if progress_callback:
                progress_callback(f"Folder nie istnieje: {folder_path}")
            return
            
        if not os.access(folder_path, os.R_OK):
            if progress_callback:
                progress_callback(f"Brak dostępu do folderu: {folder_path}")
            return
    except Exception as e:
        if progress_callback:
            progress_callback(f"Błąd dostępu do folderu {folder_path}: {e}")
        return

    index_data = {
        "folder_info": get_folder_stats(folder_path),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": []
    }

    all_items_in_dir = []
    subdirectories = []
    
    try:
        # TIMEOUT dla skanowania foldera - maksymalnie 30 sekund na folder
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Timeout podczas skanowania {folder_path}")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 sekund timeout
        
        try:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    try:
                        all_items_in_dir.append(entry.name)
                        if entry.is_dir():
                            subdirectories.append(entry.path)
                        if progress_callback and len(all_items_in_dir) % 100 == 0:
                            progress_callback(f"Przetworzono {len(all_items_in_dir)} plików w {folder_path}")
                    except (OSError, PermissionError) as e:
                        if progress_callback:
                            progress_callback(f"Błąd dostępu do pliku {entry.name}: {e}")
                        continue
        finally:
            signal.alarm(0)  # Wyłącz timeout
            signal.signal(signal.SIGALRM, old_handler)
            
    except TimeoutError as e:
        if progress_callback:
            progress_callback(f"TIMEOUT: {e}")
        return
    except (OSError, PermissionError) as e:
        if progress_callback:
            progress_callback(f"Błąd dostępu do folderu {folder_path}: {e}")
        return

    # Reszta funkcji bez zmian...
    image_filenames = [f for f in all_items_in_dir if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(IMAGE_EXTENSIONS)]
    other_filenames = [f for f in all_items_in_dir if os.path.isfile(os.path.join(folder_path, f)) and not f.lower().endswith(IMAGE_EXTENSIONS) and f.lower() != "index.json"]

    full_path_image_files = [os.path.join(folder_path, img_name) for img_name in image_filenames]
    found_previews_paths = set()

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
            "size_readable": get_file_size_readable(file_size_bytes)
        }

        preview_file_path = find_matching_preview_for_file(file_basename, full_path_image_files)

        if preview_file_path:
            file_info["preview_found"] = True
            file_info["preview_name"] = os.path.basename(preview_file_path)
            file_info["preview_path_absolute"] = os.path.abspath(preview_file_path)
            index_data["files_with_previews"].append(file_info)
            found_previews_paths.add(preview_file_path)
        else:
            file_info["preview_found"] = False
            index_data["files_without_previews"].append(file_info)
            
    # Dodaj obrazy, które nie zostały sparowane jako podglądy
    for img_name in image_filenames:
        img_path_full = os.path.join(folder_path, img_name)
        if img_path_full not in found_previews_paths:
            try:
                img_size_bytes = os.path.getsize(img_path_full)
            except OSError:
                img_size_bytes = 0
            
            index_data["other_images"].append({
                "name": img_name,
                "path_absolute": os.path.abspath(img_path_full),
                "size_bytes": img_size_bytes,
                "size_readable": get_file_size_readable(img_size_bytes)
            })

    # Zapisz index.json
    index_json_path = os.path.join(folder_path, "index.json")
    try:
        with open(index_json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4, ensure_ascii=False)
        if progress_callback:
            progress_callback(f"Zapisano: {index_json_path}")
    except IOError as e:
        if progress_callback:
            progress_callback(f"Błąd zapisu {index_json_path}: {e}")

    # Przetwarzaj podfoldery
    for subdir in subdirectories:
        try:
            process_folder(subdir, progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Błąd przetwarzania podfolderu {subdir}: {e}")
            continue
5. Poprawiony init_ui() z działającym przyciskiem
pythondef init_ui(self):
    main_widget = QWidget(self)
    self.setCentralWidget(main_widget)
    main_layout = QVBoxLayout(main_widget)

    # Górny panel kontrolny
    controls_widget = QWidget()
    controls_layout = QVBoxLayout(controls_widget)
    
    # Sekcja wyboru folderu
    folder_layout = QHBoxLayout()
    self.folder_label = QLabel("Folder roboczy: Brak")
    folder_layout.addWidget(self.folder_label, 1)
    
    self.select_folder_button = QPushButton("📁 Wybierz Folder")
    self.select_folder_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
    # NAPRAWIONE - DODANO POŁĄCZENIE SYGNAŁU
    self.select_folder_button.clicked.connect(self.select_work_directory)
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
    
    # Suwak rozmiaru kafelków
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
    self.web_view.urlChanged.connect(self.on_webview_url_changed)
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
Główne naprawki:

✅ Dodano połączenie przycisku "Wybierz Folder"
✅ Usunięto linię z ścieżką która psuła layout CSS
✅ Automatyczne ładowanie galerii przy starcie aplikacji
✅ Timeout i obsługa błędów przy skanowaniu
✅ Zabezpieczenia przed zawieszaniem się aplikacji

Teraz wszystko powinno działać poprawnie!