Zmiany w pliku gallery_generator.py
Funkcja process_single_index_json - zmiany w cachowaniu:
pythondef process_single_index_json(index_json_path, scanned_root_path, gallery_output_base_path, template_env, progress_callback=None):
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
    relative_path_from_scanned_root = os.path.relpath(current_folder_abs_path, scanned_root_path)

    current_gallery_html_dir = os.path.join(gallery_output_base_path, relative_path_from_scanned_root if relative_path_from_scanned_root != "." else "")
    os.makedirs(current_gallery_html_dir, exist_ok=True)
    
    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    # Caching: Check if HTML needs regeneration
    if os.path.exists(output_html_file) and os.path.exists(index_json_path) and \
       os.path.getmtime(output_html_file) >= os.path.getmtime(index_json_path):
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
        "current_folder_display_name": os.path.basename(current_folder_abs_path) if relative_path_from_scanned_root != "." else os.path.basename(scanned_root_path),
        "breadcrumb_parts": [],
        "depth": 0,
    }

    gallery_root_name = os.path.basename(scanned_root_path)
    template_data["breadcrumb_parts"], template_data["depth"] = generate_breadcrumb(relative_path_from_scanned_root, gallery_root_name)

    # Subfolders - dodaj statystyki
    for entry in os.scandir(current_folder_abs_path):
        if entry.is_dir():
            if os.path.exists(os.path.join(entry.path, "index.json")):
                # Wczytaj statystyki z index.json podfolderu
                try:
                    with open(os.path.join(entry.path, "index.json"), "r", encoding="utf-8") as f:
                        subfolder_data = json.load(f)
                        folder_info = subfolder_data.get("folder_info", {})
                        template_data["subfolders"].append({
                            "name": entry.name,
                            "link": f"{entry.name}/index.html",
                            "total_size_readable": folder_info.get("total_size_readable", "0 B"),
                            "file_count": folder_info.get("file_count", 0),
                            "subdir_count": folder_info.get("subdir_count", 0)
                        })
                except:
                    template_data["subfolders"].append({
                        "name": entry.name,
                        "link": f"{entry.name}/index.html",
                        "total_size_readable": "0 B",
                        "file_count": 0,
                        "subdir_count": 0
                    })
    
    # Files with previews - używaj bezpośrednich ścieżek
    for item in data.get("files_with_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
        if item.get("preview_path_absolute"):
            copied_item["preview_relative_path"] = f"file:///{item['preview_path_absolute']}"
        template_data["files_with_previews"].append(copied_item)

    # Files without previews
    for item in data.get("files_without_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
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
Usunięcie funkcji kopiowania podglądów:
python# Usuwamy te funkcje - nie są już potrzebne:
# def copy_preview_if_newer(src_path, dest_path_in_gallery_previews_dir)
# oraz wszystkie związane z kopiowaniem podglądów
Zmiany w pliku templates/gallery_template.html
Uproszczenie nagłówka - usunięcie powtarzających się informacji:
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
        {% for part in breadcrumb_parts %} 
        {% if part.link %}
        <a href="{{ part.link }}">{{ part.name }}</a> <span>/</span>
        {% else %}
        <span>{{ part.name }}</span>
        {% endif %} 
        {% endfor %}
      </div>

      <!-- TYLKO JEDEN NAGŁÓWEK -->
      <h1>{{ current_folder_display_name }}</h1>

      <!-- USUŃ te powtarzające się elementy:
      <p style="color: var(--text-secondary); margin-bottom: 24px">
        {{ folder_info.path }}
      </p>

      <div class="gallery-controls">
        <label for="sizeSlider">Rozmiar kafelków:</label>
        <input type="range" id="sizeSlider" min="150" max="350" value="200" />
        <span id="sizeValue">200px</span>
      </div>
      -->

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

      <!-- Reszta bez zmian... -->
    </div>

    <!-- Usuń JavaScript związany z suwakami rozmiaru -->
  </body>
</html>
Zmiany w pliku templates/gallery_styles.css
Nowe style dla podfolderów z ikonkami i statystykami:
css.subfolder-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  text-align: center;
  transition: var(--transition);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.subfolder-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15);
  border-color: var(--accent);
  background: var(--bg-quaternary);
}

