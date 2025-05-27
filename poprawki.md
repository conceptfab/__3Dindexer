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
      <!-- TYLKO BREADCRUMB - bez nagłówka -->
      <div class="breadcrumb">
        {% for part in breadcrumb_parts %} {% if part.link %}
        <a href="{{ part.link }}">{{ part.name }}</a> <span>/</span>
        {% else %}
        <span>{{ part.name }}</span>
        {% endif %} {% endfor %}
      </div>

      <!-- USUNIĘTO NAGŁÓWEK H1 - mamy już ścieżkę w breadcrumb -->

      {% if subfolders %}
      <div class="section">
        <!-- USUNIĘTO NAGŁÓWEK H2 - zbędny tekst -->
        <div class="subfolders-grid">
          {% for sf in subfolders %}
          <div class="subfolder-item" onclick="window.location.href='{{ sf.link }}'">
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
Zmiany w pliku templates/gallery_styles.css
Dodaj style aby całe pudełko folderu było klikalne:
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
  /* DODANO - całe pudełko jest klikalne */
  text-decoration: none;
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
  /* DODANO - pointer cursor na ikonie */
  cursor: pointer;
}

.subfolder-item a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  margin-bottom: 8px;
  /* DODANO - pointer cursor na linku */
  cursor: pointer;
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
  /* DODANO - pointer cursor na statystykach */
  cursor: pointer;
}

.folder-stats span {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
}
Co zostało naprawione:

✅ Usunięto powtarzający się nagłówek H1 - zostaje tylko breadcrumb z pełną ścieżką
✅ Usunięto zbędny nagłówek "📁 Podfoldery" - przyciski mówią same za siebie
✅ Naprawiono kliknięcie folderów - dodano onclick="window.location.href='{{ sf.link }}'"
✅ Całe pudełko folderu jest teraz klikalne - cursor pointer na wszystkich elementach

Teraz na górze będzie tylko jedna ścieżka w breadcrumb i foldery będą działać!