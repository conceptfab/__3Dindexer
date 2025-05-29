# scanner_logic.py
import json
import logging
import os
import time
import re # Przeniesiony import re na górę
from datetime import datetime
from pathlib import Path

import config_manager # Założenie: ten plik istnieje i działa poprawnie

# Konfiguracja loggera
def setup_logger(log_dir="logs", enable_file_logging=None):
    """Konfiguruje i zwraca logger z opcjonalnym zapisem do pliku."""
    if enable_file_logging is None:
        enable_file_logging = config_manager.get_config_value(
            "enable_file_logging", False
        )

    logger = logging.getLogger("scanner")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if enable_file_logging:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        log_file = log_path / f"scanner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

logger = setup_logger()

IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".apng",
    ".gif",
    ".bmp", ".dib",
    ".webp",
    ".tiff", ".tif",
    ".svg", ".svgz",
    ".ico",
    ".avif",
    ".heic", ".heif",
)

def get_file_size_readable(size_bytes):
    """Konwertuje rozmiar pliku w bajtach na czytelny format."""
    # logger.debug(f"Konwersja rozmiaru pliku: {size_bytes} bajtów") # Może być zbyt gadatliwe
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    # Ensure size_bytes is float for division if it's large
    size_bytes_float = float(size_bytes)
    while size_bytes_float >= 1024 and i < len(size_name) - 1:
        size_bytes_float /= 1024.0
        i += 1
    result = f"{size_bytes_float:.2f} {size_name[i]}"
    # logger.debug(f"Wynik konwersji: {result}")
    return result

