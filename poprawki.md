Zmiany w pliku main.py
1. Import i inicjalizacja AI
python# main.py - dodaj import na górze
import ai_sbert_matcher
2. Dodanie przycisków AI w init_ui()
python# main.py - w funkcji init_ui(), po istniejących przyciskach
def init_ui(self):
    # ... istniejący kod ...
    
    # Dodaj przyciski AI przed start_scan_button
    self.ai_scan_button = QPushButton("🤖 Skanuj AI")
    self.ai_scan_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; background-color: #2d5a50; } QPushButton:hover { background-color: #3d6a60; }")
    self.ai_scan_button.setMinimumWidth(90)
    self.ai_scan_button.clicked.connect(self.start_ai_scan)
    controls_layout.addWidget(self.ai_scan_button)
    
    self.ai_gallery_button = QPushButton("🧠 Galeria AI")
    self.ai_gallery_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; background-color: #5a2d5a; } QPushButton:hover { background-color: #6a3d6a; }")
    self.ai_gallery_button.setMinimumWidth(90)
    self.ai_gallery_button.clicked.connect(self.show_ai_gallery)
    controls_layout.addWidget(self.ai_gallery_button)
    
    # Przycisk przełączania trybu
    self.toggle_mode_button = QPushButton("🔄 Tryb: Klasyczny")
    self.toggle_mode_button.setStyleSheet("QPushButton { padding: 8px 16px; border-radius: 6px; background-color: #5a5a2d; } QPushButton:hover { background-color: #6a6a3d; }")
    self.toggle_mode_button.setMinimumWidth(120)
    self.toggle_mode_button.clicked.connect(self.toggle_gallery_mode)
    controls_layout.addWidget(self.toggle_mode_button)
    
    # ... reszta istniejącego kodu ...
3. Dodanie stanu trybu i dodatkowych katalogów cache
python# main.py - w __init__ MainWindow
def __init__(self):
    super().__init__()
    # ... istniejący kod ...
    
    # Nowe zmienne dla trybu AI
    self.gallery_mode = "classic"  # "classic" lub "ai"
    self.GALLERY_CACHE_DIR_NAME = "_gallery_cache"
    self.AI_GALLERY_CACHE_DIR_NAME = "_gallery_cache_ai"
    
    # Aktualizacja ścieżek cache
    self.GLOBAL_GALLERY_CACHE_ROOT_DIR = os.path.join(self.APP_DATA_DIR, self.GALLERY_CACHE_DIR_NAME)
    self.GLOBAL_AI_GALLERY_CACHE_ROOT_DIR = os.path.join(self.APP_DATA_DIR, self.AI_GALLERY_CACHE_DIR_NAME)
    
    os.makedirs(self.GLOBAL_GALLERY_CACHE_ROOT_DIR, exist_ok=True)
    os.makedirs(self.GLOBAL_AI_GALLERY_CACHE_ROOT_DIR, exist_ok=True)
    
    # ... reszta istniejącego kodu ...
4. Worker do AI skanowania
python# main.py - dodaj nową klasę Worker
class AIScannerWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, root_folder):
        super().__init__()
        self.root_folder = root_folder

    def run(self):
        try:
            # Utwórz procesor AI
            ai_processor = ai_sbert_matcher.AIFolderProcessor()
            
            # Uruchom przetwarzanie AI dla całego drzewa folderów
            ai_processor.process_folder_recursive(self.root_folder, self.emit_progress)
            
        except Exception as e:
            self.progress_signal.emit(f"Wystąpił krytyczny błąd AI skanowania: {e}")
            import traceback
            self.progress_signal.emit(f"Traceback (AI scan): {traceback.format_exc()}")
        finally:
            self.finished_signal.emit()

    def emit_progress(self, message):
        self.progress_signal.emit(message)
5. Funkcje obsługi przycisków AI
python# main.py - dodaj nowe funkcje w klasie MainWindow
def start_ai_scan(self):
    if not self.current_work_directory:
        QMessageBox.warning(self, "Błąd", "Najpierw wybierz folder roboczy!")
        return
    
    if self.ai_scanner_thread and self.ai_scanner_thread.isRunning():
        QMessageBox.warning(self, "Błąd", "Skanowanie AI już trwa!")
        return
    
    # Sprawdź czy istnieją pliki index.json (wymagane dla AI)
    has_index_files = False
    for root, dirs, files in os.walk(self.current_work_directory):
        if "index.json" in files:
            has_index_files = True
            break
    
    if not has_index_files:
        QMessageBox.warning(self, "Brak danych", 
                           f"Nie znaleziono plików index.json w '{self.current_work_directory}'. "
                           "Uruchom najpierw skanowanie klasyczne.")
        return
    
    self.progress_bar.setVisible(True)
    self.progress_bar.setRange(0, 0)
    
    self.ai_scanner_thread = AIScannerWorker(self.current_work_directory)
    self.ai_scanner_thread.progress_signal.connect(self.log_message)
    self.ai_scanner_thread.finished_signal.connect(self.ai_scan_finished)
    self.ai_scanner_thread.start()
    
    self.set_buttons_for_processing(True)

def ai_scan_finished(self):
    self.progress_bar.setVisible(False)
    self.set_buttons_for_processing(False)
    self.log_message("Skanowanie AI zakończone.")
    
    reply = QMessageBox.question(self, "Skanowanie AI zakończone", 
                               "Czy chcesz teraz przebudować galerię AI?",
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                               QMessageBox.StandardButton.Yes)
    if reply == QMessageBox.StandardButton.Yes:
        self.show_ai_gallery()

