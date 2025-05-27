Rozumiem twoje frustracje! Przeprowadzę poprawki aby:

Usunąć powtarzające się nagłówki - zostanie tylko jeden
Naprawić białe tło statystyk w aplikacji na ciemny schemat
Usunąć statystyki ze strony - będą tylko w aplikacji
Naprawić suwak rozmiaru w aplikacji

Zmiany w kodzie
1. Plik templates/gallery_template.html
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

      <!-- TYLKO JEDEN NAGŁÓWEK - USUNIĘTO POWTÓRZENIA -->
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

      <!-- USUNIĘTO SEKCJĘ STATYSTYK - BĘDĄ TYLKO W APLIKACJI -->

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
2. Plik main.py - funkcja init_ui()
pythondef init_ui(self):
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
3. Plik main.py - funkcja update_tile_size()
pythondef update_tile_size(self):
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
4. Plik main.py - funkcja show_gallery_in_app()
pythondef show_gallery_in_app(self):
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
Podsumowanie zmian:

✅ Usunięto powtarzające się nagłówki - zostaje tylko <h1>{{ current_folder_display_name }}</h1>
✅ Naprawiono ciemne tło panelu statystyk w aplikacji
✅ Usunięto statystyki ze strony HTML - są tylko w aplikacji
✅ Naprawiono suwak rozmiaru kafelków - działa przez JavaScript w aplikacji
✅ Dodano automatyczne ustawianie rozmiaru po załadowaniu galerii

Teraz interfejs będzie czysty i funkcjonalny!