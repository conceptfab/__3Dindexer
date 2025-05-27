# scanner_logic.py
import json
import os
import re  # Pozostaje, jeśli będziemy szukać dopasowań nazw obrazów
import time  # Dodane dla retry mechanism

# Usunięto ARCHIVE_EXTENSIONS
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")


def get_file_size_readable(size_bytes):
    """Konwertuje rozmiar pliku w bajtach na czytelny format."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"


def get_folder_stats(folder_path):
    """Zbiera statystyki dotyczące folderu."""
    total_size_bytes = 0
    file_count = 0
    subdir_count = 0
    try:
        for entry in os.scandir(folder_path):
            if (
                entry.is_file() and entry.name.lower() != "index.json"
            ):  # Nie liczymy index.json
                try:
                    total_size_bytes += entry.stat().st_size
                    file_count += 1
                except OSError:
                    pass
            elif entry.is_dir():
                subdir_count += 1
    except OSError:
        pass
    return {
        "path": os.path.abspath(folder_path),
        "total_size_bytes": total_size_bytes,
        "total_size_readable": get_file_size_readable(total_size_bytes),
        "file_count": file_count,  # Liczba plików (bez index.json)
        "subdir_count": subdir_count,
    }


def find_matching_preview_for_file(base_filename, image_files_in_folder):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    Nazwa pliku graficznego = nazwa pliku (bez rozszerzenia) + opcjonalny suffix (_0, _001, itp.)
    """
    pattern = re.compile(
        rf"^{re.escape(base_filename)}(?:_\d+)?\.({'|'.join(ext[1:] for ext in IMAGE_EXTENSIONS)})$",
        re.IGNORECASE,
    )

    for (
        img_path
    ) in image_files_in_folder:  # image_files_in_folder to lista pełnych ścieżek
        if pattern.match(os.path.basename(img_path)):
            return img_path
    return None


def process_folder(folder_path, progress_callback=None):
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
        "other_images": [],  # Obrazy, które nie są podglądami niczego
    }

    all_items_in_dir = []
    subdirectories = []

    try:
        # TIMEOUT dla skanowania foldera - maksymalnie 30 sekund na folder
        import threading
        import time

        class TimeoutError(Exception):
            pass

        def timeout_handler():
            raise TimeoutError(f"Timeout podczas skanowania {folder_path}")

        timer = threading.Timer(30.0, timeout_handler)  # 30 sekund timeout
        timer.start()

        try:
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    try:
                        all_items_in_dir.append(entry.name)
                        if entry.is_dir():
                            subdirectories.append(entry.path)
                        if progress_callback and len(all_items_in_dir) % 100 == 0:
                            progress_callback(
                                f"Przetworzono {len(all_items_in_dir)} plików w {folder_path}"
                            )
                    except (OSError, PermissionError) as e:
                        if progress_callback:
                            progress_callback(
                                f"Błąd dostępu do pliku {entry.name}: {e}"
                            )
                        continue
        finally:
            timer.cancel()  # Wyłącz timeout

    except TimeoutError as e:
        if progress_callback:
            progress_callback(f"TIMEOUT: {e}")
        return
    except (OSError, PermissionError) as e:
        if progress_callback:
            progress_callback(f"Błąd dostępu do folderu {folder_path}: {e}")
        return

    # Podziel pliki na obrazy i inne pliki
    image_filenames = [
        f
        for f in all_items_in_dir
        if os.path.isfile(os.path.join(folder_path, f))
        and f.lower().endswith(IMAGE_EXTENSIONS)
    ]
    other_filenames = [
        f
        for f in all_items_in_dir
        if os.path.isfile(os.path.join(folder_path, f))
        and not f.lower().endswith(IMAGE_EXTENSIONS)
        and f.lower() != "index.json"
    ]

    full_path_image_files = [
        os.path.join(folder_path, img_name) for img_name in image_filenames
    ]
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
            "size_readable": get_file_size_readable(file_size_bytes),
        }

        preview_file_path = find_matching_preview_for_file(
            file_basename, full_path_image_files
        )

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

            index_data["other_images"].append(
                {
                    "name": img_name,
                    "path_absolute": os.path.abspath(img_path_full),
                    "size_bytes": img_size_bytes,
                    "size_readable": get_file_size_readable(img_size_bytes),
                }
            )

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
        process_folder(subdir, progress_callback)


def process_folder_with_retry(folder_path, max_retries=3, progress_callback=None):
    """Przetwarza folder z mechanizmem ponownych prób w przypadku błędów dostępu."""
    for attempt in range(max_retries):
        try:
            return process_folder(folder_path, progress_callback)
        except PermissionError:
            if attempt == max_retries - 1:
                if progress_callback:
                    progress_callback(
                        f"Nie udało się uzyskać dostępu do folderu {folder_path} po {max_retries} próbach"
                    )
                raise
            if progress_callback:
                progress_callback(
                    f"Próba {attempt + 1}/{max_retries} nie powiodła się, ponawiam..."
                )
            time.sleep(0.5)  # Krótka pauza przed retry


def start_scanning(root_folder_path, progress_callback=None):
    """Rozpoczyna skanowanie od podanego folderu głównego."""
    if not os.path.isdir(root_folder_path):
        if progress_callback:
            progress_callback(
                f"Błąd: Ścieżka {root_folder_path} nie jest folderem lub nie istnieje."
            )
        return
    process_folder_with_retry(root_folder_path, progress_callback=progress_callback)
    if progress_callback:
        progress_callback("Skanowanie zakończone.")


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