def show_ai_gallery(self):
    if not self.current_work_directory:
        QMessageBox.warning(self, "Brak folderu", "Najpierw wybierz folder roboczy.")
        return
    
    # Sprawdź czy istnieją dane AI
    has_ai_data = False
    for root, dirs, files in os.walk(self.current_work_directory):
        if "index.json" in files:
            try:
                with open(os.path.join(root, "index.json"), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "AI_processing_date" in data:
                        has_ai_data = True
                        break
            except:
                continue
    
    if not has_ai_data:
        QMessageBox.warning(self, "Brak danych AI", 
                           "Nie znaleziono danych AI. Uruchom najpierw skanowanie AI.")
        return
    
    # Przełącz na tryb AI i przebuduj galerię
    self.gallery_mode = "ai"
    self.update_mode_button_text()
    self.rebuild_ai_gallery(auto_show_after_build=True)

def toggle_gallery_mode(self):
    if self.gallery_mode == "classic":
        self.gallery_mode = "ai"
    else:
        self.gallery_mode = "classic"
    
    self.update_mode_button_text()
    
    # Przebuduj galerię w nowym trybie
    if self.gallery_mode == "ai":
        self.show_ai_gallery()
    else:
        self.show_gallery_in_app()

def update_mode_button_text(self):
    if self.gallery_mode == "classic":
        self.toggle_mode_button.setText("🔄 Tryb: Klasyczny")
    else:
        self.toggle_mode_button.setText("🔄 Tryb: AI")

def rebuild_ai_gallery(self, auto_show_after_build=True):
    if not self.current_work_directory:
        QMessageBox.warning(self, "Brak folderu", "Najpierw wybierz folder roboczy.")
        return
    
    if (self.scanner_thread and self.scanner_thread.isRunning()) or \
       (self.gallery_thread and self.gallery_thread.isRunning()):
        QMessageBox.information(self, "Operacja w toku", "Inna operacja jest już uruchomiona.")
        return
    
    self.log_message(f"Rozpoczynanie przebudowy galerii AI dla: {self.current_work_directory}")
    self.progress_bar.setVisible(True)
    self.progress_bar.setRange(0, 0)
    
    # Użyj AI cache directory
    self.gallery_thread = GalleryWorker(self.current_work_directory, self.GLOBAL_AI_GALLERY_CACHE_ROOT_DIR)
    self.gallery_thread.progress_signal.connect(self.log_message)
    self.gallery_thread.finished_signal.connect(lambda path: self.ai_gallery_generation_finished(path, auto_show_after_build))
    self.set_buttons_for_processing(True)
    self.gallery_thread.start()

def ai_gallery_generation_finished(self, root_html_path, auto_show=True):
    self.progress_bar.setVisible(False)
    self.current_ai_gallery_root_html = root_html_path if root_html_path and os.path.exists(root_html_path) else None
    
    if self.current_ai_gallery_root_html:
        self.log_message(f"Przebudowa galerii AI zakończona. Główny plik: {self.current_ai_gallery_root_html}")
        if auto_show:
            self.show_ai_gallery_in_app()
    else:
        self.log_message("Nie udało się wygenerować galerii AI.", level="ERROR")
        QMessageBox.warning(self, "Błąd", "Nie udało się wygenerować galerii AI. Sprawdź logi konsoli.")
    
    self.set_buttons_for_processing(False)
    self.update_gallery_buttons_state()

def show_ai_gallery_in_app(self):
    ai_gallery_index_html_path = self.get_current_ai_gallery_index_html()
    if ai_gallery_index_html_path and os.path.exists(ai_gallery_index_html_path):
        abs_path = os.path.abspath(ai_gallery_index_html_path)
        self.web_view.setUrl(QUrl.fromLocalFile(abs_path))
        self.log_message(f"Ładowanie galerii AI do widoku: {abs_path}")
    else:
        self.log_message(f"❌ Nie znaleziono pliku galerii AI: {ai_gallery_index_html_path}", level="WARNING")
        self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Plik galerii AI nie istnieje.</p></body></html>")
6. Funkcje pomocnicze dla ścieżek AI
python# main.py - dodaj funkcje pomocnicze
def get_specific_ai_gallery_output_path(self):
    if not self.current_work_directory:
        return None
    sanitized_name = gallery_generator.sanitize_path_for_foldername(self.current_work_directory)
    return os.path.join(self.GLOBAL_AI_GALLERY_CACHE_ROOT_DIR, sanitized_name)

def get_current_ai_gallery_index_html(self):
    specific_ai_gallery_output_path = self.get_specific_ai_gallery_output_path()
    if not specific_ai_gallery_output_path:
        return None
    return os.path.join(specific_ai_gallery_output_path, "index.html")
7. Aktualizacja funkcji set_buttons_for_processing
python# main.py - aktualizuj funkcję
def set_buttons_for_processing(self, processing: bool):
    is_work_dir_selected = bool(self.current_work_directory)
    self.start_scan_button.setEnabled(not processing and is_work_dir_selected)
    self.rebuild_gallery_button.setEnabled(not processing and is_work_dir_selected)
    self.ai_scan_button.setEnabled(not processing and is_work_dir_selected)
    self.ai_gallery_button.setEnabled(not processing and is_work_dir_selected)
    self.toggle_mode_button.setEnabled(not processing and is_work_dir_selected)
    self.select_folder_button.setEnabled(not processing)
    self.update_gallery_buttons_state()
8. Aktualizacja update_status_label
python# main.py - aktualizuj funkcję
def update_status_label(self):
    if self.current_work_directory:
        self.folder_label.setText(f"Folder roboczy: {self.current_work_directory}")
        self.start_scan_button.setEnabled(True)
        self.rebuild_gallery_button.setEnabled(True)
        self.ai_scan_button.setEnabled(True)
        self.ai_gallery_button.setEnabled(True)
        self.toggle_mode_button.setEnabled(True)
    else:
        self.folder_label.setText("Folder roboczy: Brak (Wybierz folder)")
        self.start_scan_button.setEnabled(False)
        self.rebuild_gallery_button.setEnabled(False)
        self.ai_scan_button.setEnabled(False)
        self.ai_gallery_button.setEnabled(False)
        self.toggle_mode_button.setEnabled(False)
        self.web_view.setHtml("<html><body><p style='text-align:center; padding-top:50px;'>Wybierz folder roboczy.</p></body></html>")
    self.update_gallery_buttons_state()
9. Inicjalizacja nowych zmiennych
python# main.py - w __init__ dodaj
def __init__(self):
    # ... istniejący kod ...
    
    # Nowe zmienne dla AI
    self.ai_scanner_thread = None
    self.current_ai_gallery_root_html = None
    
    # ... reszta kodu ...
Zmiany w pliku ai_sbert_matcher.py
Dodanie funkcji do generowania galerii tylko z danymi AI
python# ai_sbert_matcher.py - dodaj na końcu pliku
def generate_ai_only_gallery_data(folder_path: str) -> Dict:
    """
    Generuje dane galerii zawierające tylko dopasowania AI
    """
    index_path = os.path.join(folder_path, "index.json")
    
    if not os.path.exists(index_path):
        return {}
        
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return {}
    
    # Sprawdź czy są dane AI
    if "AI_matches" not in data:
        return {}
    
    ai_matches = data.get("AI_matches", [])
    if not ai_matches:
        return {}
    
    # Utwórz strukturę danych tylko z dopasowaniami AI
    ai_gallery_data = {
        "folder_info": data.get("folder_info", {}),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "ai_info": {
            "processing_date": data.get("AI_processing_date"),
            "model_info": data.get("AI_model_info"),
            "statistics": data.get("AI_statistics"),
            "total_matches": len(ai_matches)
        }
    }
    
    # Dodaj nagłówek AI do folder_info
    ai_gallery_data["folder_info"]["gallery_type"] = "AI_POWERED"
    ai_gallery_data["folder_info"]["ai_matches_count"] = len(ai_matches)
    
    # Konwertuj dopasowania AI na format galerii
    for match in ai_matches:
        archive_file = match.get("archive_file")
        image_file = match.get("image_file")
        
        if not archive_file or not image_file:
            continue
            
        # Znajdź pełne ścieżki plików
        archive_path = os.path.join(folder_path, archive_file)
        image_path = os.path.join(folder_path, image_file)
        
        if os.path.exists(archive_path) and os.path.exists(image_path):
            file_info = {
                "name": archive_file,
                "path_absolute": os.path.abspath(archive_path),
                "size_bytes": os.path.getsize(archive_path) if os.path.exists(archive_path) else 0,
                "preview_found": True,
                "preview_name": image_file,
                "preview_path_absolute": os.path.abspath(image_path),
                "ai_match": True,
                "ai_confidence": match.get("confidence_level", "UNKNOWN"),
                "ai_similarity_score": match.get("similarity_score", 0.0)
            }
            
            file_info["size_readable"] = get_file_size_readable(file_info["size_bytes"])
            ai_gallery_data["files_with_previews"].append(file_info)
    
    return ai_gallery_data

def get_file_size_readable(size_bytes):
    """Funkcja pomocnicza do konwersji rozmiaru pliku"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"
Zmiany w pliku gallery_generator.py
Dodanie obsługi trybu AI
python# gallery_generator.py - dodaj na początku
def is_ai_mode_gallery(gallery_cache_root_dir: str) -> bool:
    """Sprawdza czy to galeria AI na podstawie ścieżki cache"""
    return "_gallery_cache_ai" in gallery_cache_root_dir

def process_single_index_json_ai_mode(
    index_json_path: str, 
    scanned_root_path: str, 
    gallery_output_base_path: str,
    template_env: Environment, 
    final_template_dir: str, 
    current_path_map: dict,
    progress_callback=None,
):
    """
    Wersja process_single_index_json dla trybu AI
    """
    try:
        with open(index_json_path, "r", encoding="utf-8") as f: 
            original_data = json.load(f)
    except Exception as e:
        print(f"ERROR: Odczyt {index_json_path}: {e}", flush=True)
        return None

    # Sprawdź czy są dane AI
    if "AI_matches" not in original_data:
        print(f"INFO: Brak danych AI w {index_json_path}, pomijam", flush=True)
        return None

    current_folder_abs_path = os.path.dirname(index_json_path)
    
    # Wygeneruj dane galerii AI
    import ai_sbert_matcher
    ai_gallery_data = ai_sbert_matcher.generate_ai_only_gallery_data(current_folder_abs_path)
    
    if not ai_gallery_data:
        print(f"INFO: Brak danych do galerii AI w {current_folder_abs_path}", flush=True)
        return None

    # Kontynuuj z oryginalną logiką, ale użyj ai_gallery_data zamiast original_data
    relative_path_from_scanned_root = os.path.relpath(current_folder_abs_path, scanned_root_path)
    map_key_for_current = _normalize_path_for_map_key(relative_path_from_scanned_root)
    hashed_gallery_segment = current_path_map.get(map_key_for_current)

    if hashed_gallery_segment is None:
        print(f"CRITICAL_ERROR: Brak hasha w mapie dla '{map_key_for_current}'. Pomijam {index_json_path}", flush=True)
        return None
        
    current_gallery_html_dir = os.path.join(gallery_output_base_path, hashed_gallery_segment)
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Tworzenie {current_gallery_html_dir}: {e}", flush=True)
        return None
    
    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    # Reszta logiki jak w oryginalnej funkcji, ale z ai_gallery_data
    # ... (skopiuj resztę z process_single_index_json, zastępując 'data' przez 'ai_gallery_data')
    
    print(f"INFO: Wygenerowano galerię AI dla: {relative_path_from_scanned_root}", flush=True)
    return output_html_file
Aktualizacja głównej funkcji generowania
python# gallery_generator.py - aktualizuj generate_full_gallery
def generate_full_gallery(scanned_root_path: str, gallery_cache_root_dir: str = "."):
    print(f"--- Rozpoczynam generate_full_gallery dla: {scanned_root_path} ---", flush=True)
    
    # Sprawdź czy to tryb AI
    ai_mode = is_ai_mode_gallery(gallery_cache_root_dir)
    if ai_mode:
        print(f"INFO: Tryb galerii AI aktywny", flush=True)
    
    # ... reszta oryginalnego kodu ...
    
    # W pętli przetwarzania użyj odpowiedniej funkcji
    for index_json_file_path in paths_to_process_with_index_json:
        if ai_mode:
            generated_html = process_single_index_json_ai_mode(
                index_json_file_path, 
                scanned_root_path, 
                gallery_specific_output_base,
                env, 
                final_template_dir,
                actual_path_map
            )
        else:
            generated_html = process_single_index_json(
                index_json_file_path, 
                scanned_root_path, 
                gallery_specific_output_base,
                env, 
                final_template_dir,
                actual_path_map
            )
        
        # ... reszta logiki ...
Nowy szablon dla galerii AI
Utwórz templates/gallery_ai_template.html
html<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 Galeria AI: {{ current_folder_display_name }}</title>
    <link rel="stylesheet" href="{{ css_path_prefix }}gallery_styles.css">
    <style>
        .ai-header {
            background: linear-gradient(135deg, #5a2d5a, #2d5a5a);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 24px;
            text-align: center;
        }
        .ai-stats {
            display: flex;
            justify-content: space-around;
            margin-top: 16px;
        }
        .ai-stat {
            text-align: center;
        }
        .ai-stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #3daee9;
        }
        .ai-match-confidence {
            position: absolute;
            top: 8px;
            left: 8px;
            background: rgba(61, 174, 233, 0.9);
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }
        .ai-match-confidence.HIGH {
            background: rgba(63, 185, 80, 0.9);
        }
        .ai-match-confidence.MEDIUM {
            background: rgba(210, 153, 34, 0.9);
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Nagłówek AI -->
        <div class="ai-header">
            <h1>🧠 Galeria AI: {{ current_folder_display_name }}</h1>
            <p>Inteligentne dopasowania obrazów do archiwów</p>
            {% if ai_info %}
            <div class="ai-stats">
                <div class="ai-stat">
                    <div class="ai-stat-value">{{ ai_info.total_matches }}</div>
                    <div>Dopasowań AI</div>
                </div>
                {% if ai_info.statistics %}
                <div class="ai-stat">
                    <div class="ai-stat-value">{{ "%.1f"|format(ai_info.statistics.match_rate * 100) }}%</div>
                    <div>Skuteczność</div>
                </div>
                <div class="ai-stat">
                    <div class="ai-stat-value">{{ ai_info.statistics.high_confidence_matches }}</div>
                    <div>Wysokiej pewności</div>
                </div>
                {% endif %}
            </div>
            {% endif %}
        </div>

        <!-- Breadcrumb -->
        <div class="breadcrumb">
            {% for part in breadcrumb_parts %}
                {% if part.link %}
                    <a href="{{ part.link }}">{{ part.name }}</a>
                {% else %}
                    <span>{{ part.name }}</span>
                {% endif %}
                {% if not loop.last %}<span>/</span>{% endif %}
            {% endfor %}
        </div>

        <!-- Dopasowania AI -->
        {% if files_with_previews %}
        <div class="section">
            <h2>🤖 Dopasowania AI ({{ files_with_previews|length }})</h2>
            <div class="gallery" id="aiMatchesGallery">
                {% for file in files_with_previews %}
                <div class="gallery-item">
                    <div class="ai-match-confidence {{ file.ai_confidence }}">
                        {{ file.ai_confidence }}
                        {% if file.ai_similarity_score %}
                        <br>{{ "%.1f"|format(file.ai_similarity_score * 100) }}%
                        {% endif %}
                    </div>
                    
                    {% if file.preview_path_absolute %}
                    <img src="file:///{{ file.preview_path_absolute.replace('\\', '/') }}" 
                         alt="Podgląd AI dla {{ file.name }}"
                         class="preview-image"
                         loading="lazy">
                    {% endif %}
                    
                    <p>
                        <a href="file:///{{ file.path_absolute.replace('\\', '/') }}" 
                           title="Otwórz: {{ file.name }}">{{ file.name }}</a>
                    </p>
                    <p class="file-info">{{ file.size_readable }}</p>
                    <p class="file-info" style="color: #3daee9;">
                        🧠 {{ file.preview_name }}
                    </p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% else %}
        <div class="section">
            <p>Brak dopasowań AI w tym folderze. Uruchom skanowanie AI.</p>
        </div>
        {% endif %}
    </div>

    <!-- Modal podglądu -->
    <div class="preview-backdrop" id="previewBackdrop"></div>
    <div class="preview-modal" id="previewModal">
        <img src="" alt="Podgląd" id="previewImg">
    </div>

    <script>
        // Podstawowa obsługa podglądu (skopiowana z głównego szablonu)
        document.addEventListener('DOMContentLoaded', function() {
            const previewModal = document.getElementById('previewModal');
            const previewBackdrop = document.getElementById('previewBackdrop');
            const previewImg = document.getElementById('previewImg');

            function showPreview(imageSrc) {
                if (!imageSrc || !previewModal || !previewBackdrop || !previewImg) return;
                previewBackdrop.style.display = 'block';
                previewModal.style.display = 'block';
                requestAnimationFrame(() => {
                    previewBackdrop.classList.add('show');
                    previewModal.classList.add('show');
                });
                previewImg.src = imageSrc;
            }

            function hidePreview() {
                if (!previewModal || !previewBackdrop || !previewImg) return;
                previewModal.classList.remove('show');
                previewBackdrop.classList.remove('show');
                setTimeout(() => {
                    previewModal.style.display = 'none';
                    previewBackdrop.style.display = 'none';
                    previewImg.src = '';
                }, 200);
            }

            // Obsługa obrazów
            document.querySelectorAll('.preview-image').forEach(img => {
                let hoverTimeout;
                img.addEventListener('mouseenter', function() {
                    hoverTimeout = setTimeout(() => {
                        showPreview(this.srcRetryMContinueEditjavascript                       showPreview(this.src);
                   }, 1000);
               });
               
               img.addEventListener('mouseleave', function() {
                   clearTimeout(hoverTimeout);
                   hidePreview();
               });
           });

           // Zamykanie modalu
           previewBackdrop.addEventListener('click', hidePreview);
           document.addEventListener('keydown', function(e) {
               if (e.key === 'Escape') hidePreview();
           });
       });
   </script>
</body>
</html>
Aktualizacja ai_sbert_matcher.py - kompletna funkcja generate_ai_only_gallery_data
python# ai_sbert_matcher.py - kompletna implementacja
def generate_ai_only_gallery_data(folder_path: str) -> Dict:
    """
    Generuje dane galerii zawierające tylko dopasowania AI
    """
    index_path = os.path.join(folder_path, "index.json")
    
    if not os.path.exists(index_path):
        logger.warning(f"Brak index.json w {folder_path}")
        return {}
        
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Błąd odczytu index.json w {folder_path}: {e}")
        return {}
    
    # Sprawdź czy są dane AI
    if "AI_matches" not in data:
        logger.debug(f"Brak danych AI_matches w {folder_path}")
        return {}
    
    ai_matches = data.get("AI_matches", [])
    if not ai_matches:
        logger.debug(f"Pusta lista AI_matches w {folder_path}")
        return {}
    
    logger.info(f"Generuję dane galerii AI dla {folder_path} z {len(ai_matches)} dopasowaniami")
    
    # Utwórz strukturę danych tylko z dopasowaniami AI
    ai_gallery_data = {
        "folder_info": data.get("folder_info", {}).copy(),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "ai_info": {
            "processing_date": data.get("AI_processing_date"),
            "model_info": data.get("AI_model_info", {}),
            "statistics": data.get("AI_statistics", {}),
            "total_matches": len(ai_matches)
        }
    }
    
    # Dodaj informacje AI do folder_info
    ai_gallery_data["folder_info"]["gallery_type"] = "AI_POWERED"
    ai_gallery_data["folder_info"]["ai_matches_count"] = len(ai_matches)
    ai_gallery_data["folder_info"]["ai_scan_date"] = data.get("AI_processing_date")
    
    # Konwertuj dopasowania AI na format galerii
    processed_matches = 0
    for match in ai_matches:
        archive_file = match.get("archive_file")
        image_file = match.get("image_file")
        
        if not archive_file or not image_file:
            logger.warning(f"Niepełne dopasowanie AI: {match}")
            continue
            
        # Znajdź pełne ścieżki plików
        archive_path = os.path.join(folder_path, archive_file)
        image_path = os.path.join(folder_path, image_file)
        
        if not os.path.exists(archive_path):
            logger.warning(f"Plik archiwum nie istnieje: {archive_path}")
            continue
            
        if not os.path.exists(image_path):
            logger.warning(f"Plik obrazu nie istnieje: {image_path}")
            continue
        
        try:
            archive_size = os.path.getsize(archive_path)
        except OSError:
            archive_size = 0
            
        file_info = {
            "name": archive_file,
            "path_absolute": os.path.abspath(archive_path),
            "size_bytes": archive_size,
            "size_readable": get_file_size_readable_ai(archive_size),
            "preview_found": True,
            "preview_name": image_file,
            "preview_path_absolute": os.path.abspath(image_path),
            "preview_relative_path": f"file:///{os.path.abspath(image_path).replace(os.sep, '/')}",
            "archive_link": f"file:///{os.path.abspath(archive_path).replace(os.sep, '/')}",
            "ai_match": True,
            "ai_confidence": match.get("confidence_level", "UNKNOWN"),
            "ai_similarity_score": match.get("similarity_score", 0.0),
            "ai_matching_method": match.get("matching_method", "SBERT"),
            "ai_timestamp": match.get("timestamp")
        }
        
        # Dodaj kolor archiwum jeśli dostępny
        file_ext = os.path.splitext(archive_file)[1].lower()
        try:
            import config_manager
            file_info["archive_color"] = config_manager.get_archive_color(file_ext)
        except:
            file_info["archive_color"] = "#6c757d"
        
        ai_gallery_data["files_with_previews"].append(file_info)
        processed_matches += 1
    
    logger.info(f"Przetworzone {processed_matches}/{len(ai_matches)} dopasowań AI dla {folder_path}")
    
    return ai_gallery_data

def get_file_size_readable_ai(size_bytes):
    """Funkcja pomocnicza do konwersji rozmiaru pliku dla AI"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_name) - 1:
        size_float /= 1024.0
        i += 1
    return f"{size_float:.2f} {size_name[i]}"
Kompletna aktualizacja gallery_generator.py
python# gallery_generator.py - dodaj na początku po istniejących importach
import ai_sbert_matcher

# gallery_generator.py - kompletna implementacja process_single_index_json_ai_mode
def process_single_index_json_ai_mode(
    index_json_path: str, 
    scanned_root_path: str, 
    gallery_output_base_path: str,
    template_env: Environment, 
    final_template_dir: str, 
    current_path_map: dict,
    progress_callback=None,
):
    """
    Wersja process_single_index_json dla trybu AI - generuje galerię tylko z dopasowaniami AI
    """
    current_folder_abs_path = os.path.dirname(index_json_path)
    
    # Wygeneruj dane galerii AI
    ai_gallery_data = ai_sbert_matcher.generate_ai_only_gallery_data(current_folder_abs_path)
    
    if not ai_gallery_data or not ai_gallery_data.get("files_with_previews"):
        print(f"INFO: Brak danych AI do galerii w {current_folder_abs_path}, pomijam", flush=True)
        return None

    relative_path_from_scanned_root = os.path.relpath(current_folder_abs_path, scanned_root_path)
    map_key_for_current = _normalize_path_for_map_key(relative_path_from_scanned_root)
    hashed_gallery_segment = current_path_map.get(map_key_for_current)

    if hashed_gallery_segment is None:
        print(f"CRITICAL_ERROR: Brak hasha w mapie dla '{map_key_for_current}'. Pomijam {index_json_path}", flush=True)
        return None
        
    current_gallery_html_dir = os.path.join(gallery_output_base_path, hashed_gallery_segment)
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Tworzenie {current_gallery_html_dir}: {e}", flush=True)
        return None
    
    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    print(f"INFO: Rozpoczynam generowanie HTML AI dla: {relative_path_from_scanned_root} -> {output_html_file}", flush=True)

    try:
        # Spróbuj użyć szablonu AI, jeśli nie ma to użyj zwykłego
        try:
            template = template_env.get_template("gallery_ai_template.html")
            print(f"INFO: Używam szablonu AI dla {relative_path_from_scanned_root}", flush=True)
        except:
            template = template_env.get_template("gallery_template.html")
            print(f"INFO: Używam standardowego szablonu dla AI w {relative_path_from_scanned_root}", flush=True)
    except Exception as e:
        print(f"ERROR: Ładowanie szablonu: {e}", flush=True)
        return None

    is_root_index_page = (relative_path_from_scanned_root == ".")
    
    path_components_for_depth = []
    if relative_path_from_scanned_root != ".":
        path_components_for_depth = os.path.normpath(relative_path_from_scanned_root).split(os.sep)
    calculated_depth = len(path_components_for_depth)

    template_data = {
        "folder_info": ai_gallery_data.get("folder_info", {}),
        "files_with_previews": ai_gallery_data.get("files_with_previews", []),
        "files_without_previews": [],  # Puste w trybie AI
        "other_images": [],  # Puste w trybie AI
        "subfolders": [],  # Zostanie wypełnione poniżej
        "ai_info": ai_gallery_data.get("ai_info", {}),
        "current_folder_display_name": (
            f"🧠 AI: {os.path.basename(current_folder_abs_path)}" if not is_root_index_page
            else f"🧠 AI: {os.path.basename(scanned_root_path)}"
        ),
        "breadcrumb_parts": [],
        "depth": calculated_depth, 
        "is_root_gallery_index": is_root_index_page,
        "css_path_prefix": "" if is_root_index_page else "../",
        "scanned_root_path_abs_for_template": os.path.abspath(scanned_root_path),
        "current_rel_path_for_template": relative_path_from_scanned_root,
        "complete_path_map_for_template": current_path_map,
        "gallery_mode": "ai"
    }

    gallery_root_name_for_bc = f"🧠 AI: {os.path.basename(scanned_root_path)}"
    template_data["breadcrumb_parts"], _ = generate_breadcrumb_hashed(
        relative_path_from_scanned_root, gallery_root_name_for_bc, is_root_index_page, current_path_map
    )
    
    # Znajdź podfoldery z danymi AI
    discovered_subfolders_data = []
    try:
        for entry in os.scandir(current_folder_abs_path):
            if entry.is_dir(follow_symlinks=False):
                sub_abs_path = entry.path
                sub_index_json_path = os.path.join(sub_abs_path, "index.json")
                if os.path.exists(sub_index_json_path):
                    # Sprawdź czy podfolder ma dane AI
                    try:
                        with open(sub_index_json_path, 'r', encoding='utf-8') as f:
                            sub_data = json.load(f)
                            if "AI_matches" not in sub_data or not sub_data.get("AI_matches"):
                                continue  # Pomiń podfoldery bez danych AI
                    except:
                        continue
                    
                    sub_original_relative_path = os.path.relpath(sub_abs_path, scanned_root_path)
                    sub_map_key = _normalize_path_for_map_key(sub_original_relative_path)
                    sub_hashed_name = current_path_map.get(sub_map_key)
                    if sub_hashed_name is None:
                        print(f"ERROR_LINK_SUB: Brak mapowania dla podfolderu AI '{sub_map_key}'. Pomijam.", flush=True)
                        continue
                    
                    # Pobierz statystyki AI
                    ai_matches_count = len(sub_data.get("AI_matches", []))
                    ai_stats = sub_data.get("AI_statistics", {})
                    
                    link_prefix_for_subfolder = "" if is_root_index_page else "../"
                    discovered_subfolders_data.append({
                        "name": f"🧠 {entry.name}",
                        "link": f"{link_prefix_for_subfolder}{sub_hashed_name}/index.html",
                        "total_size_readable": f"{ai_matches_count} dopasowań AI",
                        "file_count": ai_matches_count,
                        "subdir_count": 0,
                        "ai_folder": True
                    })
    except Exception as e_scan_sub:
        print(f"ERROR: Skanowanie podfolderów AI w {current_folder_abs_path}: {e_scan_sub}", flush=True)
    
    template_data["subfolders"] = sorted(discovered_subfolders_data, key=lambda sf: sf["name"].lower())

    try:
        html_content = template.render(template_data)
        if not html_content or len(html_content) < 100:
            raise ValueError("HTML AI pusty/za krótki.")
        
        temp_html_file = output_html_file + f".tmp_ai_{int(time.time())}"
        with open(temp_html_file, "w", encoding="utf-8") as f_html:
            f_html.write(html_content)
        
        if os.path.exists(temp_html_file) and os.path.getsize(temp_html_file) > 0:
            if os.path.exists(output_html_file):
                os.remove(output_html_file)
            os.rename(temp_html_file, output_html_file)
        else:
            if os.path.exists(temp_html_file):
                os.remove(temp_html_file)
            raise IOError(f"Plik tymczasowy AI {temp_html_file} nie zapisany.")
    except Exception as e_html:
        print(f"ERROR: Generowanie HTML AI dla '{relative_path_from_scanned_root}': {e_html}", flush=True)
        return None
    
    print(f"INFO: Pomyślnie wygenerowano galerię AI: {output_html_file}", flush=True)
    return output_html_file

# gallery_generator.py - aktualizacja głównej funkcji
def generate_full_gallery(scanned_root_path: str, gallery_cache_root_dir: str = "."):
    print(f"--- Rozpoczynam generate_full_gallery dla: {scanned_root_path} ---", flush=True)
    
    # Sprawdź czy to tryb AI
    ai_mode = is_ai_mode_gallery(gallery_cache_root_dir)
    if ai_mode:
        print(f"INFO: 🧠 Tryb galerii AI aktywny", flush=True)
    
    if not os.path.isdir(scanned_root_path):
        print(f"ERROR: Ścieżka skanowania '{scanned_root_path}' nie jest katalogiem.", flush=True)
        return None

    scanned_root_path = os.path.abspath(scanned_root_path)
    gallery_cache_root_dir = os.path.abspath(gallery_cache_root_dir)

    sanitized_top_level_name = sanitize_path_for_foldername(scanned_root_path)
    gallery_specific_output_base = os.path.join(gallery_cache_root_dir, sanitized_top_level_name)
    
    if ai_mode:
        print(f"INFO: Katalog bazowy galerii AI: {gallery_specific_output_base}", flush=True)
    
    try:
        os.makedirs(gallery_specific_output_base, exist_ok=True)
        print(f"INFO: Katalog bazowy galerii: {gallery_specific_output_base}", flush=True)
    except Exception as e:
        print(f"ERROR: Tworzenie '{gallery_specific_output_base}': {e}", flush=True)
        return None

    actual_path_map = build_path_map(scanned_root_path)
    save_path_map_to_file(actual_path_map, gallery_specific_output_base)
    
    if not actual_path_map:
        print(f"ERROR: Mapa ścieżek jest pusta. Brak plików index.json w '{scanned_root_path}'.", flush=True)
        return None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    td_primary = os.path.join(script_dir, "templates")
    td_alt = "templates" 
    final_template_dir = td_primary if os.path.isdir(td_primary) else (os.path.abspath(td_alt) if os.path.isdir(td_alt) else None)
    
    if not final_template_dir:
        print(f"ERROR: Brak katalogu szablonów. Sprawdzono: '{td_primary}', '{os.path.abspath(td_alt)}'", flush=True)
        return None
    print(f"INFO: Używam szablonów z: {final_template_dir}", flush=True)

    try:
        env = Environment(loader=FileSystemLoader(final_template_dir), autoescape=select_autoescape(['html', 'xml']))
        # Sprawdź dostępność szablonów
        if ai_mode:
            try:
                env.get_template("gallery_ai_template.html")
                print(f"INFO: Szablon AI dostępny", flush=True)
            except:
                print(f"WARNING: Brak szablonu AI, używam standardowego", flush=True)
        else:
            env.get_template("gallery_template.html") 
    except Exception as e:
        print(f"ERROR: Inicjalizacja Jinja2: {e}", flush=True)
        return None

    css_src = os.path.join(final_template_dir, "gallery_styles.css")
    css_dest = os.path.join(gallery_specific_output_base, "gallery_styles.css")
    if os.path.exists(css_src):
        try: 
            shutil.copy2(css_src, css_dest)
            print(f"INFO: Skopiowano CSS: {css_src} -> {css_dest}", flush=True)
        except Exception as e: 
            print(f"ERROR: Kopiowanie CSS: {e}", flush=True)
    else:
        print(f"WARNING: Plik CSS ({css_src}) nie znaleziony.", flush=True)

    root_gallery_html_path = None
    processed_count = 0
    error_count = 0
    paths_to_process_with_index_json = []
    
    for dirpath_iter, _, filenames_iter in os.walk(scanned_root_path, onerror=walk_error_handler):
        if os.path.islink(dirpath_iter): 
            continue
        if "index.json" in filenames_iter:
            paths_to_process_with_index_json.append(os.path.join(dirpath_iter, "index.json"))
    
    paths_to_process_with_index_json.sort()
    print(f"INFO: Znaleziono {len(paths_to_process_with_index_json)} plików index.json.", flush=True)

    for index_json_file_path in paths_to_process_with_index_json:
        if ai_mode:
            generated_html = process_single_index_json_ai_mode(
                index_json_file_path, 
                scanned_root_path, 
                gallery_specific_output_base,
                env, 
                final_template_dir,
                actual_path_map
            )
        else:
            generated_html = process_single_index_json(
                index_json_file_path, 
                scanned_root_path, 
                gallery_specific_output_base,
                env, 
                final_template_dir,
                actual_path_map
            )
            
        if generated_html and os.path.exists(generated_html):
            processed_count += 1
            current_folder_abs = os.path.dirname(index_json_file_path)
            if os.path.abspath(current_folder_abs) == os.path.abspath(scanned_root_path):
                expected_root_output_html = os.path.join(gallery_specific_output_base, "index.html")
                if os.path.abspath(generated_html) == os.path.abspath(expected_root_output_html):
                    root_gallery_html_path = generated_html
                    mode_info = "AI" if ai_mode else "klasycznej"
                    print(f"INFO: Ustawiono główny HTML galerii {mode_info}: {root_gallery_html_path}", flush=True)
        else: 
            error_count += 1
            print(f"ERROR: Nie udało się wygenerować HTML dla {index_json_file_path}", flush=True)
    
    mode_info = "AI" if ai_mode else "klasycznej"
    print(f"INFO: Podsumowanie galerii {mode_info}: Przetworzono {processed_count}, Błędów {error_count}.", flush=True)
    
    if not root_gallery_html_path and processed_count > 0:
        potential_root_html = os.path.join(gallery_specific_output_base, "index.html")
        if os.path.exists(potential_root_html):
            root_gallery_html_path = potential_root_html
            print(f"INFO: Główny HTML galerii {mode_info} znaleziony po pętli: {root_gallery_html_path}", flush=True)

    if root_gallery_html_path:
        print(f"SUCCESS: Główny HTML galerii {mode_info}: {root_gallery_html_path}", flush=True)
    else:
        print(f"ERROR: Główny HTML galerii {mode_info} nie został wygenerowany lub znaleziony.", flush=True)
    
    print(f"--- Zakończono generate_full_gallery {mode_info} dla: {scanned_root_path} ---", flush=True)
    return root_gallery_html_path
Ostatnie aktualizacje w main.py
python# main.py - aktualizacja closeEvent
def closeEvent(self, event):
    # Zatrzymywanie wątków przy zamykaniu
    threads_running = False
    if self.scanner_thread and self.scanner_thread.isRunning():
        threads_running = True
        self.scanner_thread.quit()
    if self.gallery_thread and self.gallery_thread.isRunning():
        threads_running = True
        self.gallery_thread.quit()
    if self.ai_scanner_thread and self.ai_scanner_thread.isRunning():  # Dodano AI thread
        threads_running = True
        self.ai_scanner_thread.quit()

    if threads_running:
        if self.scanner_thread: self.scanner_thread.wait(500) 
        if self.gallery_thread: self.gallery_thread.wait(500)
        if self.ai_scanner_thread: self.ai_scanner_thread.wait(500)  # Dodano AI thread
    event.accept()
Podsumowanie zmian
Teraz Twoja aplikacja ma:

🤖 Przycisk "Skanuj AI" - uruchamia ai_sbert_matcher.py na całym drzewie folderów
🧠 Przycisk "Galeria AI" - generuje galerię tylko z dopasowaniami AI
🔄 Przycisk przełączania trybu - przełącza między galerią klasyczną a AI
Osobny cache - galerie AI mają oddzielny katalog _gallery_cache_ai
Dedykowany szablon AI - gallery_ai_template.html z wizualizacją pewności dopasowań
Wskaźniki jakości - pokazuje procent pewności i statystyki AI

Funkcje działają następujące:

Najpierw uruchamiasz skanowanie klasyczne
Potem skanowanie AI (analizuje istniejące dane)
Możesz przełączać między widokami klasycznym i AI
Galerie mają osobne cache, więc nie interferują ze sobą

Czy chcesz, żebym wyjaśnił jakąś część implementacji lub dodał dodatkowe funkcje?