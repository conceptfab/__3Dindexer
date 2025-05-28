# gallery_generator.py
import hashlib
import json
import os
import re
import shutil
import sys
import time

from jinja2 import Environment, FileSystemLoader, select_autoescape

import ai_sbert_matcher

try:
    import config_manager
except ImportError:

    class MockConfigManager:
        def get_archive_color(self, ext):
            return "grey"  # Domyślny kolor

    config_manager = MockConfigManager()
    print("WARNING: config_manager.py not found. Using a mock version.", flush=True)

PATH_MAP_FILENAME = "path_map.json"  # Stała nazwa pliku mapy


def _normalize_path_for_map_key(path_str: str) -> str:
    """Normalizuje ścieżkę do użycia jako klucz w mapie: forward slashes, lowercase."""
    if not path_str or path_str == ".":
        return "."
    normalized = path_str.replace(os.sep, "/").replace(os.altsep or "\\", "/")
    return normalized.lower()


def get_hashed_folder_name(original_relative_path_str: str) -> str:
    """Generuje hash MD5 dla znormalizowanej ścieżki względnej."""
    if not original_relative_path_str or original_relative_path_str == ".":
        return ""
    normalized_path_for_hash = original_relative_path_str.replace(os.sep, "/").replace(
        os.altsep or "\\", "/"
    )
    return hashlib.md5(normalized_path_for_hash.encode("utf-8")).hexdigest()


def build_path_map(scanned_root_path: str) -> dict:
    """
    Skanuje strukturę katalogów od scanned_root_path w poszukiwaniu plików index.json.
    Buduje mapę: {znormalizowana_ścieżka_względna: hash_katalogu}.
    """
    path_map = {}
    print(
        f"INFO: Rozpoczynam budowanie mapy ścieżek dla: {scanned_root_path}", flush=True
    )
    if os.path.exists(os.path.join(scanned_root_path, "index.json")):
        normalized_root_key = _normalize_path_for_map_key(".")
        path_map[normalized_root_key] = get_hashed_folder_name(".")
        print(
            f"  MAP_ADD: '{normalized_root_key}' -> '{path_map[normalized_root_key]}' (ROOT)",
            flush=True,
        )

    for dirpath, _, filenames in os.walk(scanned_root_path, onerror=walk_error_handler):
        if os.path.islink(dirpath):
            continue
        if "index.json" in filenames:
            relative_path = os.path.relpath(dirpath, scanned_root_path)
            if relative_path == ".":
                continue
            normalized_key = _normalize_path_for_map_key(relative_path)
            hashed_name = get_hashed_folder_name(relative_path)
            if normalized_key not in path_map:
                path_map[normalized_key] = hashed_name
                print(
                    f"  MAP_ADD: '{normalized_key}' (oryg: '{relative_path}') -> '{hashed_name}'",
                    flush=True,
                )
            elif path_map[normalized_key] != hashed_name:
                print(
                    f"  MAP_WARN_COLLISION: Klucz '{normalized_key}' już istnieje. Stara: '{path_map[normalized_key]}', Nowa: '{hashed_name}'",
                    flush=True,
                )
    print(
        f"INFO: Zakończono budowanie mapy ścieżek. Liczba wpisów: {len(path_map)}",
        flush=True,
    )
    if not path_map and not os.path.exists(
        os.path.join(scanned_root_path, "index.json")
    ):  # Sprawdź też roota
        print(
            f"WARNING: Mapa ścieżek jest pusta i root nie ma index.json. Czy w '{scanned_root_path}' są pliki 'index.json'?",
            flush=True,
        )
    return path_map


def load_path_map_from_file(gallery_base_output_path: str) -> dict:
    """Ładuje mapę ścieżek z pliku JSON."""
    map_file = os.path.join(gallery_base_output_path, PATH_MAP_FILENAME)
    loaded_path_map = {}
    if os.path.exists(map_file):
        try:
            with open(map_file, "r", encoding="utf-8") as f:
                raw_loaded_map = json.load(f)
            for k, v in raw_loaded_map.items():
                loaded_path_map[_normalize_path_for_map_key(k)] = v
            print(
                f"INFO: Załadowano mapę ścieżek z {map_file} ({len(loaded_path_map)} wpisów)",
                flush=True,
            )
        except Exception as e:
            print(
                f"ERROR: Nie można załadować mapy {map_file}: {e}. Używam pustej mapy.",
                flush=True,
            )
    else:
        print(
            f"INFO: Plik mapy {map_file} nie istnieje.", flush=True
        )  # Niekoniecznie tworzymy nowy tutaj
    return loaded_path_map


