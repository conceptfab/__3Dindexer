Zmiany w pliku main.py
W funkcji __init__ klasy MainWindow:
pythondef __init__(self):
    super().__init__()
    self.setWindowTitle("Skaner Folderów i Kreator Galerii")
    self.setGeometry(100, 100, 1400, 900)  # Zwiększony rozmiar startowy
    self.setMinimumSize(1200, 800)  # Minimalna wielkość okna
W funkcji select_work_directory:
pythondef select_work_directory(self):
    initial_dir = self.current_work_directory if self.current_work_directory else os.path.expanduser("~")
    folder = QFileDialog.getExistingDirectory(self, "Wybierz folder roboczy", initial_dir)
    if folder:
        self.current_work_directory = folder
        if config_manager.set_work_directory(folder):
            self.log_message(f"Ustawiono folder roboczy: {folder}")
        else:
            self.log_message(f"Błąd zapisu konfiguracji dla folderu: {folder}")
        self.update_status_label()
        self.current_gallery_root_html = self.get_current_gallery_index_html()
        self.update_gallery_buttons_state()
        
        # AUTOMATYCZNE OTWIERANIE GALERII PO WYBORZE FOLDERU
        if self.current_gallery_root_html and os.path.exists(self.current_gallery_root_html):
            self.show_gallery_in_app()
        else:
            # Jeśli galeria nie istnieje, automatycznie ją zbuduj
            self.rebuild_gallery(auto_show_after_build=True)
Nowy plik templates/gallery_styles.css
css:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;  
    --bg-tertiary: #21262d;
    --bg-quaternary: #30363d;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --accent-bg: rgba(88, 166, 255, 0.1);
    --border: #30363d;
    --border-muted: #21262d;
    --success: #3fb950;
    --warning: #d29922;
    --danger: #f85149;
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    --shadow-hover: 0 16px 48px rgba(0, 0, 0, 0.8);
    --radius: 12px;
    --radius-sm: 8px;
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

* {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, var(--bg-primary) 0%, #0a0e16 100%);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: none; /* Usuwa ograniczenie szerokości */
    width: 100%;
    margin: 0;
    background: var(--bg-secondary);
    padding: 24px;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    min-height: calc(100vh - 40px);
}

h1, h2, h3 {
    color: var(--text-primary);
    margin: 0 0 16px 0;
    font-weight: 600;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
}

h1 { font-size: 2rem; }
h2 { font-size: 1.5rem; }
h3 { font-size: 1.25rem; }

.breadcrumb {
    margin-bottom: 24px;
    padding: 12px 16px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-sm);
    font-size: 0.95rem;
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
}

.breadcrumb a {
    color: var(--accent);
    transition: var(--transition);
    text-decoration: none;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
}

.breadcrumb a:hover {
    color: var(--accent-hover);
    background: var(--accent-bg);
}

.gallery-controls {
    background: var(--bg-tertiary);
    padding: 16px 20px;
    border-radius: var(--radius);
    margin-bottom: 24px;
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 16px;
}

.gallery-controls label {
    color: var(--text-primary);
    font-weight: 500;
    font-size: 0.9rem;
}

.gallery-controls input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    height: 4px;
    background: var(--bg-primary);
    border-radius: 2px;
    outline: none;
    flex: 1;
    max-width: 200px;
}

.gallery-controls input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    background: var(--accent);
    border-radius: 50%;
    cursor: pointer;
    transition: var(--transition);
    border: 2px solid var(--bg-secondary);
}

.gallery-controls input[type="range"]::-webkit-slider-thumb:hover {
    background: var(--accent-hover);
    transform: scale(1.15);
    box-shadow: 0 0 12px var(--accent);
}

#sizeValue {
    color: var(--text-secondary);
    font-size: 0.85rem;
    min-width: 50px;
}

.section {
    margin-bottom: 32px;
}

/* GALERIA - RESPONSIVE GRID */
.gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.gallery-item {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    text-align: center;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
    cursor: pointer;
}

.gallery-item:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-hover);
    border-color: var(--accent);
    background: var(--bg-quaternary);
}