def get_folder_stats(folder_path):
    """
    Zbiera podstawowe statystyki dotyczące folderu.
    UWAGA: Ta funkcja wykonuje oddzielne skanowanie. W głównym przepływie
    process_folder statystyki są zbierane bardziej efektywnie.
    Może być użyteczna do szybkiego, niezależnego sprawdzenia folderu.
    """
    logger.info(f"Zbieranie statystyk (get_folder_stats) dla folderu: {folder_path}")
    total_size_bytes = 0
    file_count = 0
    subdir_count = 0
    # archive_count jest tu interpretowane jako file_count
    # (zgodnie z wcześniejszym użyciem w tej funkcji)
    items_processed_for_stats = 0

    try:
        for entry in os.scandir(folder_path):
            items_processed_for_stats += 1
            if entry.is_file(follow_symlinks=False) and entry.name.lower() != "index.json":
                try:
                    stat_info = entry.stat(follow_symlinks=False)
                    file_size = stat_info.st_size
                    file_count += 1
                    total_size_bytes += file_size
                    logger.debug(f"Stat: Znaleziono plik: {entry.name} ({file_size} bajtów)")
                except OSError as e:
                    logger.error(f"Stat: Błąd dostępu do pliku {entry.name}: {e}")
            elif entry.is_dir(follow_symlinks=False):
                subdir_count += 1
                logger.debug(f"Stat: Znaleziono podfolder: {entry.name}")
    except OSError as e:
        logger.error(f"Stat: Błąd podczas skanowania folderu {folder_path}: {e}")

    stats = {
        "path": os.path.abspath(folder_path),
        "total_size_bytes": total_size_bytes,
        "total_size_readable": get_file_size_readable(total_size_bytes),
        "file_count": file_count,
        "subdir_count": subdir_count,
        "archive_count": file_count, # Zgodnie z logiką z oryginalnego kodu
        "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    logger.info(f"Statystyki folderu (get_folder_stats) {folder_path}: {stats}")
    return stats


def load_learning_data():
    """Wczytuje dane uczenia się z pliku JSON"""
    try:
        learning_file = config_manager.get_config_value("learning_data_file", "learning_data.json")
        if os.path.exists(learning_file):
            with open(learning_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Wczytano {len(data)} wpisów z danych uczenia się ({learning_file}).")
                return data
        logger.info(f"Plik danych uczenia się ({learning_file}) nie istnieje.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Błąd dekodowania JSON w pliku danych uczenia się: {e}")
        return []
    except Exception as e:
        logger.error(f"Błąd wczytywania danych uczenia się: {e}", exc_info=True)
        return []

def find_learned_match(archive_basename, learning_data):
    """Sprawdza czy istnieje nauczone dopasowanie dla danego pliku archiwum"""
    # archive_basename to nazwa pliku BEZ rozszerzenia
    archive_basename_lower = archive_basename.lower()
    for match_entry in learning_data:
        # Sprawdzamy czy 'archive_basename' istnieje i czy pasuje (ignorując wielkość liter)
        if match_entry.get("archive_basename", "").lower() == archive_basename_lower:
            # Zwracamy 'image_basename', czyli nazwę pliku obrazu BEZ rozszerzenia
            return match_entry.get("image_basename", "")
    return None


def find_matching_preview_for_file(
    base_filename, image_files_in_folder, learning_data=None
):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    base_filename: Nazwa pliku (bez rozszerzenia), dla którego szukamy podglądu.
    image_files_in_folder: Lista PEŁNYCH ŚCIEŻEK do plików obrazów w folderze.
    learning_data: Wczytane dane z learning_data.json.
    """
    logger.debug(f"🔍 Rozpoczynam szukanie podglądu dla pliku bazowego: '{base_filename}'")
    logger.debug(f"🖼️ Dostępne pliki obrazów (tylko nazwy): {[os.path.basename(f) for f in image_files_in_folder]}")

    if not base_filename:
        logger.warning("❌ Przekazano pustą nazwę bazową pliku do find_matching_preview_for_file.")
        return None

    # 1. PIERWSZEŃSTWO: Sprawdź nauczone dopasowania
    if learning_data:
        logger.debug(f"📚 Sprawdzam nauczone dopasowania dla: '{base_filename}'")
        learned_image_basename = find_learned_match(base_filename, learning_data) # Oczekuje nazwy pliku bez rozszerzenia

        if learned_image_basename:
            logger.debug(f"🎓 Znaleziono nauczoną bazową nazwę obrazu: '{learned_image_basename}' dla '{base_filename}'")
            learned_image_basename_lower = learned_image_basename.lower()
            for img_full_path in image_files_in_folder:
                current_img_name = os.path.basename(img_full_path)
                current_img_base, current_img_ext = os.path.splitext(current_img_name)
                if current_img_ext.lower() in IMAGE_EXTENSIONS:
                    if current_img_base.lower() == learned_image_basename_lower:
                        logger.info(f"🎓 ZNALEZIONO NAUCZONE DOPASOWANIE: '{base_filename}' (plik) ↔ '{current_img_name}' (obraz)")
                        return img_full_path
            logger.debug(f"🎓 Nauczony obraz '{learned_image_basename}' nie został fizycznie znaleziony wśród dostępnych plików obrazów w folderze.")
        else:
            logger.debug(f"📚 Brak nauczonego dopasowania dla '{base_filename}'.")

    # 2. FALLBACK: Standardowy algorytm dopasowania
    logger.debug(f"⚙️ Używam standardowego algorytmu dopasowania dla: '{base_filename}'")
    # base_filename to już nazwa bez rozszerzenia
    normalized_base_filename = base_filename.lower().strip()

    name_variants = set()
    name_variants.add(normalized_base_filename)
    # Proste zamiany separatorów
    name_variants.add(normalized_base_filename.replace("_", " "))
    name_variants.add(normalized_base_filename.replace(" ", "_"))
    name_variants.add(normalized_base_filename.replace("-", " "))
    name_variants.add(normalized_base_filename.replace(" ", "-"))
    name_variants.add(normalized_base_filename.replace("_", "-"))
    name_variants.add(normalized_base_filename.replace("-", "_"))

    # Normalizacja wielokrotnych separatorów i warianty z tym
    cleaned_variants_after_re = set()
    for variant in list(name_variants): # iterujemy po kopii, bo name_variants może być modyfikowane
        normalized_by_re = re.sub(r"[\s_-]+", " ", variant).strip()
        cleaned_variants_after_re.add(normalized_by_re)
        cleaned_variants_after_re.add(normalized_by_re.replace(" ", "_"))
        cleaned_variants_after_re.add(normalized_by_re.replace(" ", "-"))
    name_variants.update(cleaned_variants_after_re)
    logger.debug(f"📝 Warianty podstawowe nazwy dla '{base_filename}': {sorted(list(name_variants))}")

    # Dodaj warianty z typowymi sufiksami
    extended_variants_with_suffixes = set(name_variants) # Kopiujemy podstawowe
    common_suffixes = ["001", "preview", "thumb", "1", "2", "3", "0", "cover", "poster", "art", "fanart", "img", "image", "logo"]
    for variant in name_variants: # Iterujemy po podstawowych wariantach
        for separator in ["_", "-", " ", ""]: # Pusty separator dla bezpośredniego dołączenia
            for suffix in common_suffixes:
                # Unikaj dodawania np. " " na końcu jeśli separator to " " i variant już się tak kończy
                # Lub jeśli suffix jest numeryczny i variant już kończy się cyfrą (bez separatora)
                candidate = variant + separator + suffix
                if separator or not (suffix.isdigit() and variant and variant[-1].isdigit()):
                     extended_variants_with_suffixes.add(candidate.strip()) # strip na wypadek separatora spacji na końcu

    logger.debug(f" erweitert Warianty rozszerzone (z sufiksami) dla '{base_filename}' (liczba: {len(extended_variants_with_suffixes)}). Przykłady: {list(extended_variants_with_suffixes)[:15]}")
    
    # Sprawdzanie dopasowań
    # Najpierw szukamy dokładnych dopasowań do rozszerzonych wariantów (nazwa_obrazu_bez_rozszerzenia)
    for img_full_path in image_files_in_folder:
        img_name_with_ext = os.path.basename(img_full_path)
        img_base_name, img_ext = os.path.splitext(img_name_with_ext)
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue # Pomiń jeśli to nie jest obsługiwany obraz

        img_base_name_lower_stripped = img_base_name.lower().strip()
        if img_base_name_lower_stripped in extended_variants_with_suffixes:
            logger.info(f"✅ Dopasowanie (wariant rozszerzony): '{base_filename}' (plik) ↔ '{img_name_with_ext}' (obraz) przez wariant '{img_base_name_lower_stripped}'")
            return img_full_path

    # Następnie sprawdzamy, czy nazwa obrazu zaczyna się od jednego z *podstawowych* wariantów nazwy pliku
    # To jest bardziej ogólne dopasowanie.
    for img_full_path in image_files_in_folder:
        img_name_with_ext = os.path.basename(img_full_path)
        img_base_name, img_ext = os.path.splitext(img_name_with_ext)
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue

        img_base_name_lower_stripped = img_base_name.lower().strip()
        for variant in name_variants: # Iterujemy po podstawowych wariantach `base_filename`
            if len(variant) >= 3 and img_base_name_lower_stripped.startswith(variant):
                remaining_part = img_base_name_lower_stripped[len(variant):]
                # Akceptujemy, jeśli pozostała część jest pusta (dokładne dopasowanie do wariantu podstawowego),
                # lub zaczyna się od typowego separatora, cyfry, lub znanego słowa kluczowego.
                if not remaining_part: # Już powinno być złapane przez `extended_variants_with_suffixes` jeśli `variant` był tam
                    logger.info(f"✅ Dopasowanie (wariant podstawowy - dokładny): '{base_filename}' (plik) ↔ '{img_name_with_ext}' (obraz) przez wariant '{variant}'")
                    return img_full_path
                
                if remaining_part[0] in [' ', '_', '-'] or remaining_part[0].isdigit():
                    logger.info(f"✅ Dopasowanie (prefiks - wariant podstawowy + separator/cyfra): '{base_filename}' (plik) ↔ '{img_name_with_ext}' (obraz) przez wariant '{variant}'")
                    return img_full_path
                
                for suffix_keyword in common_suffixes: # Sprawdźmy także typowe słowa kluczowe w pozostałej części
                    # np. plik "movie", obraz "movie_poster.jpg" lub "movieposter.jpg"
                    if remaining_part.lower().startswith(suffix_keyword) or \
                       remaining_part.lower().startswith(f"_{suffix_keyword}") or \
                       remaining_part.lower().startswith(f"-{suffix_keyword}") or \
                       remaining_part.lower().startswith(f" {suffix_keyword}"):
                        logger.info(f"✅ Dopasowanie (prefiks - wariant podstawowy + słowo kluczowe): '{base_filename}' (plik) ↔ '{img_name_with_ext}' (obraz) przez wariant '{variant}', słowo kluczowe '{suffix_keyword}'")
                        return img_full_path

    logger.debug(f"❌ Nie znaleziono standardowego podglądu dla: '{base_filename}'")
    return None


def debug_name_matching(base_filename, image_files_in_folder_paths):
    """
    Funkcja debugowa do sprawdzenia wszystkich możliwych dopasowań.
    Użyj do diagnozowania problemów z dopasowywaniem nazw.
    `image_files_in_folder_paths` to lista pełnych ścieżek.
    """
    print(f"\n--- DEBUG NAME MATCHING dla: '{base_filename}' ---")

    # Replikacja logiki generowania wariantów z find_matching_preview_for_file
    normalized_base_filename = base_filename.lower().strip()
    name_variants = set()
    name_variants.add(normalized_base_filename)
    name_variants.add(normalized_base_filename.replace("_", " "))
    # ... (reszta logiki generowania name_variants i extended_variants_with_suffixes jak w find_matching_preview_for_file)
    # Dla uproszczenia tego przykładu, skopiuję tylko podstawową część, ale powinna być pełna.
    temp_variants = set([normalized_base_filename, normalized_base_filename.replace("_", " "), normalized_base_filename.replace(" ", "_")])
    print(f"📝 Podstawowe warianty testowe dla '{base_filename}': {sorted(list(temp_variants))}")
    # Tu powinna być pełna logika extended_variants_with_suffixes

    image_filenames = [os.path.basename(p) for p in image_files_in_folder_paths]
    print(f"🖼️ Dostępne obrazy (nazwy): {image_filenames}")

    # Testowanie z find_matching_preview_for_file
    # Należy załadować learning_data, jeśli ma być testowane
    # learning_data_for_debug = load_learning_data()
    # match = find_matching_preview_for_file(base_filename, image_files_in_folder_paths, learning_data_for_debug)

    # Uproszczone testowanie (bezpośrednie)
    for img_path in image_files_in_folder_paths:
        img_name_with_ext = os.path.basename(img_path)
        img_base_name, img_ext = os.path.splitext(img_name_with_ext)

        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue

        img_base_lower_stripped = img_base_name.lower().strip()
        print(f"  🔎 Sprawdzam obraz: '{img_name_with_ext}' (baza: '{img_base_lower_stripped}')")

        # Tutaj można by dodać logikę sprawdzania dopasowania z debug_name_matching
        # np. czy img_base_lower_stripped jest w extended_variants_with_suffixes
        # lub czy img_base_lower_stripped.startswith(variant) itd.
        # Dla zwięzłości pomijam pełną reimplementację logiki dopasowania tutaj.
        # Najlepiej byłoby wywołać find_matching_preview_for_file i przeanalizować jego logi DEBUG.

    print(f"--- KONIEC DEBUG NAME MATCHING dla: '{base_filename}' ---")


def log_file_matching_debug(folder_path, progress_callback=None):
    """
    Funkcja debugowa do sprawdzenia dopasowywania plików.
    Użyj jej do diagnozowania problemów z dopasowywaniem.
    """
    logger.info(f"🔍 DEBUG MATCHING: Analiza dopasowywania plików w: {folder_path}")
    if progress_callback: progress_callback(f"🔍 Rozpoczynam debugowanie dopasowań w: {folder_path}")

    all_files_in_dir = []
    try:
        logger.debug(f"Debug Matching: Skanuję {folder_path} dla plików...")
        for entry in os.scandir(folder_path):
            if entry.is_file(follow_symlinks=False):
                all_files_in_dir.append(entry.name)
        logger.debug(f"Debug Matching: Znaleziono {len(all_files_in_dir)} plików: {all_files_in_dir}")
    except OSError as e:
        logger.error(f"Debug Matching: Błąd listowania plików w {folder_path}: {e}")
        if progress_callback: progress_callback(f"Debug Matching: Błąd listowania {folder_path}: {e}")
        return

    image_filenames = [f for f in all_files_in_dir if any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)]
    other_filenames = [f for f in all_files_in_dir if f not in image_filenames and f.lower() != "index.json"]

    logger.info(f"Debug Matching: Pliki obrazów ({len(image_filenames)}): {image_filenames}")
    logger.info(f"Debug Matching: Inne pliki ({len(other_filenames)}): {other_filenames}")

    full_path_image_files = [os.path.join(folder_path, img_name) for img_name in image_filenames]
    learning_data = load_learning_data() # Załaduj dane uczenia się do testu

    matches_found = 0
    for other_file_name in other_filenames:
        base_name_of_other_file, _ = os.path.splitext(other_file_name)
        
        # Włącz szczegółowe logowanie dla tej konkretnej operacji
        # Można tymczasowo podnieść poziom loggera find_matching_preview_for_file, jeśli jest oddzielny,
        # lub po prostu polegać na globalnym poziomie DEBUG.
        
        matched_preview_path = find_matching_preview_for_file(base_name_of_other_file, full_path_image_files, learning_data)

        if matched_preview_path:
            matches_found += 1
            logger.info(f"Debug Matching: ✅ DOPASOWANIE: '{other_file_name}' ↔ '{os.path.basename(matched_preview_path)}'")
            if progress_callback: progress_callback(f"Debug Dopasowano: {other_file_name} ↔ {os.path.basename(matched_preview_path)}")
        else:
            logger.info(f"Debug Matching: ❌ BRAK DOPASOWANIA: '{other_file_name}' (szukano dla bazy '{base_name_of_other_file}')")
            if progress_callback: progress_callback(f"Debug Brak podglądu dla: {other_file_name}")
            # Dodatkowe wywołanie debug_name_matching dla nieudanych przypadków
            debug_name_matching(base_name_of_other_file, full_path_image_files)


    logger.info(f"Debug Matching: 📊 PODSUMOWANIE: {matches_found}/{len(other_filenames)} innych plików ma znaleziony podgląd.")
    if progress_callback: progress_callback(f"🔍 Zakończono debugowanie dopasowań w: {folder_path}")


def process_folder(folder_path, progress_callback=None):
    logger.info(f"🔄 Rozpoczynam przetwarzanie folderu: {folder_path}")
    if progress_callback:
        progress_callback(f"🔄 Przetwarzanie folderu: {folder_path}")

    learning_data = load_learning_data()

    # --- Sprawdzenia folderu ---
    try:
        logger.debug(f"Sprawdzanie istnienia: {folder_path}")
        if not os.path.exists(folder_path):
            msg = f"❌ Folder nie istnieje: {folder_path}"
            logger.error(msg)
            if progress_callback: progress_callback(msg)
            return
        if not os.access(folder_path, os.R_OK):
            msg = f"❌ Brak uprawnień do odczytu folderu: {folder_path}"
            logger.error(msg)
            if progress_callback: progress_callback(msg)
            return
        if os.path.islink(folder_path):
            msg = f"⚠️ Pomijam przetwarzanie, folder jest linkiem symbolicznym: {folder_path}"
            logger.warning(msg)
            if progress_callback: progress_callback(msg)
            return
    except OSError as e:
        msg = f"❌ Błąd OSError podczas wstępnych sprawdzeń folderu {folder_path}: {e}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)
        return
    except Exception as e:
        msg = f"❌ Nieoczekiwany błąd podczas wstępnych sprawdzeń folderu {folder_path}: {e}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)
        return

    # --- Wczytaj lub utwórz index.json ---
    index_json_path = os.path.join(folder_path, "index.json")
    if os.path.exists(index_json_path):
        try:
            with open(index_json_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            logger.info(f"📖 Załadowano istniejący index.json: {index_json_path}")
        except Exception as e:
            logger.error(f"❌ Błąd odczytu index.json ({index_json_path}): {e}")
            # Jeśli nie da się odczytać, utwórz od nowa
            index_data = {
                "folder_info": {
                    "path": os.path.abspath(folder_path),
                    "total_size_bytes": 0,
                    "file_count": 0,
                    "subdir_count": 0,
                    "archive_count": 0,
                    "scan_date": None
                },
                "files_with_previews": [],
                "files_without_previews": [],
                "other_images": [],
            }
    else:
        index_data = {
            "folder_info": {
                "path": os.path.abspath(folder_path),
                "total_size_bytes": 0,
                "file_count": 0,
                "subdir_count": 0,
                "archive_count": 0,
                "scan_date": None
            },
            "files_with_previews": [],
            "files_without_previews": [],
            "other_images": [],
        }
        logger.info(f"📝 Tworzę nowy index.json: {index_json_path}")

    # Listy do przechowywania szczegółów o plikach przed dopasowaniem
    # Każdy element to krotka: (name, full_path, size_bytes)
    image_file_details = [] 
    other_file_details = [] # Dla plików niebędących obrazami
    subdirectories_to_scan_recursively = []

    # --- Skanowanie zawartości folderu za pomocą os.scandir ---
    logger.info(f"📂 Rozpoczynam skanowanie zawartości (os.scandir) dla: {folder_path}")
    scan_start_time = time.time()
    processed_item_count_in_scandir = 0
    SCAN_TIMEOUT_SECONDS = int(config_manager.get_config_value("scan_timeout_per_folder", "120")) # Sekundy

    try:
        logger.debug(f"Wywołuję os.scandir({folder_path})")
        # os.scandir jest iteratorem; błędy mogą wystąpić przy samym wywołaniu lub podczas iteracji
        with os.scandir(folder_path) as scandir_iterator:
            logger.debug(f"Pomyślnie utworzono iterator os.scandir dla {folder_path}")
            for entry in scandir_iterator:
                if time.time() - scan_start_time > SCAN_TIMEOUT_SECONDS:
                    logger.warning(f"⏰ Przekroczono limit czasu skanowania ({SCAN_TIMEOUT_SECONDS}s) w folderze {folder_path} po {processed_item_count_in_scandir} elementach.")
                    if progress_callback: progress_callback(f"⏰ Timeout skanowania w {folder_path}")
                    break # Przerwij pętlę, folder zostanie przetworzony częściowo
                
                processed_item_count_in_scandir += 1
                if processed_item_count_in_scandir % 200 == 0 and progress_callback: # Rzadsze raportowanie
                    progress_callback(f"📊 Przetworzono {processed_item_count_in_scandir} elementów w {folder_path}...")

                try:
                    entry_name = entry.name
                    entry_path = entry.path # Pełna ścieżka

                    if entry_name.lower() == "index.json":
                        logger.debug(f"Pominięto plik 'index.json': {entry_path}")
                        continue

                    # Ważne: follow_symlinks=False dla is_file/is_dir, aby uniknąć problemów z zepsutymi linkami
                    # lub niespodziewanego śledzenia linków do plików/folderów poza skanowanym obszarem.
                    if entry.is_file(follow_symlinks=False):
                        file_size_bytes = 0
                        try:
                            # entry.stat() może być szybsze, bo entry już jest "świadome" pliku
                            stat_result = entry.stat(follow_symlinks=False) 
                            file_size_bytes = stat_result.st_size
                        except OSError as e_stat:
                            logger.error(f"Błąd odczytu statystyk dla pliku {entry_path}: {e_stat}")
                            # Plik zostanie dodany z rozmiarem 0
                        
                        index_data["folder_info"]["total_size_bytes"] += file_size_bytes
                        index_data["folder_info"]["file_count"] += 1
                        index_data["folder_info"]["archive_count"] += 1 # Utrzymanie logiki

                        is_image = any(entry_name.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)
                        if is_image:
                            image_file_details.append((entry_name, entry_path, file_size_bytes))
                        else: # Plik niebędący obrazem
                            other_file_details.append((entry_name, entry_path, file_size_bytes))

                    elif entry.is_dir(follow_symlinks=False):
                        index_data["folder_info"]["subdir_count"] += 1
                        # Sprawdzamy, czy sam katalog (DirEntry) nie jest linkiem symbolicznym
                        if not entry.is_symlink(): 
                            subdirectories_to_scan_recursively.append(entry_path)
                        else:
                            logger.debug(f"Pominięto rekurencyjne skanowanie linku symbolicznego do katalogu: {entry_path}")
                    else: # Ani plik, ani katalog (np. link symboliczny do nieistniejącego pliku, urządzenie specjalne)
                        logger.debug(f"Pominięto element specjalny (nie plik/katalog lub zepsuty link): {entry_path}")

                except OSError as e_entry: # Błędy dla pojedynczego entry (np. permission denied na stat)
                    logger.error(f"Błąd OSError podczas przetwarzania elementu '{getattr(entry, 'name', 'NieznanyElement')}' w {folder_path}: {e_entry}", exc_info=False) # exc_info=False by nie spamować logów
                    if progress_callback: progress_callback(f"Błąd elementu w {folder_path}: {getattr(entry, 'name', 'NieznanyElement')}")
                    # Kontynuuj z następnym elementem
            
        logger.debug(f"Zakończono pętlę os.scandir dla {folder_path}. Przetworzono {processed_item_count_in_scandir} elementów.")

    except PermissionError as e_perm_scandir:
        logger.error(f"❌ Brak uprawnień (PermissionError) do listowania folderu (os.scandir) {folder_path}: {e_perm_scandir}", exc_info=False)
        if progress_callback: progress_callback(f"❌ Brak uprawnień do listowania {folder_path}")
        return # Przerwij przetwarzanie tego folderu
    except OSError as e_os_scandir: # Inne błędy systemowe przy os.scandir
        logger.error(f"❌ Błąd OSError podczas listowania (os.scandir) folderu {folder_path}: {e_os_scandir}", exc_info=True)
        if progress_callback: progress_callback(f"❌ Błąd listowania folderu {folder_path}: {e_os_scandir}")
        return 
    except Exception as e_unexpected_scan: # Inne, nieprzewidziane błędy
        logger.error(f"❌ Nieoczekiwany błąd podczas skanowania (os.scandir) folderu {folder_path}: {e_unexpected_scan}", exc_info=True)
        if progress_callback: progress_callback(f"❌ Nieoczekiwany błąd w {folder_path}: {e_unexpected_scan}")
        return

    scan_duration = time.time() - scan_start_time
    logger.info(f"⏱️ Skanowanie {folder_path} (os.scandir) i zbieranie danych o plikach zajęło {scan_duration:.2f}s.")
    logger.info(f"📊 W {folder_path}: {len(other_file_details)} innych plików, {len(image_file_details)} obrazów, {len(subdirectories_to_scan_recursively)} podfolderów.")

    # --- Dopasowywanie podglądów ---
    # Przygotuj listę pełnych ścieżek obrazów dla funkcji dopasowującej
    full_paths_of_images_in_folder = [details[1] for details in image_file_details]
    # Zbiór pełnych ścieżek obrazów, które zostały użyte jako podglądy
    used_preview_image_paths = set() 

    logger.debug(f"Rozpoczynam dopasowywanie podglądów dla {len(other_file_details)} plików niebędących obrazami.")
    for file_name, file_path, file_size_bytes in other_file_details:
        file_basename_no_ext, _ = os.path.splitext(file_name)
        
        file_info_dict = {
            "name": file_name,
            "path_absolute": os.path.abspath(file_path), # os.path.abspath dla pewności
            "size_bytes": file_size_bytes,
            "size_readable": get_file_size_readable(file_size_bytes),
        }
        
        # Wywołanie funkcji dopasowującej
        matched_preview_path = find_matching_preview_for_file(
            file_basename_no_ext, 
            full_paths_of_images_in_folder, 
            learning_data
        )

        if matched_preview_path:
            file_info_dict["preview_found"] = True
            file_info_dict["preview_name"] = os.path.basename(matched_preview_path)
            file_info_dict["preview_path_absolute"] = os.path.abspath(matched_preview_path)
            index_data["files_with_previews"].append(file_info_dict)
            used_preview_image_paths.add(matched_preview_path) # Dodaj pełną ścieżkę
            # logger.info (już jest w find_matching_preview_for_file)
        else:
            file_info_dict["preview_found"] = False
            index_data["files_without_previews"].append(file_info_dict)
            # logger.debug (już jest w find_matching_preview_for_file)

    # --- Dodawanie obrazów, które nie zostały użyte jako podglądy ---
    logger.debug(f"Dodawanie {len(image_file_details) - len(used_preview_image_paths)} niesparowanych obrazów do 'other_images'.")
    for img_name, img_path, img_size_bytes in image_file_details:
        if img_path not in used_preview_image_paths:
            index_data["other_images"].append({
                "name": img_name,
                "path_absolute": os.path.abspath(img_path),
                "size_bytes": img_size_bytes,
                "size_readable": get_file_size_readable(img_size_bytes),
            })

    # --- Finalizacja statystyk folderu i zapis index.json ---
    index_data["folder_info"]["total_size_readable"] = get_file_size_readable(index_data["folder_info"]["total_size_bytes"])
    index_data["folder_info"]["scan_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        logger.debug(f"Próba zapisu pliku index.json do: {index_json_path}")
        with open(index_json_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4, ensure_ascii=False)
        logger.info(f"💾 Zapisano plik index.json: {index_json_path}")
        if progress_callback:
            progress_callback(f"💾 Zapisano: {index_json_path}")
    except IOError as e_io_write:
        msg = f"❌ Błąd zapisu pliku index.json ({index_json_path}): {e_io_write}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)
    except Exception as e_json_write: # Inne błędy np. z serializacją (mało prawdopodobne tutaj)
        msg = f"❌ Nieoczekiwany błąd podczas zapisu index.json ({index_json_path}): {e_json_write}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)


    # --- Przetwarzanie podfolderów (rekurencja) ---
    logger.debug(f"Znaleziono {len(subdirectories_to_scan_recursively)} podfolderów do rekurencyjnego skanowania.")
    for subdir_path in subdirectories_to_scan_recursively:
        logger.info(f"⤵️ Przechodzę do przetwarzania podfolderu: {subdir_path}")
        # Ważne: przekazujemy progress_callback dalej
        process_folder(subdir_path, progress_callback) 


def process_folder_with_retry(folder_path, max_retries=3, progress_callback=None):
    """Przetwarza folder z mechanizmem ponownych prób w przypadku błędów dostępu."""
    logger.debug(f"Rozpoczęcie przetwarzania folderu z mechanizmem retry: {folder_path} (max_retries={max_retries})")
    
    # Ustawienie domyślnego retry_delay jeśli nie ma w konfiguracji
    retry_delay_seconds = float(config_manager.get_config_value("retry_delay_seconds", "0.5"))

    for attempt in range(max_retries):
        try:
            process_folder(folder_path, progress_callback)
            return # Sukces, wyjdź z funkcji
        except PermissionError as e_perm: # Tylko PermissionError jest tutaj retry-able
            logger.warning(f"Błąd dostępu (PermissionError) przy przetwarzaniu {folder_path} - próba {attempt + 1}/{max_retries}: {e_perm}")
            if progress_callback:
                progress_callback(f"Błąd dostępu {folder_path} (próba {attempt + 1}), ponawiam za {retry_delay_seconds}s...")
            
            if attempt == max_retries - 1:
                msg = f"🚫 Nie udało się uzyskać dostępu do folderu {folder_path} po {max_retries} próbach z powodu PermissionError."
                logger.error(msg)
                if progress_callback: progress_callback(msg)
                # Nie rzucamy wyjątku dalej, aby skanowanie mogło kontynuować inne foldery,
                # chyba że chcemy innego zachowania. Tutaj logujemy i kończymy dla tego folderu.
                return 
            time.sleep(retry_delay_seconds)
        # Inne wyjątki z process_folder (np. OSError, RuntimeError) nie są tutaj łapane,
        # aby mogły być obsłużone wyżej lub przerwać skanowanie, jeśli są krytyczne.
        # process_folder sam loguje swoje błędy.

    logger.debug(f"Zakończono (lub przerwano retry) przetwarzanie dla: {folder_path}")


def start_scanning(root_folder_path, progress_callback=None):
    """Rozpoczyna skanowanie od podanego folderu głównego."""
    logger.info(f"🚀 Rozpoczynam skanowanie od folderu głównego: {root_folder_path}")
    if progress_callback: progress_callback(f"🚀 Rozpoczynam skanowanie: {root_folder_path}")

    if not os.path.isdir(root_folder_path): # Sprawdź czy to folder przed os.access
        msg = f"❌ Błąd: Ścieżka '{root_folder_path}' nie jest folderem lub nie istnieje."
        logger.error(msg)
        if progress_callback: progress_callback(msg)
        return

    try:
        if not os.access(root_folder_path, os.R_OK):
            msg = f"❌ Brak uprawnień do odczytu folderu głównego: {root_folder_path}"
            logger.error(msg)
            if progress_callback: progress_callback(msg)
            return

        # Sprawdzenie czy folder nie jest pusty (opcjonalne, może być mylące jeśli zawiera tylko podfoldery)
        # try:
        #     if not os.listdir(root_folder_path): # listdir może być wolne dla dużych folderów
        #         msg = f"⚠️ Folder główny jest pusty (nie zawiera plików ani podfolderów na pierwszym poziomie): {root_folder_path}"
        #         logger.warning(msg)
        #         if progress_callback: progress_callback(msg)
        # except OSError as e_listdir_root:
        #     logger.warning(f"Nie można sprawdzić zawartości folderu głównego {root_folder_path} z os.listdir: {e_listdir_root}")

        # Uruchom skanowanie z mechanizmem retry dla folderu głównego,
        # a następnie rekurencyjnie dla podfolderów (obsługiwane wewnątrz process_folder)
        max_retries_for_scan = int(config_manager.get_config_value("max_scan_retries", "3"))
        process_folder_with_retry(root_folder_path, max_retries=max_retries_for_scan, progress_callback=progress_callback)

        logger.info("✅ Skanowanie zakończone.")
        if progress_callback: progress_callback("✅ Skanowanie zakończone.")

    except Exception as e_critical: # Łapanie wszelkich innych, nieprzewidzianych błędów na najwyższym poziomie
        msg = f"💥 Krytyczny błąd podczas operacji start_scanning dla '{root_folder_path}': {e_critical}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)
        # Można zdecydować o ponownym rzuceniu wyjątku, jeśli aplikacja główna ma go obsłużyć
        # raise


def quick_rescan_folder(folder_path, progress_callback=None):
    """Szybkie ponowne skanowanie folderu po modyfikacji plików"""
    logger.info(f"🔄 Rozpoczynam szybkie ponowne skanowanie folderu: {folder_path}")
    if progress_callback:
        progress_callback(f"🔄 Ponowne skanowanie: {folder_path}")
    
    # Użyj process_folder bezpośrednio (retry jest bardziej na poziomie całego skanowania lub pierwszego dostępu)
    # Można dodać retry, jeśli jest taka potrzeba specyficznie dla rescan.
    try:
        process_folder(folder_path, progress_callback)
        logger.info(f"✅ Szybkie ponowne skanowanie folderu {folder_path} zakończone.")
        if progress_callback: progress_callback(f"✅ Ponowne skanowanie {folder_path} zakończone.")
    except Exception as e:
        msg = f"❌ Błąd podczas szybkiego ponownego skanowania {folder_path}: {e}"
        logger.error(msg, exc_info=True)
        if progress_callback: progress_callback(msg)


if __name__ == "__main__":
    print("--- Rozpoczynam testowanie scanner_logic.py ---")

    # Ustawienia testowe
    # Możesz chcieć ustawić enable_file_logging na True, aby zobaczyć szczegółowe logi w pliku
    # logger = setup_logger(enable_file_logging=False) # Lub True
    # config_manager można by zamockować lub utworzyć tymczasowy plik config.json
    # Na potrzeby tego testu, zakładamy, że config_manager.get_config_value zwróci domyślne wartości.
    
    # --- Tworzenie tymczasowej struktury folderów i plików ---
    base_test_dir = Path("./test_scan_environment_no_archive") # Użyj ścieżki względnej dla łatwiejszego czyszczenia
    
    if base_test_dir.exists():
        import shutil
        print(f"Usuwam istniejący folder testowy: {base_test_dir.resolve()}")
        try:
            shutil.rmtree(base_test_dir)
        except OSError as e:
            print(f"Nie udało się usunąć starego folderu testowego: {e}. Test może nie być czysty.")
            # exit(1) # Można przerwać, jeśli czysty test jest krytyczny

    print(f"Tworzę nową strukturę testową w: {base_test_dir.resolve()}")
    
    # Główny folder testowy
    main_folder = base_test_dir / "main_scan_dir"
    main_folder.mkdir(parents=True, exist_ok=True)

    # Podfolder
    sub_folder = main_folder / "subfolder_A"
    sub_folder.mkdir(exist_ok=True)

    # Podfolder w podfolderze (głębsza rekurencja)
    sub_sub_folder = sub_folder / "sub_sub_B"
    sub_sub_folder.mkdir(exist_ok=True)

    # Pliki w folderze głównym
    (main_folder / "document_alpha.txt").write_text("Content of document alpha.")
    (main_folder / "document_alpha.jpg").write_text("Fake JPEG for alpha") # Podgląd
    (main_folder / "presentation_beta.pdf").write_text("Content of presentation beta.")
    (main_folder / "presentation_beta_preview.png").write_text("Fake PNG for beta") # Podgląd
    (main_folder / "archive_gamma with spaces.zip").write_text("Fake ZIP content gamma.") # Celowo ze spacjami
    (main_folder / "archive gamma with spaces_cover.gif").write_text("Fake GIF for gamma") # Podgląd
    (main_folder / "loose_image_delta.webp").write_text("Fake WebP delta") # Obraz bez pary
    (main_folder / "no_preview_file_epsilon.docx").write_text("Docx without preview.")
    (main_folder / "index.json").write_text("{}") # Stary index.json, powinien być nadpisany

    # Pliki w podfolderze
    (sub_folder / "notes_zeta.md").write_text("Markdown notes zeta.")
    (sub_folder / "notes_zeta-001.jpg").write_text("Fake JPEG for zeta") # Podgląd
    (sub_folder / "image_only_eta.avif").write_text("Fake AVIF eta")

    # Pliki w pod-podfolderze
    (sub_sub_folder / "final_doc_theta.rtf").write_text("Rich text theta.")
    # Brak podglądu dla final_doc_theta

    # Plik danych uczenia się
    learning_data_content = [
        {"archive_basename": "archive_gamma with spaces", "image_basename": "archive gamma with spaces_cover"},
        {"archive_basename": "document_alpha", "image_basename": "document_alpha"}, # Mimo że pasuje, testujemy czy nauka działa
        {"archive_basename": "non_existent_archive", "image_basename": "non_existent_image_preview"} # Dla testu
    ]
    learning_file_path = base_test_dir / "learning_data_test.json"
    with open(learning_file_path, "w", encoding="utf-8") as lf:
        json.dump(learning_data_content, lf, indent=2)
    
    # Mock config_manager.get_config_value jeśli nie jest dostępny lub chcemy nadpisać
    # W tym przykładzie zakładamy, że config_manager.py istnieje i `get_config_value` 
    # ma sensowne wartości domyślne lub odczytuje je z pliku konfiguracyjnego.
    # Można by to zamockować tak:
    original_get_config = config_manager.get_config_value
    def mocked_get_config_value(key, default=None):
        if key == "learning_data_file":
            return str(learning_file_path.resolve())
        if key == "scan_timeout_per_folder":
            return "30" # Krótki timeout dla testu
        # ... inne klucze
        return original_get_config(key, default) # lub po prostu `default`
    
    config_manager.get_config_value = mocked_get_config_value
    logger.info(f"Używam mockowanego config_manager.get_config_value, plik nauki: {learning_file_path.resolve()}")


    def simple_progress_logger(message):
        print(f"[PROGRESS] {message}")

    print(f"\n--- Rozpoczynam skanowanie testowe w: {main_folder.resolve()} ---")
    try:
        start_scanning(str(main_folder.resolve()), simple_progress_logger)
    except Exception as e:
        print(f"!!! KRYTYCZNY BŁĄD PODCZAS TESTU start_scanning: {e}")
        logger.error("Krytyczny błąd w __main__ podczas start_scanning", exc_info=True)

    print(f"\n--- Skanowanie testowe zakończone. Sprawdź pliki index.json w: ---")
    print(f" - {main_folder.resolve()}")
    print(f" - {sub_folder.resolve()}")
    print(f" - {sub_sub_folder.resolve()}")
    print(f"Oraz logi w konsoli / folderze 'logs'.")

    # Przywrócenie oryginalnej funkcji config_manager, jeśli była mockowana
    config_manager.get_config_value = original_get_config

    # Opcjonalnie: Uruchomienie debugowania dopasowań dla jednego z folderów
    # print(f"\n--- Testuję log_file_matching_debug dla: {main_folder.resolve()} ---")
    # log_file_matching_debug(str(main_folder.resolve()), simple_progress_logger)

    print("\n--- Testowanie zakończone ---")