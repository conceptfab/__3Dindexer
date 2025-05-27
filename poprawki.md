1. Modernizacja CSS - Ciemny schemat
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
    backdrop-filter: blur(10px);
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

.section h2 {
    color: var(--text-primary);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 10px;
    margin-bottom: 20px;
}

.subfolders-list, .no-preview-list {
    list-style: none;
    padding: 0;
    background: var(--bg-tertiary);
    border-radius: 8px;
    overflow: hidden;
}

.subfolders-list li, .no-preview-list li {
    padding: 15px 20px;
    border-bottom: 1px solid var(--border);
    transition: var(--transition);
}

.subfolders-list li:hover, .no-preview-list li:hover {
    background: var(--bg-primary);
}

.folder-stats {
    background: linear-gradient(135deg, var(--bg-tertiary) 0%, #1e3a5f 100%);
    padding: 20px;
    border-radius: 12px;
    border-left: 4px solid var(--accent);
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
    
    .container {
        padding: 20px;
        margin: 10px;
    }
}
2. Rozszerzenie konfiguracji o podgląd
Plik: config.json
json{
    "work_directory": "W:/3Dsky/ARCHITECTURE",
    "preview_size": 400,
    "thumbnail_size": 150,
    "dark_theme": true,
    "performance": {
        "max_worker_threads": 4,
        "cache_previews": true,
        "lazy_loading": true
    }
}
3. Rozbudowa config_manager.py
Plik: config_manager.py
python# config_manager.py
import json
import os
from typing import Optional, Dict, Any

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "work_directory": None,
    "preview_size": 400,
    "thumbnail_size": 150,
    "dark_theme": True,
    "performance": {
        "max_worker_threads": 4,
        "cache_previews": True,
        "lazy_loading": True
    }
}

def load_config() -> Dict[str, Any]:
    """Wczytuje konfigurację z pliku config.json z domyślnymi wartościami."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                # Scalenie z domyślną konfiguracją
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                # Upewnij się, że performance jest słownikiem
                if 'performance' not in config:
                    config['performance'] = DEFAULT_CONFIG['performance']
                else:
                    default_perf = DEFAULT_CONFIG['performance'].copy()
                    default_perf.update(config['performance'])
                    config['performance'] = default_perf
                return config
        except json.JSONDecodeError:
            print(f"Błąd: Plik {CONFIG_FILE} jest uszkodzony. Używam domyślnych wartości.")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_data: Dict[str, Any]) -> bool:
    """Zapisuje konfigurację do pliku config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except IOError:
        print(f"Błąd: Nie można zapisać pliku {CONFIG_FILE}.")
        return False

def get_config_value(key: str, default=None) -> Any:
    """Pobiera wartość z konfiguracji."""
    config = load_config()
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    return value

def set_config_value(key: str, value: Any) -> bool:
    """Ustawia wartość w konfiguracji."""
    config = load_config()
    keys = key.split('.')
    current = config
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value
    return save_config(config)

# Funkcje pomocnicze dla kompatybilności
def get_work_directory() -> Optional[str]:
    return get_config_value("work_directory")

def set_work_directory(path: str) -> bool:
    return set_config_value("work_directory", path)

def get_preview_size() -> int:
    return get_config_value("preview_size", 400)

def get_thumbnail_size() -> int:
    return get_config_value("thumbnail_size", 150)
4. Optymalizacja scanner_logic.py z wielowątkowością
Plik: scanner_logic.py
python# scanner_logic.py
import os
import json
import re
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import config_manager

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg')

@dataclass
class FileInfo:
    name: str
    path_absolute: str
    size_bytes: int
    size_readable: str
    modified_time: float
    file_hash: Optional[str] = None

@dataclass
class FolderScanResult:
    folder_info: Dict[str, Any]
    files_with_previews: List[Dict[str, Any]]
    files_without_previews: List[Dict[str, Any]]
    other_images: List[Dict[str, Any]]