.folder-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.subfolder-item a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  margin-bottom: 8px;
}

.subfolder-item:hover a {
  color: var(--accent);
}

.folder-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.folder-stats span {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Usuń style związane z gallery-controls */
Zmiany w pliku main.py
Nowy layout z panelem statystyk po prawej stronie:
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
    main_layout.addWidget(self.web_view, 1)

    # Dolny obszar: Logi i Statystyki obok siebie
    bottom_layout = QHBoxLayout()
    
    # Logi - lewa połowa
    self.log_output = QTextEdit()
    self.log_output.setReadOnly(True)
    self.log_output.setMaximumHeight(150)
    bottom_layout.addWidget(self.log_output, 1)
    
    # Panel statystyk - prawa połowa
    self.stats_panel = QWidget()
    self.stats_panel.setMaximumHeight(150)
    self.stats_panel.setStyleSheet("QWidget { background-color: #f0f0f0; border: 1px solid #ccc; }")
    stats_layout = QVBoxLayout(self.stats_panel)
    
    self.stats_title = QLabel("📊 Statystyki aktualnego folderu")
    self.stats_title.setStyleSheet("font-weight: bold; font-size: 14px;")
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

def update_tile_size(self):
    """Aktualizuje rozmiar kafelków w galerii poprzez JavaScript"""
    size = self.size_slider.value()
    self.size_label.setText(f"{size}px")
    
    # Wyślij JavaScript do WebView aby zaktualizować CSS
    js_code = f"""
    var galleries = document.querySelectorAll('.gallery');
    galleries.forEach(function(gallery) {{
        gallery.style.gridTemplateColumns = 'repeat(auto-fill, minmax({size}px, 1fr))';
    }});
    """
    self.web_view.page().runJavaScript(js_code)

def update_folder_stats(self, folder_path=None):
    """Aktualizuje panel statystyk folderu"""
    if not folder_path:
        folder_path = self.current_work_directory
    
    if not folder_path or not os.path.exists(folder_path):
        self.stats_path.setText("Ścieżka: -")
        self.stats_size.setText("Rozmiar: -")
        self.stats_files.setText("Pliki: -")
        self.stats_folders.setText("Foldery: -")
        return
    
    # Wczytaj statystyki z index.json jeśli istnieje
    index_json = os.path.join(folder_path, "index.json")
    if os.path.exists(index_json):
        try:
            with open(index_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                folder_info = data.get("folder_info", {})
                
                self.stats_path.setText(f"Ścieżka: {folder_path}")
                self.stats_size.setText(f"Rozmiar: {folder_info.get('total_size_readable', '0 B')}")
                self.stats_files.setText(f"Pliki: {folder_info.get('file_count', 0)}")
                self.stats_folders.setText(f"Foldery: {folder_info.get('subdir_count', 0)}")
        except:
            self.stats_path.setText(f"Ścieżka: {folder_path}")
            self.stats_size.setText("Rozmiar: Błąd odczytu")
            self.stats_files.setText("Pliki: -")
            self.stats_folders.setText("Foldery: -")
    else:
        self.stats_path.setText(f"Ścieżka: {folder_path}")
        self.stats_size.setText("Rozmiar: Nie zeskanowano")
        self.stats_files.setText("Pliki: -")
        self.stats_folders.setText("Foldery: -")

def select_work_directory(self):
    # ... kod wyboru folderu ...
    # Na końcu dodaj:
    self.update_folder_stats()
Główne zmiany:

Cachowanie tylko HTML - miniaturki nie są kopiowane, używane są bezpośrednie ścieżki file:///
Jeden nagłówek - usunięto powtarzające się informacje o ścieżce
Podfoldery z ikonkami i statystykami - każdy podfolder pokazuje rozmiar, liczbę plików i folderów
Suwak rozmiaru w UI aplikacji - wspólny dla całego projektu, nie w każdej stronie osobno
Panel statystyk w aplikacji - po prawej stronie dolnego panelu, pokazuje statystyki aktualnego folderu
Stylizowane przyciski - każdy ma inny kolor i ikonkę dla lepszego rozróżnienia

Te zmiany znacznie poprawią wydajność (brak kopiowania plików) i użyteczność interfejsu!