.gallery-item img {
    width: 100%;
    height: 160px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    margin-bottom: 12px;
    transition: var(--transition);
    cursor: pointer;
}

.gallery-item:hover img {
    transform: scale(1.02);
}

.gallery-item p {
    margin: 4px 0;
    font-size: 0.9rem;
    word-wrap: break-word;
    color: var(--text-primary);
}

.file-info {
    font-size: 0.75rem;
    color: var(--text-secondary);
}

/* PODGLĄD W MODALNYM OKNIE */
.preview-modal {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-hover);
    padding: 20px;
    z-index: 1001;
    max-width: 80vw;
    max-height: 80vh;
    display: none;
}

.preview-modal.show {
    display: block;
}

.preview-modal img {
    max-width: 100%;
    max-height: 70vh;
    object-fit: contain;
    border-radius: var(--radius-sm);
}

.preview-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: none;
}

.preview-backdrop.show {
    display: block;
}

/* PODFOLDERY */
.subfolders-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
}

.subfolder-item {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    text-align: center;
    transition: var(--transition);
    cursor: pointer;
}

.subfolder-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15);
    border-color: var(--accent);
    background: var(--bg-quaternary);
}

.subfolder-item a {
    color: var(--text-primary);
    text-decoration: none;
    font-weight: 500;
    display: block;
    font-size: 0.95rem;
}

.subfolder-item:hover a {
    color: var(--accent);
}

.no-preview-list {
    list-style: none;
    padding: 0;
    background: var(--bg-tertiary);
    border-radius: var(--radius);
    overflow: hidden;
    border: 1px solid var(--border);
}

.no-preview-list li {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-muted);
    transition: var(--transition);
}

.no-preview-list li:last-child {
    border-bottom: none;
}

.no-preview-list li:hover {
    background: var(--bg-quaternary);
}

.no-preview-list a {
    color: var(--text-primary);
    text-decoration: none;
    font-weight: 500;
}

.no-preview-list a:hover {
    color: var(--accent);
}

.folder-stats {
    background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-quaternary) 100%);
    padding: 20px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
}

.folder-stats h3 {
    margin-top: 0;
    color: var(--accent);
}

.folder-stats p {
    margin: 8px 0;
    color: var(--text-primary);
}

a {
    color: var(--accent);
    text-decoration: none;
    transition: var(--transition);
}

a:hover {
    color: var(--accent-hover);
}

/* RESPONSIVE */
@media (max-width: 1200px) {
    .gallery {
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 16px;
    }
}

