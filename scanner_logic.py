# scanner_logic.py
import json
import logging
import os
import time  # Dodane dla retry mechanism
from datetime import datetime
from pathlib import Path

import config_manager


# Konfiguracja loggera
def setup_logger(log_dir="logs", enable_file_logging=None):
    """Konfiguruje i zwraca logger z opcjonalnym zapisem do pliku."""
    # Sprawdź ustawienie z konfiguracji jeśli nie podano explicite
    if enable_file_logging is None:
        enable_file_logging = config_manager.get_config_value(
            "enable_file_logging", False
        )

    logger = logging.getLogger("scanner")
    logger.setLevel(logging.DEBUG)

    # Wyczyść istniejące handlery
    logger.handlers.clear()

    # Format logów
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler dla konsoli - zawsze aktywny
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler dla pliku - opcjonalny
    if enable_file_logging:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        log_file = log_path / f"scanner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Inicjalizacja loggera
logger = setup_logger()

# Usunięto ARCHIVE_EXTENSIONS
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",  # JPEG i warianty
    ".png",
    ".apng",  # PNG i animowane PNG
    ".gif",  # GIF
    ".bmp",
    ".dib",  # Bitmap
    ".webp",  # WebP
    ".tiff",
    ".tif",  # TIFF
    ".svg",
    ".svgz",  # SVG
    ".ico",  # Ikony
    ".avif",  # AVIF (nowoczesny format)
    ".heic",
    ".heif",  # HEIC/HEIF (Apple)
)


def get_file_size_readable(size_bytes):
    """Konwertuje rozmiar pliku w bajtach na czytelny format."""
    logger.debug(f"Konwersja rozmiaru pliku: {size_bytes} bajtów")
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    result = f"{size_bytes:.2f} {size_name[i]}"
    logger.debug(f"Wynik konwersji: {result}")
    return result