def get_file_size_readable(size_bytes: int) -> str:
    """Konwertuje rozmiar pliku w bajtach na czytelny format."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def get_file_hash(filepath: str) -> Optional[str]:
    """Oblicza hash MD5 pliku do sprawdzania zmian."""
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (OSError, IOError):
        return None

def get_file_info(filepath: str, calculate_hash: bool = False) -> Optional[FileInfo]:
    """Pobiera informacje o pliku."""
    try:
        stat = os.stat(filepath)
        file_hash = get_file_hash(filepath) if calculate_hash else None
        
        return FileInfo(
            name=os.path.basename(filepath),
            path_absolute=os.path.abspath(filepath),
            size_bytes=stat.st_size,
            size_readable=get_file_size_readable(stat.st_size),
            modified_time=stat.st_mtime,
            file_hash=file_hash
        )
    except OSError:
        return None

def get_folder_stats(folder_path: str) -> Dict[str, Any]:
    """Zbiera statystyki dotyczące folderu z cache'em."""
    cache_file = os.path.join(folder_path, ".folder_cache.json")
    folder_mtime = os.path.getmtime(folder_path)
    
    # Sprawdź czy cache jest aktualny
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if cache_data.get('folder_mtime', 0) >= folder_mtime:
                    return cache_data['stats']
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    
    # Oblicz statystyki
    total_size_bytes = 0
    file_count = 0
    subdir_count = 0
    
    try:
        with ThreadPoolExecutor(max_workers=config_manager.get_config_value('performance.max_worker_threads', 4)) as executor:
            futures = []
            
            for entry in os.scandir(folder_path):
                if entry.is_file() and entry.name.lower() not in ["index.json", ".folder_cache.json"]:
                    futures.append(executor.submit(entry.stat))
                    file_count += 1
                elif entry.is_dir():
                    subdir_count += 1
            
            for future in as_completed(futures):
                try:
                    stat_result = future.result()
                    total_size_bytes += stat_result.st_size
                except OSError:
                    pass
                    
    except OSError:
        pass
    
    stats = {
        "path": os.path.abspath(folder_path),
        "total_size_bytes": total_size_bytes,
        "total_size_readable": get_file_size_readable(total_size_bytes),
        "file_count": file_count,
        "subdir_count": subdir_count
    }
    
    # Zapisz cache
    try:
        cache_data = {
            'folder_mtime': folder_mtime,
            'stats': stats
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
    
    return stats

def find_matching_preview_for_file(base_filename: str, image_files_in_folder: List[str]) -> Optional[str]:
    """Szuka pasującego pliku podglądu dla dowolnego pliku."""
    extensions = '|'.join(ext[1:] for ext in IMAGE_EXTENSIONS)
    pattern = re.compile(rf"^{re.escape(base_filename)}(?:_\d+)?\.({extensions})$", re.IGNORECASE)
    
    for img_path in image_files_in_folder:
        if pattern.match(os.path.basename(img_path)):
            return img_path
    return None

def process_single_folder(folder_path: str) -> Optional[FolderScanResult]:
    """Przetwarza pojedynczy folder bez rekursji."""
    try:
        all_items = list(os.scandir(folder_path))
        
        # Podziel na kategorie
        image_files = []
        other_files = []
        
        with ThreadPoolExecutor(max_workers=config_manager.get_config_value('performance.max_worker_threads', 4)) as executor:
            file_info_futures = {}
            
            for entry in all_items:
                if entry.is_file() and entry.name.lower() not in ["index.json", ".folder_cache.json"]:
                    future = executor.submit(get_file_info, entry.path, False)
                    file_info_futures[future] = entry
            
            for future in as_completed(file_info_futures):
                entry = file_info_futures[future]
                file_info = future.result()
                
                if file_info:
                    if entry.name.lower().endswith(IMAGE_EXTENSIONS):
                        image_files.append(file_info)
                    else:
                        other_files.append(file_info)
        
        # Znajdź dopasowania podglądów
        image_paths = [img.path_absolute for img in image_files]
        found_previews = set()
        
        files_with_previews = []
        files_without_previews = []
        
        for file_info in other_files:
            file_basename, _ = os.path.splitext(file_info.name)
            preview_path = find_matching_preview_for_file(file_basename, image_paths)
            
            file_dict = {
                "name": file_info.name,
                "path_absolute": file_info.path_absolute,
                "size_bytes": file_info.size_bytes,
                "size_readable": file_info.size_readable,
                "modified_time": file_info.modified_time
            }
            
            if preview_path:
                file_dict.update({
                    "preview_found": True,
                    "preview_name": os.path.basename(preview_path),
                    "preview_path_absolute": preview_path
                })
                files_with_previews.append(file_dict)
                found_previews.add(preview_path)
            else:
                file_dict["preview_found"] = False
                files_without_previews.append(file_dict)
        
        # Obrazy bez dopasowań
        other_images = []
        for img_info in image_files:
            if img_info.path_absolute not in found_previews:
                other_images.append({
                    "name": img_info.name,
                    "path_absolute": img_info.path_absolute,
                    "size_bytes": img_info.size_bytes,
                    "size_readable": img_info.size_readable,
                    "modified_time": img_info.modified_time
                })
        
        return FolderScanResult(
            folder_info=get_folder_stats(folder_path),
            files_with_previews=files_with_previews,
            files_without_previews=files_without_previews,
            other_images=other_images
        )
        
    except OSError as e:
        print(f"Błąd dostępu do folderu {folder_path}: {e}")
        return None

def should_skip_folder(folder_path: str) -> bool:
    """Sprawdza czy folder powinien być pominięty."""
    folder_name = os.path.basename(folder_path).lower()
    skip_patterns = ['.git', '__pycache__', 'node_modules', '.vscode', '_gallery_cache']
    return any(pattern in folder_name for pattern in skip_patterns)

def collect_folders_to_scan(root_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> List[str]:
    """Zbiera wszystkie foldery do zeskanowania."""
    folders_to_scan = []
    
    for root, dirs, _ in os.walk(root_path):
        # Filtruj foldery do pominięcia
        dirs[:] = [d for d in dirs if not should_skip_folder(os.path.join(root, d))]
        
        folders_to_scan.append(root)
        if progress_callback:
            progress_callback(f"Znaleziono folder: {root}")
    
    return folders_to_scan

def process_folder_batch(folders: List[str], progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, FolderScanResult]:
    """Przetwarza grupę folderów równolegle."""
    results = {}
    max_workers = config_manager.get_config_value('performance.max_worker_threads', 4)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_folder = {
            executor.submit(process_single_folder, folder): folder 
            for folder in folders
        }
        
        for future in as_completed(future_to_folder):
            folder = future_to_folder[future]
            try:
                result = future.result()
                if result:
                    results[folder] = result
                    if progress_callback:
                        progress_callback(f"Przetworzono: {folder}")
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Błąd przetwarzania {folder}: {e}")
    
    return results

def save_index_json(folder_path: str, scan_result: FolderScanResult, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
    """Zapisuje index.json dla folderu."""
    index_data = {
        "folder_info": scan_result.folder_info,
        "files_with_previews": scan_result.files_with_previews,
        "files_without_previews": scan_result.files_without_previews,
        "other_images": scan_result.other_images,
        "scan_timestamp": time.time()
    }
    
    index_json_path = os.path.join(folder_path, "index.json")
    try:
        with open(index_json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        if progress_callback:
            progress_callback(f"Zapisano: {index_json_path}")
        return True
    except IOError as e:
        if progress_callback:
            progress_callback(f"Błąd zapisu {index_json_path}: {e}")
        return False

def start_scanning(root_folder_path: str, progress_callback: Optional[Callable[[str], None]] = None):
    """Rozpoczyna zoptymalizowane skanowanie z wielowątkowością."""
    if not os.path.isdir(root_folder_path):
        if progress_callback:
            progress_callback(f"Błąd: Ścieżka {root_folder_path} nie jest folderem lub nie istnieje.")
        return
    
    start_time = time.time()
    
    if progress_callback:
        progress_callback("Zbieranie listy folderów...")
    
    folders_to_scan = collect_folders_to_scan(root_folder_path, progress_callback)
    
    if progress_callback:
        progress_callback(f"Znaleziono {len(folders_to_scan)} folderów do zeskanowania.")
        progress_callback("Rozpoczynanie skanowania równoległego...")
    
    # Przetwarzaj foldery w grupach
    batch_size = config_manager.get_config_value('performance.max_worker_threads', 4) * 2
    total_processed = 0
    
    for i in range(0, len(folders_to_scan), batch_size):
        batch = folders_to_scan[i:i+batch_size]
        results = process_folder_batch(batch, progress_callback)
        
        # Zapisz wyniki
        for folder_path, scan_result in results.items():
            save_index_json(folder_path, scan_result, progress_callback)
        
        total_processed += len(batch)
        if progress_callback:
            progress_callback(f"Przetworzono {total_processed}/{len(folders_to_scan)} folderów")
    
    elapsed_time = time.time() - start_time
    if progress_callback:
        progress_callback(f"Skanowanie zakończone w {elapsed_time:.2f} sekund.")
5. Ulepszony szablon HTML z podglądem
Plik: templates/gallery_template.html (fragment - głównie JavaScript)
Dodaj do sekcji <script> na końcu pliku:
javascriptdocument.addEventListener('DOMContentLoaded', function () {
    const slider = document.getElementById('sizeSlider');
    const sizeValueDisplay = document.getElementById('sizeValue');
    const galleries = [
        document.getElementById('filesWithPreviewsGallery'),
        document.getElementById('otherImagesGallery')
    ].filter(Boolean);

    // Konfiguracja podglądu z config.json
    const previewSize = {{ get_config_value('preview_size', 400) }};
    
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
        previewImg.style.maxWidth = previewSize + 'px';
        previewImg.style.maxHeight = previewSize + 'px';
        
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
        const images = gallery.querySelectorAll('.gallery-item img');
        images.forEach(img => {
            let hoverTimeout;
            
            img.addEventListener('mouseenter', function(e) {
                hoverTimeout = setTimeout(() => {
                    showPreview(this.src, e);
                }, 500); // Opóźnienie 500ms
            });
            
            img.addEventListener('mouseleave', function() {
                clearTimeout(hoverTimeout);
                setTimeout(hidePreview, 200); // Krótkie opóźnienie przed ukryciem
            });
        });
    });

    // Ukryj podgląd po kliknięciu
    previewOverlay.addEventListener('click', hidePreview);
    
    // Ukryj podgląd po naciśnięciu ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hidePreview();
        }
    });

    // Lazy loading dla obrazów
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        });

        galleries.forEach(gallery => {
            const images = gallery.querySelectorAll('img[data-src]');
            images.forEach(img => imageObserver.observe(img));
        });
    }
});
6. Podsumowanie optymalizacji
Główne ulepszenia:

Wielowątkowość: Scanner używa ThreadPoolExecutor do równoległego przetwarzania folderów
Cache'owanie: Statystyki folderów są cache'owane w .folder_cache.json
Lazy loading: Obrazy ładują się dopiero gdy są widoczne
Nowoczesny interfejs: Ciemny schemat, płynne animacje, hover effects
Podgląd na hover: Możliwość podglądu miniaturek w większym rozmiarze
Konfigurowalność: Rozszerzona konfiguracja z możliwością dostrajania wydajności
Responsywność: Lepsze zachowanie na różnych rozmiarach ekranu

Kolejne kroki do wdrożenia:

Wprowadź zmiany we wszystkich plikach zgodnie z propozycjami
Przetestuj wydajność na dużych folderach
Dostosuj liczbę wątków w konfiguracji według potrzeb
Rozważ dodanie cache'owania miniaturek obrazów
Możesz dodać progres bar dla operacji skanowania

Te zmiany znacznie poprawią zarówno wydajność, jak i wygląd aplikacji, czyniąc ją bardziej nowoczesną i użyteczną.