@media (max-width: 768px) {
    .container {
        padding: 16px;
        margin: 10px;
    }
    
    .gallery {
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 12px;
    }
    
    .subfolders-grid {
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    }
    
    .gallery-controls {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
    }
}
Nowy plik templates/gallery_template.html
html<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Galeria: {{ current_folder_display_name }}</title>
    <link rel="stylesheet" href="{{ ' ../' * depth }}gallery_styles.css">
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
        
        <h1>{{ current_folder_display_name }}</h1>
        <p style="color: var(--text-secondary); margin-bottom: 24px;">{{ folder_info.path }}</p>

        <div class="gallery-controls">
            <label for="sizeSlider">Rozmiar kafelków:</label>
            <input type="range" id="sizeSlider" min="150" max="350" value="200">
            <span id="sizeValue">200px</span>
        </div>

        {% if subfolders %}
        <div class="section">
            <h2>📁 Podfoldery ({{ subfolders|length }})</h2>
            <div class="subfolders-grid">
                {% for sf in subfolders %}
                <div class="subfolder-item">
                    <a href="{{ sf.link }}">{{ sf.name }}</a>
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
                    <img src="{{ file.preview_relative_path }}" 
                         alt="Podgląd dla {{ file.name }}" 
                         class="preview-image"
                         data-full-src="{{ file.preview_relative_path }}">
                    {% else %}
                    <div style="height: 160px; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; border-radius: 8px; color: var(--text-secondary);">
                        <span>Brak podglądu</span>
                    </div>
                    {% endif %}
                    <p><a href="{{ file.archive_link }}" title="Otwórz: {{ file.name }}">{{ file.name }}</a></p>
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
                    <img src="{{ image.image_relative_path }}" 
                         alt="{{ image.name }}" 
                         class="preview-image"
                         data-full-src="{{ image.image_relative_path }}">
                    {% else %}
                    <div style="height: 160px; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; border-radius: 8px; color: var(--text-secondary);">
                        <span>Błąd ładowania</span>
                    </div>
                    {% endif %}
                    <p><a href="{{ image.file_link }}" title="Otwórz: {{ image.name }}">{{ image.name }}</a></p>
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
                    <a href="{{ file.archive_link }}" title="Otwórz: {{ file.name }}">{{ file.name }}</a>
                    <span class="file-info"> — {{ file.size_readable }}</span>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div class="section folder-stats">
            <h3>📊 Statystyki folderu</h3>
            <p><strong>Całkowity rozmiar:</strong> {{ folder_info.total_size_readable }}</p>
            <p><strong>Liczba plików:</strong> {{ folder_info.file_count }}</p>
            <p><strong>Liczba podfolderów:</strong> {{ folder_info.subdir_count }}</p>
        </div>
    </div>

    <!-- Modal podglądu -->
    <div class="preview-backdrop" id="previewBackdrop"></div>
    <div class="preview-modal" id="previewModal">
        <img src="" alt="Podgląd" id="previewImg">
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function () {
            const slider = document.getElementById('sizeSlider');
            const sizeValueDisplay = document.getElementById('sizeValue');
            const galleries = [
                document.getElementById('filesWithPreviewsGallery'),
                document.getElementById('otherImagesGallery')
            ].filter(Boolean);

            const previewModal = document.getElementById('previewModal');
            const previewBackdrop = document.getElementById('previewBackdrop');
            const previewImg = document.getElementById('previewImg');

            // Aktualizacja rozmiaru kafelków
            function updateTileSize() {
                const newSize = slider.value + 'px';
                sizeValueDisplay.textContent = newSize;
                
                galleries.forEach(gallery => {
                    gallery.style.gridTemplateColumns = `repeat(auto-fill, minmax(${slider.value}px, 1fr))`;
                });
            }

            // Podgląd w modalnym oknie
            function showPreview(imageSrc) {
                previewImg.src = imageSrc;
                previewModal.classList.add('show');
                previewBackdrop.classList.add('show');
                
                // Wyśrodkowanie
                previewModal.style.transform = 'translate(-50%, -50%)';
            }

            function hidePreview() {
                previewModal.classList.remove('show');
                previewBackdrop.classList.remove('show');
                previewImg.src = '';
            }

            // Event listeners
            if (slider) {
                slider.addEventListener('input', updateTileSize);
                updateTileSize();
            }

            // Podgląd na hover
            galleries.forEach(gallery => {
                const images = gallery.querySelectorAll('.preview-image');
                images.forEach(img => {
                    let hoverTimeout;
                    
                    img.addEventListener('mouseenter', function() {
                        hoverTimeout = setTimeout(() => {
                            showPreview(this.src);
                        }, 500); // 500ms opóźnienia
                    });
                    
                    img.addEventListener('mouseleave', function() {
                        clearTimeout(hoverTimeout);
                    });
                });
            });

            // Zamykanie modala
            previewBackdrop.addEventListener('click', hidePreview);
            previewModal.addEventListener('click', hidePreview);
            
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    hidePreview();
                }
            });
        });
    </script>
</body>
</html>
Główne zmiany:

Automatyczne otwieranie galerii - Po wyborze folderu automatycznie otwiera galerię lub ją buduje
Pełna szerokość - Usunięto ograniczenie max-width, strona zajmuje całą dostępną przestrzeń
Rozmiar kafelków - Suwak teraz zmienia rozmiar całych kafelków, nie tylko miniaturek
Modal podglądu - Podgląd w małym oknie modalnym zamiast na całym ekranie
Nowoczesny design - GitHub-style ciemny motyw z lepszymi kolorami i efektami
Większe okno startowe - 1400x900px z minimum 1200x800px

Teraz aplikacja powinna działać znacznie lepiej i wyglądać profesjonalnie!