def get_folder_stats(folder_path):
    """Zbiera podstawowe statystyki dotyczące folderu."""
    logger.info(f"Zbieranie statystyk dla folderu: {folder_path}")
    total_size_bytes = 0
    file_count = 0
    subdir_count = 0
    archive_count = 0

    try:
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.lower() != "index.json":
                try:
                    stat = entry.stat()
                    file_size = stat.st_size
                    file_count += 1
                    total_size_bytes += file_size
                    archive_count += 1
                    logger.debug(f"Znaleziono plik: {entry.name} ({file_size} bajtów)")
                except OSError as e:
                    logger.error(f"Błąd dostępu do pliku {entry.name}: {e}")
            elif entry.is_dir():
                subdir_count += 1
                logger.debug(f"Znaleziono podfolder: {entry.name}")
    except OSError as e:
        logger.error(f"Błąd podczas skanowania folderu {folder_path}: {e}")

    # Przygotuj podstawowe statystyki
    stats = {
        "path": os.path.abspath(folder_path),
        "total_size_bytes": total_size_bytes,
        "total_size_readable": get_file_size_readable(total_size_bytes),
        "file_count": file_count,
        "subdir_count": subdir_count,
        "archive_count": archive_count,
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    logger.info(f"Statystyki folderu {folder_path}: {stats}")
    return stats


def load_learning_data():
    """Wczytuje dane uczenia się z pliku JSON"""
    try:
        learning_file = "learning_data.json"
        if os.path.exists(learning_file):
            with open(learning_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Błąd wczytywania danych uczenia się: {e}")
        return []


def find_learned_match(archive_basename, learning_data):
    """Sprawdza czy istnieje nauczone dopasowanie dla danego pliku archiwum"""
    for match in learning_data:
        if match.get("archive_basename", "").lower() == archive_basename.lower():
            return match.get("image_basename", "")
    return None


def find_matching_preview_for_file(
    base_filename, image_files_in_folder, learning_data=None
):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    NOWA FUNKCJONALNOŚĆ: Najpierw sprawdza nauczone dopasowania!
    """
    logger.debug(f"🔍 Szukam podglądu dla pliku: {base_filename}")
    logger.debug(f"📝 Dostępne pliki obrazów: {[os.path.basename(f) for f in image_files_in_folder]}")

    if not base_filename:
        logger.debug("❌ Brak nazwy bazowej pliku")
        return None

    # PIERWSZEŃSTWO: Sprawdź nauczone dopasowania
    if learning_data:
        logger.debug(f"📚 Sprawdzam nauczone dopasowania dla: {base_filename}")
        learned_image = find_learned_match(base_filename, learning_data)
        if learned_image:
            logger.debug(f"🎓 Znaleziono nauczone dopasowanie: {learned_image}")
            # Szukaj dokładnego dopasowania nazwy z nauki
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)

                if img_ext.lower() in IMAGE_EXTENSIONS:
                    if img_base.lower() == learned_image.lower():
                        logger.info(
                            f"🎓 NAUCZONE dopasowanie: '{base_filename}' ↔ '{img_name}'"
                        )
                        return img_path

    # FALLBACK: Użyj standardowego algorytmu jeśli nie ma nauki
    logger.debug(f"🔍 Używam standardowego algorytmu dopasowania dla: {base_filename}")
    base_name = base_filename.lower().strip()

    # Twórz różne warianty nazwy bazowej
    name_variants = set()

    # Podstawowy wariant
    name_variants.add(base_name)

    # Zamiana podkreśleń na spacje i odwrotnie
    name_variants.add(base_name.replace("_", " "))
    name_variants.add(base_name.replace(" ", "_"))
    name_variants.add(base_name.replace("-", " "))
    name_variants.add(base_name.replace(" ", "-"))
    name_variants.add(base_name.replace("_", "-"))
    name_variants.add(base_name.replace("-", "_"))

    # Usuń wielokrotne spacje/podkreślenia
    cleaned_variants = set()
    for variant in name_variants:
        # Normalizuj wielokrotne separatory
        import re

        normalized = re.sub(r"[\s_-]+", " ", variant).strip()
        cleaned_variants.add(normalized)
        cleaned_variants.add(normalized.replace(" ", "_"))
        cleaned_variants.add(normalized.replace(" ", "-"))

    name_variants.update(cleaned_variants)
    logger.debug(f"📝 Wygenerowane warianty nazwy: {sorted(name_variants)}")

    # Dodaj warianty z typowymi sufiksami
    extended_variants = set(name_variants)
    for variant in name_variants:
        for separator in ["_", "-", " ", ""]:
            for suffix in ["001", "preview", "thumb", "1", "2", "3", "0"]:
                if separator or suffix.isdigit():
                    extended_variants.add(variant + separator + suffix)

    logger.debug(
        f"🔍 Szukam podglądu dla '{base_filename}' z {len(extended_variants)} wariantami"
    )

    for img_path in image_files_in_folder:
        img_name = os.path.basename(img_path)
        img_base, img_ext = os.path.splitext(img_name)

        # Sprawdź czy to obsługiwane rozszerzenie obrazu
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            logger.debug(f"⚠️ Pomijam nieobsługiwany format: {img_name}")
            continue

        img_base_clean = img_base.lower().strip()
        logger.debug(f"🖼️ Sprawdzam obraz: {img_name} (bazowa nazwa: {img_base_clean})")

        # Dokładne dopasowanie
        if img_base_clean in extended_variants:
            logger.debug(f"✅ Dokładne dopasowanie: '{img_name}' dla '{base_filename}'")
            return img_path

        # Sprawdzenie czy obraz zaczyna się od któregoś z wariantów
        for variant in name_variants:
            if len(variant) >= 3:  # Minimalna długość dla bezpiecznego dopasowania
                # Obraz zaczyna się od wariantu + separator/cyfra
                if (
                    img_base_clean.startswith(variant + " ")
                    or img_base_clean.startswith(variant + "_")
                    or img_base_clean.startswith(variant + "-")
                    or (
                        img_base_clean.startswith(variant)
                        and len(img_base_clean) > len(variant)
                        and img_base_clean[len(variant) :][0].isdigit()
                    )
                ):
                    logger.debug(
                        f"✅ Dopasowanie z prefiksem: '{img_name}' dla '{base_filename}' (wariant: '{variant}')"
                    )
                    return img_path

    logger.debug(f"❌ Nie znaleziono podglądu dla: '{base_filename}'")
    return None


def debug_name_matching(base_filename, image_files_in_folder):
    """
    Funkcja debugowa do sprawdzenia wszystkich możliwych dopasowań.
    Użyj do diagnozowania problemów z dopasowywaniem nazw.
    """
    print(f"\n🔍 DEBUG dla: '{base_filename}'")

    base_name = base_filename.lower().strip()

    # Twórz warianty tak samo jak w głównej funkcji
    name_variants = {base_name}
    name_variants.add(base_name.replace("_", " "))
    name_variants.add(base_name.replace(" ", "_"))
    name_variants.add(base_name.replace("-", " "))
    name_variants.add(base_name.replace(" ", "-"))

    print(f"📝 Warianty bazowe: {sorted(name_variants)}")

    for img_path in image_files_in_folder:
        img_name = os.path.basename(img_path)
        img_base, img_ext = os.path.splitext(img_name)

        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue

        img_base_clean = img_base.lower().strip()
        print(f"🖼️ Sprawdzam obraz: '{img_base_clean}'")

        # Test dokładnego dopasowania
        if img_base_clean in name_variants:
            print(f"   ✅ DOKŁADNE dopasowanie!")

        # Test dopasowania z prefiksem
        for variant in name_variants:
            if len(variant) >= 3:
                if (
                    img_base_clean.startswith(variant + " ")
                    or img_base_clean.startswith(variant + "_")
                    or img_base_clean.startswith(variant + "-")
                ):
                    print(f"   ✅ PREFIKS dopasowanie z wariantem: '{variant}'")
                elif (
                    img_base_clean.startswith(variant)
                    and len(img_base_clean) > len(variant)
                    and img_base_clean[len(variant) :][0].isdigit()
                ):
                    print(f"   ✅ PREFIKS+CYFRA dopasowanie z wariantem: '{variant}'")


def log_file_matching_debug(folder_path, progress_callback=None):
    """
    Funkcja debugowa do sprawdzenia dopasowywania plików.
    Użyj jej do diagnozowania problemów z dopasowywaniem.
    """
    logger.info(f"🔍 DEBUG: Analiza dopasowywania plików w: {folder_path}")

    try:
        all_files = []
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if entry.is_file():
                    all_files.append(entry.name)

        # Podziel pliki
        image_files = [
            f
            for f in all_files
            if any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)
        ]
        other_files = [
            f for f in all_files if f not in image_files and f.lower() != "index.json"
        ]

        logger.info(f"📁 Pliki obrazów ({len(image_files)}): {image_files}")
        logger.info(f"📄 Inne pliki ({len(other_files)}): {other_files}")

        # Sprawdź dopasowania
        matches_found = 0
        for other_file in other_files:
            base_name = os.path.splitext(other_file)[0]
            full_image_paths = [os.path.join(folder_path, img) for img in image_files]
            match = find_matching_preview_for_file(base_name, full_image_paths)

            if match:
                matches_found += 1
                logger.info(
                    f"✅ DOPASOWANIE: '{other_file}' ↔ '{os.path.basename(match)}'"
                )
                if progress_callback:
                    progress_callback(
                        f"Dopasowano: {other_file} ↔ {os.path.basename(match)}"
                    )
            else:
                logger.info(f"❌ BRAK: '{other_file}' (szukano dla '{base_name}')")
                if progress_callback:
                    progress_callback(f"Brak podglądu dla: {other_file}")

        logger.info(
            f"📊 PODSUMOWANIE: {matches_found}/{len(other_files)} plików ma podgląd"
        )

    except Exception as e:
        logger.error(f"Błąd podczas debugowania: {e}")


def process_folder(folder_path, progress_callback=None):
    """
    Przetwarza pojedynczy folder: zbiera informacje i generuje index.json.
    NOWA FUNKCJONALNOŚĆ: Używa danych uczenia się.
    """
    logger.info(f"🔄 Rozpoczynam przetwarzanie folderu: {folder_path}")

    if progress_callback:
        progress_callback(f"🔄 Przetwarzanie folderu: {folder_path}")

    # WCZYTAJ DANE UCZENIA SIĘ
    learning_data = load_learning_data()
    if learning_data:
        logger.info(f"📚 Wczytano {len(learning_data)} nauczonych dopasowań")
        if progress_callback:
            progress_callback(f"📚 Zastosowano {len(learning_data)} nauczonych dopasowań")

    # ULEPSZONE ZABEZPIECZENIE PRZED ZAWIESZENIEM
    try:
        if not os.path.exists(folder_path):
            msg = f"❌ Folder nie istnieje: {folder_path}"
            logger.error(msg)
            if progress_callback:
                progress_callback(msg)
            return

        if not os.access(folder_path, os.R_OK):
            msg = f"❌ Brak dostępu do folderu: {folder_path}"
            logger.error(msg)
            if progress_callback:
                progress_callback(msg)
            return
            
        # Sprawdź czy folder nie jest symbolicznym linkiem (może powodować zapętlenia)
        if os.path.islink(folder_path):
            msg = f"⚠️ Pomijam link symboliczny: {folder_path}"
            logger.warning(msg)
            if progress_callback:
                progress_callback(msg)
            return
            
    except Exception as e:
        msg = f"❌ Błąd dostępu do folderu {folder_path}: {e}"
        logger.error(msg)
        if progress_callback:
            progress_callback(msg)
        return

    index_data = {
        "folder_info": None,
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
    }

    all_items_in_dir = []
    subdirectories = []

    try:
        # UPROSZCZONY MECHANIZM SKANOWANIA BEZ TIMEOUT THREADING
        logger.info(f"📂 Rozpoczynam skanowanie zawartości: {folder_path}")
        start_time = time.time()
        
        # Użyj prostego os.listdir zamiast os.scandir dla lepszej stabilności
        try:
            items = os.listdir(folder_path)
            logger.debug(f"📊 Znaleziono {len(items)} elementów w {folder_path}")
            
            for item_name in items:
                current_time = time.time()
                
                # Bezpieczny timeout bez threading - przerwij po 30 sekundach
                if current_time - start_time > 30:
                    logger.warning(f"⏰ Przekroczono limit czasu w {folder_path}")
                    break
                
                try:
                    item_path = os.path.join(folder_path, item_name)
                    
                    # Sprawdź czy element rzeczywiście istnieje (może być usunięty podczas skanowania)
                    if not os.path.exists(item_path):
                        logger.debug(f"⚠️ Element nie istnieje już: {item_name}")
                        continue
                    
                    all_items_in_dir.append(item_name)
                    
                    if os.path.isdir(item_path):
                        # Dodatkowe sprawdzenie dla folderów
                        if not os.path.islink(item_path):  # Pomijaj linki symboliczne
                            subdirectories.append(item_path)
                            logger.debug(f"📁 Znaleziono podfolder: {item_path}")
                    else:
                        logger.debug(f"📄 Znaleziono plik: {item_name}")
                        
                    # Raportuj postęp co 100 elementów
                    if len(all_items_in_dir) % 100 == 0 and progress_callback:
                        progress_callback(f"📊 Przetworzono {len(all_items_in_dir)} elementów w {folder_path}")
                        
                except (OSError, PermissionError) as e:
                    logger.error(f"❌ Błąd dostępu do {item_name}: {e}")
                    continue
                    
        except (OSError, PermissionError) as e:
            logger.error(f"❌ Błąd listowania folderu {folder_path}: {e}")
            if progress_callback:
                progress_callback(f"❌ Błąd listowania folderu {folder_path}: {e}")
            return
            
        elapsed_time = time.time() - start_time
        logger.debug(f"⏱️ Skanowanie {folder_path} zajęło {elapsed_time:.2f} sekund")
        logger.debug(f"📊 Łącznie przetworzono {len(all_items_in_dir)} elementów")

    except Exception as e:
        logger.error(f"❌ Nieoczekiwany błąd w {folder_path}: {e}")
        if progress_callback:
            progress_callback(f"❌ Nieoczekiwany błąd w {folder_path}: {e}")
        return

    logger.info(f"📊 Znaleziono {len(all_items_in_dir)} elementów w {folder_path}")

    # Podziel pliki na obrazy i inne pliki
    logger.debug(f"🔍 Rozpoczynam podział plików w {folder_path}")
    logger.debug(f"📝 Lista wszystkich elementów: {all_items_in_dir}")

    image_filenames = [
        f
        for f in all_items_in_dir
        if os.path.isfile(os.path.join(folder_path, f))
        and any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)
    ]
    logger.debug(f"🖼️ Znalezione pliki obrazów: {image_filenames}")

    other_filenames = [
        f
        for f in all_items_in_dir
        if os.path.isfile(os.path.join(folder_path, f))
        and not any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)
        and f.lower() != "index.json"
    ]
    logger.debug(f"📄 Znalezione inne pliki: {other_filenames}")

    logger.info(f"🖼️ Znaleziono {len(image_filenames)} obrazów i {len(other_filenames)} innych plików")

    logger.debug(f"🔍 Tworzę pełne ścieżki do plików obrazów")
    full_path_image_files = [
        os.path.join(folder_path, img_name) for img_name in image_filenames
    ]
    logger.debug(f"📝 Pełne ścieżki do obrazów: {full_path_image_files}")
    found_previews_paths = set()

    logger.debug(f"🔄 Rozpoczynam przetwarzanie plików")
    for file_name in other_filenames:
        logger.debug(f"📄 Przetwarzam plik: {file_name}")
        file_path = os.path.join(folder_path, file_name)
        file_basename, _ = os.path.splitext(file_name)
        logger.debug(f"📝 Nazwa bazowa pliku: {file_basename}")

        try:
            file_size_bytes = os.path.getsize(file_path)
            logger.debug(f"📄 Przetwarzanie pliku: {file_name} ({get_file_size_readable(file_size_bytes)})")
        except OSError as e:
            logger.error(f"❌ Błąd odczytu rozmiaru {file_name}: {e}")
            file_size_bytes = 0

        file_info = {
            "name": file_name,
            "path_absolute": os.path.abspath(file_path),
            "size_bytes": file_size_bytes,
            "size_readable": get_file_size_readable(file_size_bytes),
        }

        # ULEPSZONE dopasowywanie z NAUKĄ
        logger.debug(f"🔍 Szukam podglądu dla: {file_name}")
        preview_file_path = find_matching_preview_for_file(
            file_basename, full_path_image_files, learning_data
        )

        if preview_file_path:
            file_info["preview_found"] = True
            file_info["preview_name"] = os.path.basename(preview_file_path)
            file_info["preview_path_absolute"] = os.path.abspath(preview_file_path)
            index_data["files_with_previews"].append(file_info)
            found_previews_paths.add(preview_file_path)
            logger.info(
                f"✅ Dopasowano: '{file_name}' ↔ '{os.path.basename(preview_file_path)}'"
            )
        else:
            file_info["preview_found"] = False
            index_data["files_without_previews"].append(file_info)
            logger.debug(f"❌ Brak podglądu dla: '{file_name}'")

    logger.debug(f"🔄 Rozpoczynam przetwarzanie niesparowanych obrazów")
    # Dodaj obrazy, które nie zostały sparowane jako podglądy
    for img_name in image_filenames:
        logger.debug(f"🖼️ Sprawdzam obraz: {img_name}")
        img_path_full = os.path.join(folder_path, img_name)
        if img_path_full not in found_previews_paths:
            try:
                img_size_bytes = os.path.getsize(img_path_full)
                logger.debug(f"🖼️ Dodaję niesparowany obraz: {img_name} ({get_file_size_readable(img_size_bytes)})")
            except OSError as e:
                logger.error(f"❌ Błąd odczytu rozmiaru obrazu {img_name}: {e}")
                img_size_bytes = 0

            index_data["other_images"].append(
                {
                    "name": img_name,
                    "path_absolute": os.path.abspath(img_path_full),
                    "size_bytes": img_size_bytes,
                    "size_readable": get_file_size_readable(img_size_bytes),
                }
            )

    # Aktualizuj statystyki folderu na końcu
    index_data["folder_info"] = get_folder_stats(folder_path)

    # Zapisz index.json
    index_json_path = os.path.join(folder_path, "index.json")
    try:
        with open(index_json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4, ensure_ascii=False)
        logger.info(f"💾 Zapisano plik index.json: {index_json_path}")
        if progress_callback:
            progress_callback(f"💾 Zapisano: {index_json_path}")
    except IOError as e:
        msg = f"❌ Błąd zapisu {index_json_path}: {e}"
        logger.error(msg)
        if progress_callback:
            progress_callback(msg)

    # Przetwarzaj podfoldery
    for subdir in subdirectories:
        logger.info(f"📁 Przetwarzanie podfolderu: {subdir}")
        process_folder(subdir, progress_callback)


def process_folder_with_retry(folder_path, max_retries=3, progress_callback=None):
    """Przetwarza folder z mechanizmem ponownych prób w przypadku błędów dostępu."""
    logger.info(f"Rozpoczęcie przetwarzania folderu z mechanizmem retry: {folder_path}")

    for attempt in range(max_retries):
        try:
            return process_folder(folder_path, progress_callback)
        except PermissionError as e:
            logger.warning(f"Próba {attempt + 1}/{max_retries} nie powiodła się: {e}")
            if attempt == max_retries - 1:
                msg = f"Nie udało się uzyskać dostępu do folderu {folder_path} po {max_retries} próbach"
                logger.error(msg)
                if progress_callback:
                    progress_callback(msg)
                raise
            if progress_callback:
                progress_callback(
                    f"Próba {attempt + 1}/{max_retries} nie powiodła się, ponawiam..."
                )
            time.sleep(0.5)


def start_scanning(root_folder_path, progress_callback=None):
    """Rozpoczyna skanowanie od podanego folderu głównego."""
    logger.info(f"🚀 Rozpoczynam skanowanie od folderu: {root_folder_path}")

    if not os.path.isdir(root_folder_path):
        msg = f"❌ Błąd: Ścieżka {root_folder_path} nie jest folderem lub nie istnieje."
        logger.error(msg)
        if progress_callback:
            progress_callback(msg)
        return

    try:
        # Sprawdź uprawnienia do folderu
        if not os.access(root_folder_path, os.R_OK):
            msg = f"❌ Brak uprawnień do odczytu folderu: {root_folder_path}"
            logger.error(msg)
            if progress_callback:
                progress_callback(msg)
            return

        # Sprawdź czy folder nie jest pusty
        if not os.listdir(root_folder_path):
            msg = f"⚠️ Folder jest pusty: {root_folder_path}"
            logger.warning(msg)
            if progress_callback:
                progress_callback(msg)

        # Dodaj informację o rozpoczęciu skanowania
        if progress_callback:
            progress_callback(f"🚀 Rozpoczynam skanowanie: {root_folder_path}")

        # Uruchom skanowanie z mechanizmem retry
        process_folder_with_retry(root_folder_path, progress_callback=progress_callback)

        logger.info("✅ Skanowanie zakończone pomyślnie")
        if progress_callback:
            progress_callback("✅ Skanowanie zakończone.")

    except Exception as e:
        msg = f"❌ Krytyczny błąd podczas skanowania: {e}"
        logger.error(msg)
        if progress_callback:
            progress_callback(msg)
        raise


def quick_rescan_folder(folder_path, progress_callback=None):
    """Szybkie ponowne skanowanie folderu po modyfikacji plików"""
    logger.info(f"Szybkie ponowne skanowanie: {folder_path}")

    if progress_callback:
        progress_callback(f"Ponowne skanowanie: {folder_path}")

    # Wykorzystaj istniejącą funkcję process_folder
    return process_folder(folder_path, progress_callback)


if __name__ == "__main__":
    # Testowanie logiki
    test_dir = "/tmp/test_scan_py_no_archive"  # Zmień na istniejący folder testowy
    if os.path.exists(test_dir):  # Usuń stary, jeśli istnieje, dla czystego testu
        import shutil

        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(os.path.join(test_dir, "subfolder"), exist_ok=True)

    # Przykładowe pliki
    with open(os.path.join(test_dir, "dokument1.txt"), "w") as f:
        f.write("text content1")
    with open(os.path.join(test_dir, "dokument1.jpg"), "w") as f:
        f.write("jpeg_content1")  # Podgląd dla dokument1.txt
    with open(os.path.join(test_dir, "prezentacja.pdf"), "w") as f:
        f.write("pdf_content2")
    with open(os.path.join(test_dir, "prezentacja_001.png"), "w") as f:
        f.write("png_content2")  # Podgląd dla prezentacja.pdf
    with open(os.path.join(test_dir, "plik_bez_podgladu.docx"), "w") as f:
        f.write("docx_content3")
    with open(os.path.join(test_dir, "obrazek_luzem.gif"), "w") as f:
        f.write("gif content")  # Obraz niebędący podglądem
    with open(os.path.join(test_dir, "subfolder", "inny_plik.md"), "w") as f:
        f.write("sub markdown content")
    with open(os.path.join(test_dir, "subfolder", "inny_plik_0.jpg"), "w") as f:
        f.write("sub jpeg content")  # Podgląd dla inny_plik.md
    print(f"Utworzono testowy folder i pliki w: {test_dir}")

    def simple_progress_logger(message):
        print(message)

    print(f"Rozpoczynanie skanowania w {test_dir}...")
    start_scanning(test_dir, simple_progress_logger)
    print("Testowanie zakończone. Sprawdź pliki index.json.")