def save_path_map_to_file(path_map: dict, gallery_base_output_path: str):
    """Zapisuje mapę ścieżek do pliku JSON."""
    map_file = os.path.join(gallery_base_output_path, PATH_MAP_FILENAME)
    try:
        os.makedirs(os.path.dirname(map_file), exist_ok=True)
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(path_map, f, indent=2, sort_keys=True)
        print(
            f"INFO: Zapisano mapę ścieżek do {map_file} ({len(path_map)} wpisów)",
            flush=True,
        )
    except Exception as e:
        print(f"ERROR: Nie można zapisać mapy do {map_file}: {e}", flush=True)


def sanitize_path_for_foldername(path_str: str) -> str:
    if not path_str:
        return "default_gallery"
    path_str = re.sub(r"^([a-zA-Z]):", r"\1_drive", path_str)
    path_str = re.sub(r'[\\/*?"<>|:]', "_", path_str)
    path_str = re.sub(r"_+", "_", path_str)
    path_str = path_str.strip("_")
    return path_str if path_str else "default_gallery"


def generate_breadcrumb_hashed(
    relative_path_from_scanned_root: str,
    gallery_root_name: str,
    is_root_index_page: bool,
    current_path_map: dict,
):
    parts = []
    if is_root_index_page:
        parts.append({"name": gallery_root_name, "link": None})
        return parts, 0
    parts.append({"name": gallery_root_name, "link": "../index.html"})
    path_components = []
    if relative_path_from_scanned_root != ".":
        path_components = os.path.normpath(relative_path_from_scanned_root).split(
            os.sep
        )

    current_accumulated_original_path = ""
    for i, component_name in enumerate(path_components):
        if not component_name:
            continue
        current_accumulated_original_path = os.path.join(
            current_accumulated_original_path, component_name
        )
        map_key_for_link = _normalize_path_for_map_key(
            current_accumulated_original_path
        )
        hashed_segment_for_link = current_path_map.get(map_key_for_link)

        is_last_component = i == len(path_components) - 1

        if (
            hashed_segment_for_link is None and not is_last_component
        ):  # Błąd tylko jeśli to nie ostatni komponent
            print(
                f"ERROR_BREADCRUMB: Brak mapowania dla klucza '{map_key_for_link}'. Komponent '{component_name}' nie będzie linkiem.",
                flush=True,
            )
            parts.append({"name": component_name, "link": None})  # Nie ma linku
        elif is_last_component:  # Ostatni komponent (bieżący folder) - zawsze bez linku
            parts.append({"name": component_name, "link": None})
        else:  # Komponent pośredni z hashem
            parts.append(
                {
                    "name": component_name,
                    "link": f"../{hashed_segment_for_link}/index.html",
                }
            )

    return parts, len(path_components)  # Zwraca oryginalną głębokość


def should_regenerate_gallery(
    index_json_path,
    output_html_path,
    template_dir_to_check,
    gallery_base_output_path_for_map,
):
    if not os.path.exists(output_html_path):
        return True
    try:
        output_html_mtime = os.path.getmtime(output_html_path)
        if template_dir_to_check:  # Tylko jeśli jest katalog szablonów
            for tf_name in ["gallery_template.html", "gallery_styles.css"]:
                tf_path = os.path.join(template_dir_to_check, tf_name)
                if (
                    os.path.exists(tf_path)
                    and os.path.getmtime(tf_path) > output_html_mtime
                ):
                    print(
                        f"INFO: Regeneracja {output_html_path} bo szablon/CSS ({tf_name}) jest nowszy.",
                        flush=True,
                    )
                    return True

        map_file_path = os.path.join(
            gallery_base_output_path_for_map, PATH_MAP_FILENAME
        )
        if (
            os.path.exists(map_file_path)
            and os.path.getmtime(map_file_path) > output_html_mtime
        ):
            print(
                f"INFO: Regeneracja {output_html_path} bo mapa ({map_file_path}) jest nowsza.",
                flush=True,
            )
            return True

        if os.path.getmtime(index_json_path) > output_html_mtime:
            print(
                f"INFO: Regeneracja {output_html_path} bo index.json jest nowszy.",
                flush=True,
            )
            return True
        return False
    except OSError:
        return True


