1. Napraw CSS - Ciemny schemat
Plik: templates/gallery_styles.css
css:root {
    --bg-primary: #1a1a1a;
    --bg-secondary: #2d2d2d;
    --bg-tertiary: #3a3a3a;
    --text-primary: #ffffff;
    --text-secondary: #b0b0b0;
    --accent: #007acc;
    --accent-hover: #005a9e;
    --border: #404040;
    --shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

* {
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, var(--bg-primary) 0%, #0f0f0f 100%);
    color: var(--text-primary);
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 1800px;
    margin: 0 auto;
    background: var(--bg-secondary);
    padding: 30px;
    border-radius: 16px;
    box-shadow: var(--shadow);
}

h1, h2, h3 {
    color: var(--text-primary);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 10px;
}

.breadcrumb {
    margin-bottom: 25px;
    padding: 15px;
    background: var(--bg-tertiary);
    border-radius: 8px;
    font-size: 1.1em;
    border-left: 4px solid var(--accent);
}

.breadcrumb a {
    color: var(--accent);
    transition: var(--transition);
    text-decoration: none;
}

.breadcrumb a:hover {
    color: var(--accent-hover);
    text-shadow: 0 0 8px var(--accent);
}

.gallery-controls {
    background: var(--bg-tertiary);
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 30px;
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 15px;
}

.gallery-controls label {
    color: var(--text-primary);
    font-weight: bold;
}

.gallery-controls input[type="range"] {
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    background: var(--bg-primary);
    border-radius: 3px;
    outline: none;
    flex: 1;
    max-width: 200px;
}

.gallery-controls input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    background: var(--accent);
    border-radius: 50%;
    cursor: pointer;
    transition: var(--transition);
}

.gallery-controls input[type="range"]::-webkit-slider-thumb:hover {
    background: var(--accent-hover);
    transform: scale(1.1);
}

.gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.gallery-item {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    transition: var(--transition);
    position: relative;
    overflow: hidden;
}

.gallery-item:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0, 123, 255, 0.15);
    border-color: var(--accent);
}

.gallery-item img {
    width: 100%;
    height: 140px;
    object-fit: cover;
    border-radius: 8px;
    margin-bottom: 12px;
    transition: var(--transition);
    cursor: pointer;
}

.gallery-item:hover img {
    transform: scale(1.05);
}

.gallery-item p {
    margin: 5px 0;
    font-size: 0.9em;
    word-wrap: break-word;
    color: var(--text-primary);
}

.file-info {
    font-size: 0.8em;
    color: var(--text-secondary);
}

/* FOLDERY W KAFELKACH - NIE LISTA */
.subfolders-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.subfolder-item {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    transition: var(--transition);
    cursor: pointer;
}

.subfolder-item:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0, 123, 255, 0.2);
    border-color: var(--accent);
}

.subfolder-item a {
    color: var(--text-primary);
    text-decoration: none;
    font-weight: bold;
    display: block;
}

.subfolder-item:hover a {
    color: var(--accent);
}

/* Podgląd po najechaniu */
.preview-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.9);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    backdrop-filter: blur(5px);
}

.preview-overlay img {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
    border-radius: 12px;
    box-shadow: var(--shadow);
}

.preview-overlay.show {
    display: flex;
}

.no-preview-list {
    list-style: none;
    padding: 0;
    background: var(--bg-tertiary);
    border-radius: 8px;
    overflow: hidden;
}

.no-preview-list li {
    padding: 15px 20px;
    border-bottom: 1px solid var(--border);
    transition: var(--transition);
}

.no-preview-list li:hover {
    background: var(--bg-primary);
}

.no-preview-list a {
    color: var(--text-primary);
    text-decoration: none;
}

.no-preview-list a:hover {
    color: var(--accent);
}