def process_single_index_json(
    index_json_path: str,
    scanned_root_path: str,
    gallery_output_base_path: str,  # To jest gallery_specific_output_base
    template_env: Environment,
    final_template_dir: str,
    current_path_map: dict,
    progress_callback=None,  # Nie jest obecnie używany w tej funkcji
):
    try:
        with open(index_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Odczyt {index_json_path}: {e}", flush=True)
        return None

    current_folder_abs_path = os.path.dirname(index_json_path)
    relative_path_from_scanned_root = os.path.relpath(
        current_folder_abs_path, scanned_root_path
    )
    map_key_for_current = _normalize_path_for_map_key(relative_path_from_scanned_root)
    hashed_gallery_segment = current_path_map.get(map_key_for_current)

    if hashed_gallery_segment is None:
        print(
            f"CRITICAL_ERROR: Brak hasha w mapie dla '{map_key_for_current}'. Pomijam {index_json_path}",
            flush=True,
        )
        return None

    current_gallery_html_dir = os.path.join(
        gallery_output_base_path, hashed_gallery_segment
    )
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Tworzenie {current_gallery_html_dir}: {e}", flush=True)
        return None

    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    if os.path.exists(output_html_file) and not should_regenerate_gallery(
        index_json_path,
        output_html_file,
        final_template_dir,
        gallery_output_base_path,  # Przekaż gallery_output_base_path do should_regenerate
    ):
        # print(f"INFO: Pomijam regenerację {output_html_file}, jest aktualny.", flush=True)
        return output_html_file

    print(
        f"INFO: Rozpoczynam generowanie HTML dla: {relative_path_from_scanned_root} -> {output_html_file}",
        flush=True,
    )

    try:
        template = template_env.get_template("gallery_template.html")
    except Exception as e:
        print(f"ERROR: Ładowanie szablonu: {e}", flush=True)
        return None

    is_root_index_page = relative_path_from_scanned_root == "."

    path_components_for_depth = []
    if relative_path_from_scanned_root != ".":
        path_components_for_depth = os.path.normpath(
            relative_path_from_scanned_root
        ).split(os.sep)
    calculated_depth = len(path_components_for_depth)

    template_data = {
        "folder_info": data.get("folder_info", {}),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "subfolders": [],
        "current_folder_display_name": (
            os.path.basename(current_folder_abs_path)
            if not is_root_index_page
            else os.path.basename(scanned_root_path)
        ),
        "breadcrumb_parts": [],
        "depth": calculated_depth,
        "is_root_gallery_index": is_root_index_page,
        "css_path_prefix": "" if is_root_index_page else "../",  # Kluczowe dla CSS
        "scanned_root_path_abs_for_template": os.path.abspath(scanned_root_path),
        "current_rel_path_for_template": relative_path_from_scanned_root,
        "complete_path_map_for_template": current_path_map,
    }

    gallery_root_name_for_bc = os.path.basename(scanned_root_path)
    template_data["breadcrumb_parts"], _ = generate_breadcrumb_hashed(
        relative_path_from_scanned_root,
        gallery_root_name_for_bc,
        is_root_index_page,
        current_path_map,
    )

    discovered_subfolders_data = []
    try:
        for entry in os.scandir(current_folder_abs_path):
            if entry.is_dir(follow_symlinks=False):
                sub_abs_path = entry.path
                sub_index_json_path = os.path.join(sub_abs_path, "index.json")
                if os.path.exists(sub_index_json_path):
                    sub_original_relative_path = os.path.relpath(
                        sub_abs_path, scanned_root_path
                    )
                    sub_map_key = _normalize_path_for_map_key(
                        sub_original_relative_path
                    )
                    sub_hashed_name = current_path_map.get(sub_map_key)
                    if sub_hashed_name is None:
                        print(
                            f"ERROR_LINK_SUB: Brak mapowania dla podfolderu '{sub_map_key}'. Pomijam.",
                            flush=True,
                        )
                        continue
                    sub_fi_data = {
                        "total_size_readable": "N/A",
                        "file_count": 0,
                        "subdir_count": 0,
                    }
                    try:
                        with open(sub_index_json_path, "r", encoding="utf-8") as sfif:
                            sub_json_content = json.load(sfif)
                            fi_from_sub_json = sub_json_content.get("folder_info", {})
                            sub_fi_data["total_size_readable"] = fi_from_sub_json.get(
                                "total_size_readable", "N/A"
                            )
                            sub_fi_data["file_count"] = fi_from_sub_json.get(
                                "file_count", 0
                            )
                            sub_fi_data["subdir_count"] = fi_from_sub_json.get(
                                "subdir_count", 0
                            )
                    except Exception as e_sfi:
                        print(
                            f"WARNING: Błąd odczytu info z {sub_index_json_path}: {e_sfi}",
                            flush=True,
                        )
                    link_prefix_for_subfolder = "" if is_root_index_page else "../"
                    discovered_subfolders_data.append(
                        {
                            "name": entry.name,
                            "link": f"{link_prefix_for_subfolder}{sub_hashed_name}/index.html",
                            "total_size_readable": sub_fi_data["total_size_readable"],
                            "file_count": sub_fi_data["file_count"],
                            "subdir_count": sub_fi_data["subdir_count"],
                        }
                    )
    except Exception as e_scan_sub:
        print(
            f"ERROR: Skanowanie podfolderów w {current_folder_abs_path}: {e_scan_sub}",
            flush=True,
        )
    template_data["subfolders"] = sorted(
        discovered_subfolders_data, key=lambda sf: sf["name"].lower()
    )

    for item_type_key in [
        "files_with_previews",
        "files_without_previews",
        "other_images",
    ]:
        for item_from_json in data.get(item_type_key, []):
            copied_item = item_from_json.copy()
            if "path_absolute" in copied_item:
                common_link_part = (
                    f"file:///{copied_item['path_absolute'].replace(os.sep, '/')}"
                )
                if item_type_key == "other_images":
                    copied_item["file_link"] = common_link_part
                    copied_item["image_relative_path"] = common_link_part
                else:
                    copied_item["archive_link"] = common_link_part
                    if item_type_key == "files_with_previews" and copied_item.get(
                        "preview_path_absolute"
                    ):
                        copied_item["preview_relative_path"] = (
                            f"file:///{copied_item['preview_path_absolute'].replace(os.sep, '/')}"
                        )
                file_ext = os.path.splitext(copied_item.get("name", ""))[1].lower()
                copied_item["archive_color"] = config_manager.get_archive_color(
                    file_ext
                )
                if "size_readable" not in copied_item:
                    if "size" in copied_item and isinstance(
                        copied_item["size"], (int, float)
                    ):
                        size_val = copied_item["size"]
                        if size_val < 1024:
                            copied_item["size_readable"] = f"{size_val} B"
                        elif size_val < 1024 * 1024:
                            copied_item["size_readable"] = f"{size_val/1024:.1f} KB"
                        else:
                            copied_item["size_readable"] = (
                                f"{size_val/(1024*1024):.1f} MB"
                            )
                    else:
                        copied_item["size_readable"] = "N/A"
            template_data[item_type_key].append(copied_item)

    try:
        html_content = template.render(template_data)
        if not html_content or len(html_content) < 100:
            raise ValueError("HTML pusty/za krótki.")
        temp_html_file = output_html_file + f".tmp_{int(time.time())}"
        with open(temp_html_file, "w", encoding="utf-8") as f_html:
            f_html.write(html_content)
        if os.path.exists(temp_html_file) and os.path.getsize(temp_html_file) > 0:
            if os.path.exists(output_html_file):
                os.remove(output_html_file)
            os.rename(temp_html_file, output_html_file)
        else:
            if os.path.exists(temp_html_file):
                os.remove(temp_html_file)
            raise IOError(f"Plik tymczasowy {temp_html_file} nie zapisany.")
    except Exception as e_html:
        print(
            f"ERROR: Generowanie HTML dla '{relative_path_from_scanned_root}': {e_html}",
            flush=True,
        )
        return None
    # print(f"INFO: Pomyślnie wygenerowano: {output_html_file}", flush=True)
    return output_html_file


def walk_error_handler(os_err):
    print(f"ERROR_WALK: os.walk na '{os_err.filename}': {os_err.strerror}", flush=True)


def generate_full_gallery(scanned_root_path: str, gallery_cache_root_dir: str = "."):
    print(
        f"--- Rozpoczynam generate_full_gallery dla: {scanned_root_path} ---",
        flush=True,
    )
    if not os.path.isdir(scanned_root_path):
        print(
            f"ERROR: Ścieżka skanowania '{scanned_root_path}' nie jest katalogiem.",
            flush=True,
        )
        return None

    scanned_root_path = os.path.abspath(scanned_root_path)
    gallery_cache_root_dir = os.path.abspath(gallery_cache_root_dir)

    sanitized_top_level_name = sanitize_path_for_foldername(scanned_root_path)
    gallery_specific_output_base = os.path.join(
        gallery_cache_root_dir, sanitized_top_level_name
    )

    try:
        os.makedirs(gallery_specific_output_base, exist_ok=True)
        print(
            f"INFO: Katalog bazowy galerii: {gallery_specific_output_base}", flush=True
        )
    except Exception as e:
        print(f"ERROR: Tworzenie '{gallery_specific_output_base}': {e}", flush=True)
        return None

    actual_path_map = build_path_map(scanned_root_path)
    save_path_map_to_file(actual_path_map, gallery_specific_output_base)

    if not actual_path_map:
        print(
            f"ERROR: Mapa ścieżek jest pusta. Brak plików index.json w '{scanned_root_path}'.",
            flush=True,
        )
        return None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    td_primary = os.path.join(script_dir, "templates")
    td_alt = "templates"
    final_template_dir = (
        td_primary
        if os.path.isdir(td_primary)
        else (os.path.abspath(td_alt) if os.path.isdir(td_alt) else None)
    )

    if not final_template_dir:
        print(
            f"ERROR: Brak katalogu szablonów. Sprawdzono: '{td_primary}', '{os.path.abspath(td_alt)}'",
            flush=True,
        )
        return None
    print(f"INFO: Używam szablonów z: {final_template_dir}", flush=True)

    try:
        env = Environment(
            loader=FileSystemLoader(final_template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
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
    for dirpath_iter, _, filenames_iter in os.walk(
        scanned_root_path, onerror=walk_error_handler
    ):
        if os.path.islink(dirpath_iter):
            continue
        if "index.json" in filenames_iter:
            paths_to_process_with_index_json.append(
                os.path.join(dirpath_iter, "index.json")
            )
    paths_to_process_with_index_json.sort()
    print(
        f"INFO: Znaleziono {len(paths_to_process_with_index_json)} plików index.json.",
        flush=True,
    )

    for index_json_file_path in paths_to_process_with_index_json:
        # print(f"--- Przetwarzam: {index_json_file_path} ---", flush=True) # Już logowane w process_single
        generated_html = process_single_index_json(
            index_json_file_path,
            scanned_root_path,
            gallery_specific_output_base,
            env,
            final_template_dir,
            actual_path_map,
        )
        if generated_html and os.path.exists(generated_html):
            processed_count += 1
            current_folder_abs = os.path.dirname(index_json_file_path)
            if os.path.abspath(current_folder_abs) == os.path.abspath(
                scanned_root_path
            ):
                expected_root_output_html = os.path.join(
                    gallery_specific_output_base, "index.html"
                )
                if os.path.abspath(generated_html) == os.path.abspath(
                    expected_root_output_html
                ):
                    root_gallery_html_path = generated_html
                    print(
                        f"INFO: Ustawiono główny HTML galerii (pętla): {root_gallery_html_path}",
                        flush=True,
                    )
        else:
            error_count += 1
            print(
                f"ERROR: Nie udało się wygenerować HTML dla {index_json_file_path}",
                flush=True,
            )

    print(
        f"INFO: Podsumowanie: Przetworzono {processed_count}, Błędów {error_count}.",
        flush=True,
    )

    # Ostateczne sprawdzenie ścieżki roota, jeśli nie została ustawiona w pętli
    # (co może się zdarzyć, jeśli root był przetwarzany, ale warunek go nie złapał - mało prawdopodobne)
    if not root_gallery_html_path and processed_count > 0:
        potential_root_html = os.path.join(gallery_specific_output_base, "index.html")
        if os.path.exists(potential_root_html):
            root_gallery_html_path = potential_root_html
            print(
                f"INFO: Główny HTML galerii znaleziony po pętli: {root_gallery_html_path}",
                flush=True,
            )

    if root_gallery_html_path:
        print(f"SUCCESS: Główny HTML galerii: {root_gallery_html_path}", flush=True)
    else:
        print(
            f"ERROR: Główny HTML galerii nie został wygenerowany lub znaleziony.",
            flush=True,
        )
    print(
        f"--- Zakończono generate_full_gallery dla: {scanned_root_path} ---", flush=True
    )
    return root_gallery_html_path


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
    Wersja process_single_index_json dla trybu AI - generuje galerię tylko z dopasowaniami AI
    """
    current_folder_abs_path = os.path.dirname(index_json_path)

    # Wygeneruj dane galerii AI
    ai_gallery_data = ai_sbert_matcher.generate_ai_only_gallery_data(
        current_folder_abs_path
    )

    if not ai_gallery_data or not ai_gallery_data.get("files_with_previews"):
        print(
            f"INFO: Brak danych AI do galerii w {current_folder_abs_path}, pomijam",
            flush=True,
        )
        return None

    relative_path_from_scanned_root = os.path.relpath(
        current_folder_abs_path, scanned_root_path
    )
    map_key_for_current = _normalize_path_for_map_key(relative_path_from_scanned_root)
    hashed_gallery_segment = current_path_map.get(map_key_for_current)

    if hashed_gallery_segment is None:
        print(
            f"CRITICAL_ERROR: Brak hasha w mapie dla '{map_key_for_current}'. Pomijam {index_json_path}",
            flush=True,
        )
        return None

    current_gallery_html_dir = os.path.join(
        gallery_output_base_path, hashed_gallery_segment
    )
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
    except Exception as e:
        print(f"ERROR: Tworzenie {current_gallery_html_dir}: {e}", flush=True)
        return None

    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    print(
        f"INFO: Rozpoczynam generowanie HTML AI dla: {relative_path_from_scanned_root} -> {output_html_file}",
        flush=True,
    )

    try:
        # Spróbuj użyć szablonu AI, jeśli nie ma to użyj zwykłego
        try:
            template = template_env.get_template("gallery_ai_template.html")
            print(
                f"INFO: Używam szablonu AI dla {relative_path_from_scanned_root}",
                flush=True,
            )
        except:
            template = template_env.get_template("gallery_template.html")
            print(
                f"INFO: Używam standardowego szablonu dla AI w {relative_path_from_scanned_root}",
                flush=True,
            )
    except Exception as e:
        print(f"ERROR: Ładowanie szablonu: {e}", flush=True)
        return None

    is_root_index_page = relative_path_from_scanned_root == "."

    path_components_for_depth = []
    if relative_path_from_scanned_root != ".":
        path_components_for_depth = os.path.normpath(
            relative_path_from_scanned_root
        ).split(os.sep)
    calculated_depth = len(path_components_for_depth)

    template_data = {
        "folder_info": ai_gallery_data.get("folder_info", {}),
        "files_with_previews": ai_gallery_data.get("files_with_previews", []),
        "files_without_previews": [],  # Puste w trybie AI
        "other_images": [],  # Puste w trybie AI
        "subfolders": [],  # Zostanie wypełnione poniżej
        "ai_info": ai_gallery_data.get("ai_info", {}),
        "current_folder_display_name": (
            f"🧠 AI: {os.path.basename(current_folder_abs_path)}"
            if not is_root_index_page
            else f"🧠 AI: {os.path.basename(scanned_root_path)}"
        ),
        "breadcrumb_parts": [],
        "depth": calculated_depth,
        "is_root_gallery_index": is_root_index_page,
        "css_path_prefix": "" if is_root_index_page else "../",
        "scanned_root_path_abs_for_template": os.path.abspath(scanned_root_path),
        "current_rel_path_for_template": relative_path_from_scanned_root,
        "complete_path_map_for_template": current_path_map,
        "gallery_mode": "ai",
    }

    gallery_root_name_for_bc = f"🧠 AI: {os.path.basename(scanned_root_path)}"
    template_data["breadcrumb_parts"], _ = generate_breadcrumb_hashed(
        relative_path_from_scanned_root,
        gallery_root_name_for_bc,
        is_root_index_page,
        current_path_map,
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
                        with open(sub_index_json_path, "r", encoding="utf-8") as f:
                            sub_data = json.load(f)
                            if "AI_matches" not in sub_data or not sub_data.get(
                                "AI_matches"
                            ):
                                continue  # Pomiń podfoldery bez danych AI
                    except:
                        continue

                    sub_original_relative_path = os.path.relpath(
                        sub_abs_path, scanned_root_path
                    )
                    sub_map_key = _normalize_path_for_map_key(
                        sub_original_relative_path
                    )
                    sub_hashed_name = current_path_map.get(sub_map_key)
                    if sub_hashed_name is None:
                        print(
                            f"ERROR_LINK_SUB: Brak mapowania dla podfolderu AI '{sub_map_key}'. Pomijam.",
                            flush=True,
                        )
                        continue

                    # Pobierz statystyki AI
                    ai_matches_count = len(sub_data.get("AI_matches", []))
                    ai_stats = sub_data.get("AI_statistics", {})

                    link_prefix_for_subfolder = "" if is_root_index_page else "../"
                    discovered_subfolders_data.append(
                        {
                            "name": f"🧠 {entry.name}",
                            "link": f"{link_prefix_for_subfolder}{sub_hashed_name}/index.html",
                            "total_size_readable": f"{ai_matches_count} dopasowań AI",
                            "file_count": ai_matches_count,
                            "subdir_count": 0,
                            "ai_folder": True,
                        }
                    )
    except Exception as e_scan_sub:
        print(
            f"ERROR: Skanowanie podfolderów AI w {current_folder_abs_path}: {e_scan_sub}",
            flush=True,
        )

    template_data["subfolders"] = sorted(
        discovered_subfolders_data, key=lambda sf: sf["name"].lower()
    )

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
        print(
            f"ERROR: Generowanie HTML AI dla '{relative_path_from_scanned_root}': {e_html}",
            flush=True,
        )
        return None

    print(f"INFO: Pomyślnie wygenerowano galerię AI: {output_html_file}", flush=True)
    return output_html_file


if __name__ == "__main__":
    print(
        "INFO: Test gallery_generator.py (Mapa Pierwsza v3 - pełny kod)...", flush=True
    )
    script_dir_main = os.path.dirname(os.path.abspath(__file__))
    test_scan_parent_dir = os.path.abspath("_test_gallery_artefacts_map_first_v3")
    if os.path.exists(test_scan_parent_dir):
        shutil.rmtree(test_scan_parent_dir)
    os.makedirs(test_scan_parent_dir, exist_ok=True)
    sim_scan_root_name = "Test_MapFirst_Root_v3"
    test_scan_dir = os.path.join(test_scan_parent_dir, sim_scan_root_name)
    os.makedirs(test_scan_dir, exist_ok=True)

    def create_dummy_index(
        path, name, files=None, subfolders_data_names=None, create_index_json=True
    ):
        os.makedirs(path, exist_ok=True)
        if not create_index_json:
            print(f"  DUMMY: Tworzę katalog {name} bez index.json", flush=True)
            return
        print(f"  DUMMY: Tworzę index.json dla {name} w {path}", flush=True)
        folder_info_dict = {
            "name": name,
            "path_absolute": os.path.abspath(path),
            "file_count": len(files) if files else 0,
            "subdir_count": len(subfolders_data_names) if subfolders_data_names else 0,
            "total_size_readable": f"{(len(files) if files else 0) * 10} B",
        }
        if subfolders_data_names:
            folder_info_dict["subfolders_present"] = True
        content = {
            "folder_info": folder_info_dict,
            "files_with_previews": [],
            "files_without_previews": [],
            "other_images": [],
        }
        if files:
            for i, fname in enumerate(files):
                fpath = os.path.join(path, fname)
                try:
                    with open(fpath, "w") as ftemp:
                        ftemp.write(f"content of {fname}")
                except IOError as e:
                    print(f"Warning: Nie można utworzyć pliku {fpath}: {e}")
                content["files_without_previews"].append(
                    {
                        "name": fname,
                        "path_absolute": os.path.abspath(fpath),
                        "size": 10 + i,
                        "size_readable": f"{10+i} B",
                        "ext": os.path.splitext(fname)[1],
                    }
                )
        with open(os.path.join(path, "index.json"), "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)

    print("INFO: Tworzenie struktury testowej...", flush=True)
    create_dummy_index(
        test_scan_dir,
        os.path.basename(test_scan_dir),
        ["root.txt"],
        subfolders_data_names=["L1_A", "L1_B_no_idx", "L1_C"],
    )
    path_l1a = os.path.join(test_scan_dir, "L1_A")
    create_dummy_index(
        path_l1a, "L1_A", ["file_l1a.txt"], subfolders_data_names=["L2_A_sub"]
    )
    path_l2sa = os.path.join(path_l1a, "L2_A_sub")
    create_dummy_index(path_l2sa, "L2_A_sub", ["file_l2sa.dat"])
    path_l1b_no_idx = os.path.join(test_scan_dir, "L1_B_no_idx")
    create_dummy_index(path_l1b_no_idx, "L1_B_no_idx", create_index_json=False)
    path_l2sc_with_idx = os.path.join(path_l1b_no_idx, "L2_B_sub_with_idx")
    create_dummy_index(path_l2sc_with_idx, "L2_B_sub_with_idx", ["file_l2sc.doc"])
    path_l1c = os.path.join(test_scan_dir, "L1_C")
    create_dummy_index(path_l1c, "L1_C", ["file_l1c.jpg"])
    print("INFO: Struktura testowa utworzona.", flush=True)

    gallery_cache_base = os.path.join(
        test_scan_parent_dir, "_gallery_cache_map_first_v3"
    )
    os.makedirs(gallery_cache_base, exist_ok=True)
    templates_dir_path = os.path.join(script_dir_main, "templates")
    if not os.path.exists(templates_dir_path):
        os.makedirs(templates_dir_path)
        print(f"INFO: Utworzono {templates_dir_path}", flush=True)

    template_file_path = os.path.join(templates_dir_path, "gallery_template.html")
    # WAŻNE: Użyj szablonu, który został poprawiony w poprzedniej odpowiedzi (z {{ css_path_prefix }})
    # Poniżej jest skrócona wersja, ale Ty użyj PEŁNEGO POPRAWIONEGO szablonu.
    with open(template_file_path, "w", encoding="utf-8") as f_tpl:
        f_tpl.write(
            """<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8">
        <title>Galeria Testowa: {{ current_folder_display_name }}</title>
        <link rel="stylesheet" href="{{ css_path_prefix }}gallery_styles.css">
        </head><body><h1>{{ current_folder_display_name }}</h1>
        <div class="breadcrumb"><b>Ścieżka:</b> {% for p in breadcrumb_parts %}{% if p.link %}<a href="{{ p.link }}">{{ p.name }}</a>{% else %}<b>{{ p.name }}</b>{% endif %}{% if not loop.last %} / {% endif %}{% endfor %}</div>
        <h2>Podfoldery:</h2><ul>{% for sf_ in subfolders %}<li><a href="{{ sf_.link }}">{{ sf_.name }}</a></li>{% else %}<li>Brak</li>{% endfor %}</ul>
        <h2>Pliki:</h2><ul>{% for f_ in files_without_previews %}<li><a href="{{ f_.archive_link }}">{{ f_.name }}</a></li>{% else %}<li>Brak</li>{% endfor %}</ul>
        <p><small>CSS Path: {{ css_path_prefix }}gallery_styles.css</small></p></body></html>"""
        )

    css_file_path = os.path.join(templates_dir_path, "gallery_styles.css")
    with open(css_file_path, "w", encoding="utf-8") as f_css:
        f_css.write(
            "body {font-family: sans-serif; background-color: #f0f0f0; margin:20px;} .breadcrumb {padding:5px; background-color:#e0e0e0; border:1px solid #ccc; margin-bottom:10px;}"
        )

    print("\nINFO: ===== Rozpoczynam generowanie galerii (TEST) =====\n", flush=True)
    root_html = generate_full_gallery(
        test_scan_dir, gallery_cache_root_dir=gallery_cache_base
    )
    print("\nINFO: ===== Zakończono generowanie galerii (TEST) =====\n", flush=True)

    if root_html and os.path.exists(root_html):
        print(
            f"SUCCESS: Testowa galeria (v3) wygenerowana. Otwórz: file:///{os.path.abspath(root_html).replace(os.sep, '/')}",
            flush=True,
        )
    else:
        print(f"FAILURE: Nie udało się wygenerować testowej galerii (v3).", flush=True)
    print(f"INFO: Artefakty testu (v3) w: {test_scan_parent_dir}", flush=True)