.folder-stats {
    background: linear-gradient(135deg, var(--bg-tertiary) 0%, #1e3a5f 100%);
    padding: 20px;
    border-radius: 12px;
    border-left: 4px solid var(--accent);
}

.folder-stats p {
    margin: 5px 0;
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

/* Responsive */
@media (max-width: 768px) {
    .gallery {
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 15px;
    }
    
    .subfolders-grid {
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }
    
    .container {
        padding: 20px;
        margin: 10px;
    }
}
2. Napraw szablon HTML z podglądem i kafelkami folderów
Plik: templates/gallery_template.html
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
                    <a href="{{ part.link }}">{{ part.name }}</a> /
                {% else %}
                    <span>{{ part.name }}</span>
                {% endif %}
            {% endfor %}
        </div>
        <h1>Galeria: {{ current_folder_display_name }}</h1>
        <p>Pełna ścieżka: {{ folder_info.path }}</p>

        <div class="gallery-controls">
            <label for="sizeSlider">Rozmiar miniaturki:</label>
            <input type="range" id="sizeSlider" min="100" max="400" value="150">
            <span id="sizeValue">150px</span>
        </div>

        {% if subfolders %}
        <div class="section">
            <h2>Podfoldery ({{ subfolders|length }})</h2>
            <div class="subfolders-grid">
                {% for sf in subfolders %}
                <div class="subfolder-item">
                    <a href="{{ sf.link }}">📁 {{ sf.name }}</a>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if files_with_previews %}
        <div class="section">
            <h2>Pliki z podglądem ({{ files_with_previews|length }})</h2>
            <div class="gallery" id="filesWithPreviewsGallery">
                {% for file in files_with_previews %}
                <div class="gallery-item">
                    <a href="{{ file.archive_link }}" title="Otwórz plik: {{ file.name }}">
                        {% if file.preview_relative_path %}
                        <img src="{{ file.preview_relative_path }}" alt="Podgląd dla {{ file.name }}" class="preview-image">
                        {% else %}
                        <div style="height: 140px; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; border-radius: 8px;">
                            <span>Brak podglądu</span>
                        </div>
                        {% endif %}
                    </a>
                    <p><a href="{{ file.archive_link }}" title="Otwórz plik: {{ file.name }}">{{ file.name }}</a></p>
                    <p class="file-info">{{ file.size_readable }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if other_images %}
        <div class="section">
            <h2>Pozostałe obrazy ({{ other_images|length }})</h2>
            <div class="gallery" id="otherImagesGallery">
                {% for image in other_images %}
                <div class="gallery-item">
                     <a href="{{ image.file_link }}" title="Otwórz plik: {{ image.name }}">
                        {% if image.image_relative_path %}
                        <img src="{{ image.image_relative_path }}" alt="{{ image.name }}" class="preview-image">
                        {% else %}
                        <div style="height: 140px; background: var(--bg-primary); display: flex; align-items: center; justify-content: center; border-radius: 8px;">
                            <span>Błąd ładowania</span>
                        </div>
                        {% endif %}
                     </a>
                    <p><a href="{{ image.file_link }}" title="Otwórz plik: {{ image.name }}">{{ image.name }}</a></p>
                    <p class="file-info">{{ image.size_readable }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if files_without_previews %}
        <div class="section">
            <h2>Pliki bez podglądu ({{ files_without_previews|length }})</h2>
            <ul class="no-preview-list">
                {% for file in files_without_previews %}
                <li>
                    <a href="{{ file.archive_link }}" title="Otwórz plik: {{ file.name }}">{{ file.name }}</a>
                    <span class="file-info"> ({{ file.size_readable }})</span>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div class="section folder-stats">
            <h3>Statystyki folderu</h3>
            <p>Całkowity rozmiar plików: {{ folder_info.total_size_readable }}</p>
            <p>Liczba plików: {{ folder_info.file_count }}</p>
            <p>Liczba podfolderów: {{ folder_info.subdir_count }}</p>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function () {
            const slider = document.getElementById('sizeSlider');
            const sizeValueDisplay = document.getElementById('sizeValue');
            const galleries = [
                document.getElementById('filesWithPreviewsGallery'),
                document.getElementById('otherImagesGallery')
            ].filter(Boolean);

            // Tworzenie overlay'a dla podglądu
            const previewOverlay = document.createElement('div');
            previewOverlay.className = 'preview-overlay';
            previewOverlay.innerHTML = '<img src="" alt="Podgląd">';
            document.body.appendChild(previewOverlay);

            function updateThumbnailSize() {
                const newSize = slider.value + 'px';
                sizeValueDisplay.textContent = newSize;
                galleries.forEach(gallery => {
                    const items = gallery.querySelectorAll('.gallery-item');
                    items.forEach(item => {
                        item.style.width = newSize;
                        const img = item.querySelector('img');
                        if (img) {
                            img.style.maxHeight = (parseInt(slider.value) * 0.8) + 'px';
                        }
                    });
                });
            }

            function showPreview(imageSrc, event) {
                event.preventDefault();
                event.stopPropagation();
                
                const previewImg = previewOverlay.querySelector('img');
                previewImg.src = imageSrc;
                previewImg.style.maxWidth = '800px';
                previewImg.style.maxHeight = '800px';
                
                previewOverlay.classList.add('show');
            }

            function hidePreview() {
                previewOverlay.classList.remove('show');
            }

            // Event listenery
            if (slider) {
                slider.addEventListener('input', updateThumbnailSize);
                updateThumbnailSize();
            }

            // Podgląd na hover dla miniaturek
            galleries.forEach(gallery => {
                const images = gallery.querySelectorAll('.preview-image');
                images.forEach(img => {
                    let hoverTimeout;
                    
                    img.addEventListener('mouseenter', function(e) {
                        hoverTimeout = setTimeout(() => {
                            showPreview(this.src, e);
                        }, 300); // Opóźnienie 300ms
                    });
                    
                    img.addEventListener('mouseleave', function() {
                        clearTimeout(hoverTimeout);
                        setTimeout(hidePreview, 100);
                    });
                });
            });

            // Ukryj podgląd po kliknięciu lub ESC
            previewOverlay.addEventListener('click', hidePreview);
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    hidePreview();
                }
            });

            // Hover na overlay też ukrywa
            previewOverlay.addEventListener('mouseenter', function() {
                setTimeout(hidePreview, 500);
            });
        });
    </script>
</body>
</html>
3. Zaktualizuj gitignore
Plik: .gitignore
gitignore# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project specific
_gallery_cache/
*.log
.env
.folder_cache.json

# System files
.DS_Store
Thumbs.db