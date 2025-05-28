python# gallery_generator.py
import json
import os
import re
import shutil
import time
import signal
import sys

from jinja2 import Environment, FileSystemLoader

import config_manager


def sanitize_path_for_foldername(path_str):
    """Sanitizes a path string to be used as a folder name."""
    if not path_str:
        return "default_gallery"
    # Handle Windows drive letters like C:
    path_str = re.sub(r"^([a-zA-Z]):", r"\1_drive", path_str)
    # Replace problematic characters
    path_str = re.sub(r'[\\/*?"<>|:]', "_", path_str)
    # Consolidate multiple underscores
    path_str = re.sub(r"_+", "_", path_str)
    # Remove leading/trailing underscores
    path_str = path_str.strip("_")
    return path_str if path_str else "default_gallery"


def copy_preview_if_newer(src_path, dest_path_in_gallery_previews_dir):
    """Copies a file if source is newer or destination doesn't exist."""
    os.makedirs(os.path.dirname(dest_path_in_gallery_previews_dir), exist_ok=True)
    if not os.path.exists(src_path):
        return False

    if not os.path.exists(dest_path_in_gallery_previews_dir) or os.path.getmtime(
        src_path
    ) > os.path.getmtime(dest_path_in_gallery_previews_dir):
        try:
            shutil.copy2(src_path, dest_path_in_gallery_previews_dir)
            return True
        except Exception as e:
            return False
    return True


def generate_breadcrumb(relative_path_from_scanned_root, gallery_root_name):
    parts = []
    if relative_path_from_scanned_root == ".":
        parts.append({"name": gallery_root_name, "link": None})
        return parts, 0

    path_components = relative_path_from_scanned_root.split(os.sep)
    current_link_path = ""
    depth = len(path_components)

    parts.append({"name": gallery_root_name, "link": "../" * depth + "index.html"})

    for i, component in enumerate(path_components):
        if i < len(path_components) - 1:
            current_link_path += component + "/"
            parts.append(
                {
                    "name": component,
                    "link": "../" * (depth - 1 - i) + "index.html",
                }
            )
        else:
            parts.append({"name": component, "link": None})
    return parts, depth


def should_regenerate_gallery(index_json_path, output_html_path):
    """Sprawdza czy galeria powinna być wygenerowana ponownie."""
    if not os.path.exists(output_html_path):
        return True

    template_files = ["gallery_template.html", "gallery_styles.css"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates")

    if not os.path.isdir(template_dir):
        alt_template_dir = "templates"
        if os.path.isdir(alt_template_dir):
            template_dir = alt_template_dir
        else:
            return True

    for template_file in template_files:
        template_path = os.path.join(template_dir, template_file)
        if os.path.exists(template_path) and os.path.getmtime(
            template_path
        ) > os.path.getmtime(output_html_path):
            return True

    return os.path.getmtime(index_json_path) > os.path.getmtime(output_html_path)


def process_single_index_json(
    index_json_path,
    scanned_root_path,
    gallery_output_base_path,
    template_env,
    progress_callback=None,
):
    if progress_callback:
        progress_callback(f"🔄 Generowanie galerii dla: {index_json_path}")

    try:
        print(f"📂 Wczytywanie pliku index.json: {index_json_path}")
        with open(index_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✅ Wczytano dane z {index_json_path}")
    except Exception as e:
        print(f"❌ Błąd odczytu {index_json_path}: {e}")
        if progress_callback:
            progress_callback(f"❌ Błąd odczytu {index_json_path}: {e}")
        return None

    current_folder_abs_path = os.path.dirname(index_json_path)
    relative_path_from_scanned_root = os.path.relpath(
        current_folder_abs_path, scanned_root_path
    )
    print(f"📁 Ścieżka względna: {relative_path_from_scanned_root}")

    current_gallery_html_dir = os.path.join(
        gallery_output_base_path,
        (
            relative_path_from_scanned_root
            if relative_path_from_scanned_root != "."
            else ""
        ),
    )
    print(f"📂 Tworzenie katalogu galerii: {current_gallery_html_dir}")
    
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
        
        if not os.path.exists(current_gallery_html_dir):
            raise OSError(f"Nie udało się utworzyć katalogu: {current_gallery_html_dir}")
            
        if not os.access(current_gallery_html_dir, os.W_OK):
            raise PermissionError(f"Brak uprawnień do zapisu w: {current_gallery_html_dir}")
            
    except Exception as e:
        print(f"❌ Błąd tworzenia katalogu galerii: {e}")
        if progress_callback:
            progress_callback(f"❌ Błąd tworzenia katalogu galerii: {e}")
        return None

    output_html_file = os.path.join(current_gallery_html_dir, "index.html")
    print(f"📄 Plik wyjściowy: {output_html_file}")

    if os.path.exists(output_html_file) and not should_regenerate_gallery(
        index_json_path, output_html_file
    ):
        print(f"ℹ️ Galeria {output_html_file} jest aktualna, pomijam.")
        if progress_callback:
            progress_callback(f"ℹ️ Galeria {output_html_file} jest aktualna, pomijam.")
        return output_html_file

    print("🔄 Przygotowywanie danych do szablonu...")
    
    try:
        template = template_env.get_template("gallery_template.html")
        print("✅ Szablon załadowany pomyślnie")
    except Exception as e:
        print(f"❌ Błąd ładowania szablonu: {e}")
        if progress_callback:
            progress_callback(f"❌ Błąd ładowania szablonu: {e}")
        return None

    template_data = {
        "folder_info": data.get("folder_info", {}),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "subfolders": [],
        "current_folder_display_name": (
            os.path.basename(current_folder_abs_path)
            if relative_path_from_scanned_root != "."
            else os.path.basename(scanned_root_path)
        ),
        "breadcrumb_parts": [],
        "depth": 0,
    }

    gallery_root_name = os.path.basename(scanned_root_path)
    template_data["breadcrumb_parts"], template_data["depth"] = generate_breadcrumb(
        relative_path_from_scanned_root, gallery_root_name
    )

    print("📁 Przetwarzanie podfolderów...")
    # PRZETWARZANIE PODFOLDERÓW Z TIMEOUT
    processed_subfolders = 0
    start_time = time.time()
    
    try:
        with os.scandir(current_folder_abs_path) as entries:
            for entry in entries:
                # Sprawdź timeout
                if time.time() - start_time > 30:
                    print(f"⏰ Timeout w przetwarzaniu podfolderów: {current_folder_abs_path}")
                    break
                    
                if entry.is_dir():
                    processed_subfolders += 1
                    print(f"📂 [{processed_subfolders}] Sprawdzanie podfolderu: {entry.name}")
                    
                    index_json_path_sub = os.path.join(entry.path, "index.json")
                    try:
                        if os.path.exists(index_json_path_sub):
                            print(f"📄 Wczytywanie index.json z podfolderu: {entry.name}")
                            with open(index_json_path_sub, "r", encoding="utf-8") as f:
                                subfolder_data = json.load(f)
                                folder_info = subfolder_data.get("folder_info", {})
                                template_data["subfolders"].append(
                                    {
                                        "name": entry.name,
                                        "link": f"{entry.name}/index.html",
                                        "total_size_readable": folder_info.get(
                                            "total_size_readable", "0 B"
                                        ),
                                        "file_count": folder_info.get("file_count", 0),
                                        "subdir_count": folder_info.get("subdir_count", 0),
                                    }
                                )
                            print(f"✅ Dodano podfolder: {entry.name}")
                        else:
                            print(f"⚠️ Brak index.json w podfolderze: {entry.name}")
                            template_data["subfolders"].append(
                                {
                                    "name": entry.name,
                                    "link": f"{entry.name}/index.html",
                                    "total_size_readable": "0 B",
                                    "file_count": 0,
                                    "subdir_count": 0,
                                }
                            )
                            
                    except Exception as e:
                        print(f"❌ Błąd przetwarzania podfolderu {entry.name}: {e}")
                        template_data["subfolders"].append(
                            {
                                "name": entry.name,
                                "link": f"{entry.name}/index.html",
                                "total_size_readable": "0 B",
                                "file_count": 0,
                                "subdir_count": 0,
                            }
                        )
                        
                    # Raportuj postęp co 10 podfolderów
                    if processed_subfolders % 10 == 0 and progress_callback:
                        progress_callback(f"📁 Przetworzono {processed_subfolders} podfolderów")
                        
    except Exception as e:
        print(f"❌ Błąd podczas skanowania podfolderów: {e}")

    print(f"📁 Zakończono przetwarzanie {processed_subfolders} podfolderów")

    print("🖼️ Przetwarzanie plików z podglądami...")
    # PRZETWARZANIE PLIKÓW Z PODGLĄDAMI
    processed_files = 0
    start_time = time.time()
    
    for item in data.get("files_with_previews", []):
        # Sprawdź timeout
        if time.time() - start_time > 20:
            print(f"⏰ Timeout w przetwarzaniu plików z podglądami")
            break
            
        try:
            processed_files += 1
            if processed_files % 50 == 0:
                print(f"📄 [{processed_files}] Przetwarzanie pliku z podglądem: {item.get('name', '')}")
                
            copied_item = item.copy()
            copied_item["archive_link"] = f"file:///{item['path_absolute']}"
            if item.get("preview_path_absolute"):
                copied_item["preview_relative_path"] = (
                    f"file:///{item['preview_path_absolute']}"
                )

            file_name = item.get("name", "")
            file_ext = os.path.splitext(file_name)[1].lower()
            copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

            template_data["files_with_previews"].append(copied_item)
            
        except Exception as e:
            print(f"❌ Błąd przetwarzania pliku z podglądem {item.get('name', '')}: {e}")
            continue

    print(f"✅ Przetworzono {len(template_data['files_with_previews'])} plików z podglądami")

    print("📄 Przetwarzanie plików bez podglądów...")
    # PRZETWARZANIE PLIKÓW BEZ PODGLĄDÓW
    processed_files = 0
    start_time = time.time()
    
    for item in data.get("files_without_previews", []):
        # Sprawdź timeout
        if time.time() - start_time > 15:
            print(f"⏰ Timeout w przetwarzaniu plików bez podglądów")
            break
            
        try:
            processed_files += 1
            if processed_files % 50 == 0:
                print(f"📄 [{processed_files}] Przetwarzanie pliku bez podglądu: {item.get('name', '')}")
                
            copied_item = item.copy()
            copied_item["archive_link"] = f"file:///{item['path_absolute']}"

            file_name = item.get("name", "")
            file_ext = os.path.splitext(file_name)[1].lower()
            copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

            template_data["files_without_previews"].append(copied_item)
            
        except Exception as e:
            print(f"❌ Błąd przetwarzania pliku bez podglądu {item.get('name', '')}: {e}")
            continue

    print(f"✅ Przetworzono {len(template_data['files_without_previews'])} plików bez podglądów")

    print("🖼️ Przetwarzanie pozostałych obrazów...")
    # PRZETWARZANIE OBRAZÓW Z LIMITEM
    processed_images = 0
    start_time = time.time()
    max_images = 500  # Zmniejszony limit
    
    for item in data.get("other_images", []):
        # KRYTYCZNY timeout
        if time.time() - start_time > 5:  # Zmniejszono z 10 do 5 sekund
            print(f"⏰ TIMEOUT w przetwarzaniu obrazów po {processed_images} elementach")
            break
            
        # Limit obrazów
        if processed_images >= max_images:
            print(f"📊 Osiągnięto limit {max_images} obrazów, pomijam resztę")
            break
            
        try:
            processed_images += 1
            
            # Raportuj co 50 obrazów
            if processed_images % 50 == 0:
                print(f"🖼️ [{processed_images}] Przetwarzanie obrazu: {item.get('name', '')}")
                if progress_callback:
                    progress_callback(f"🖼️ Przetworzono {processed_images} obrazów")
            
            copied_item = item.copy()
            copied_item["file_link"] = f"file:///{item['path_absolute']}"
            if item.get("path_absolute"):
                copied_item["image_relative_path"] = f"file:///{item['path_absolute']}"
            template_data["other_images"].append(copied_item)
            
        except Exception as e:
            print(f"❌ Błąd przetwarzania obrazu {item.get('name', '')}: {e}")
            continue

    print(f"✅ Przetworzono {len(template_data['other_images'])} pozostałych obrazów")

    print("📝 Generowanie HTML...")
    try:
        print(f"📊 Dane do szablonu: {len(template_data['files_with_previews'])} plików z podglądami, {len(template_data['files_without_previews'])} bez podglądów, {len(template_data['other_images'])} innych obrazów")
        print("🔄 Renderowanie szablonu...")
        
        # Renderowanie z prostym timeout
        start_render = time.time()
        html_content = template.render(template_data)
        render_time = time.time() - start_render
        
        print(f"✅ Szablon wyrenderowany w {render_time:.2f}s, rozmiar: {len(html_content)} bajtów")
        
        if not html_content or len(html_content) < 100:
            raise ValueError("Wygenerowany HTML jest pusty lub zbyt krótki")
        
        print(f"💾 Zapisuję plik HTML: {output_html_file}")
        
        # Dodatkowe sprawdzenia przed zapisem
        output_dir = os.path.dirname(output_html_file)
        if not os.path.exists(output_dir):
            print(f"📂 Tworzę katalog: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # ATOMOWY ZAPIS
        temp_html_file = output_html_file + ".tmp"
        try:
            with open(temp_html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            if os.path.exists(temp_html_file) and os.path.getsize(temp_html_file) > 0:
                if os.path.exists(output_html_file):
                    os.remove(output_html_file)
                os.rename(temp_html_file, output_html_file)
                print(f"✅ Zapisano galerię: {output_html_file}")
            else:
                raise IOError("Plik tymczasowy nie został zapisany poprawnie")
                
        except Exception as write_error:
            if os.path.exists(temp_html_file):
                try:
                    os.remove(temp_html_file)
                except:
                    pass
            raise write_error
            
        if os.path.exists(output_html_file):
            file_size = os.path.getsize(output_html_file)
            print(f"✅ Plik zapisany, rozmiar: {file_size} bajtów")
            
            if file_size < 100:
                raise ValueError(f"Zapisany plik HTML jest zbyt mały: {file_size} bajtów")
        else:
            raise IOError("Plik nie został zapisany mimo braku błędów!")
            
        if progress_callback:
            progress_callback(f"✅ Zapisano galerię: {output_html_file}")
            
    except Exception as e:
        print(f"❌ Błąd generowania HTML dla {index_json_path}: {e}")
        if progress_callback:
            progress_callback(f"❌ Błąd generowania HTML dla {index_json_path}: {e}")
        return None

    return output_html_file


def generate_full_gallery(scanned_root_path, gallery_cache_root_dir="."):
    """Generates the full gallery."""
    print(f"🚀 Rozpoczynam generowanie galerii dla: {scanned_root_path}")
    
    if not os.path.isdir(scanned_root_path):
        print(f"❌ Błąd: Ścieżka {scanned_root_path} nie jest katalogiem.")
        return None

    sanitized_folder_name = sanitize_path_for_foldername(scanned_root_path)
    gallery_output_base_path = os.path.join(
        gallery_cache_root_dir, sanitized_folder_name
    )
    print(f"📂 Katalog wyjściowy galerii: {gallery_output_base_path}")
    
    try:
        os.makedirs(gallery_output_base_path, exist_ok=True)
        
        if not os.access(gallery_output_base_path, os.W_OK):
            print(f"❌ Brak uprawnień do zapisu w: {gallery_output_base_path}")
            return None
            
    except Exception as e:
        print(f"❌ Błąd tworzenia katalogu galerii: {e}")
        return None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates")
    print(f"📂 Katalog szablonów: {template_dir}")

    if not os.path.isdir(template_dir):
        print(f"⚠️ Nie znaleziono katalogu szablonów w {template_dir}")
        alt_template_dir = "templates"
        if os.path.isdir(alt_template_dir):
            template_dir = alt_template_dir
            print(f"✅ Użyto alternatywnego katalogu szablonów: {template_dir}")
        else:
            print("❌ Nie można znaleźć katalogu szablonów.")
            return None

    template_html_path = os.path.join(template_dir, "gallery_template.html")
    if not os.path.exists(template_html_path):
        print(f"❌ Nie znaleziono szablonu HTML: {template_html_path}")
        return None

    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        test_template = env.get_template("gallery_template.html")
        print("✅ Zainicjalizowano środowisko szablonów")
    except Exception as e:
        print(f"❌ Błąd inicjalizacji szablonów: {e}")
        return None

    # KOPIOWANIE CSS
    css_src_path = os.path.join(template_dir, "gallery_styles.css")
    css_dest_path = os.path.join(gallery_output_base_path, "gallery_styles.css")
    
    print(f"📄 Kopiowanie CSS z {css_src_path} do {css_dest_path}")
    
    if os.path.exists(css_src_path):
        try:
            css_size = os.path.getsize(css_src_path)
            if css_size == 0:
                print(f"⚠️ Plik CSS jest pusty: {css_src_path}")
            else:
                print(f"📄 Rozmiar pliku CSS: {css_size} bajtów")
            
            shutil.copy2(css_src_path, css_dest_path)
            
            if os.path.exists(css_dest_path):
                copied_size = os.path.getsize(css_dest_path)
                if copied_size == css_size:
                    print(f"✅ Skopiowano plik CSS: {css_dest_path} ({copied_size} bajtów)")
                else:
                    print(f"⚠️ Rozmiar skopiowanego CSS nie zgadza się: {copied_size} vs {css_size}")
            else:
                print(f"❌ Plik CSS nie został skopiowany: {css_dest_path}")
                
        except Exception as e:
            print(f"❌ Nie można skopiować gallery_styles.css: {e}")
            return None
    else:
        print(f"❌ Nie znaleziono pliku gallery_styles.css w {css_src_path}")
        return None

    root_gallery_html_path = None
    processed_count = 0
    error_count = 0

    print("🔄 Rozpoczynam przetwarzanie plików index.json...")
    
    for dirpath, dirnames, filenames in os.walk(scanned_root_path):
        if os.path.islink(dirpath):
            print(f"⚠️ Pomijam link symboliczny: {dirpath}")
            continue
            
        if "index.json" in filenames:
            index_json_file = os.path.join(dirpath, "index.json")
            print(f"📄 Przetwarzanie: {index_json_file}")
            
            try:
                with open(index_json_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                
                generated_html = process_single_index_json(
                    index_json_file, scanned_root_path, gallery_output_base_path, env, print
                )
                
                if generated_html and os.path.exists(generated_html):
                    processed_count += 1
                    if dirpath == scanned_root_path:
                        root_gallery_html_path = generated_html
                        print(f"✅ Znaleziono główny plik HTML: {generated_html}")
                else:
                    error_count += 1
                    print(f"❌ Nie udało się wygenerować HTML dla: {index_json_file}")
                    
            except json.JSONDecodeError as e:
                error_count += 1
                print(f"❌ Uszkodzony plik JSON {index_json_file}: {e}")
            except Exception as e:
                error_count += 1
                print(f"❌ Błąd przetwarzania {index_json_file}: {e}")

    print(f"📊 Podsumowanie: Przetworzono {processed_count} plików, {error_count} błędów")
    
    if root_gallery_html_path and os.path.exists(root_gallery_html_path):
        print(f"✅ Generowanie galerii zakończone. Główny plik HTML: {root_gallery_html_path}")
        
        try:
            file_size = os.path.getsize(root_gallery_html_path)
            if file_size < 100:
                print(f"⚠️ Główny plik HTML jest podejrzanie mały: {file_size} bajtów")
            else:
                print(f"✅ Rozmiar głównego pliku HTML: {file_size} bajtów")
        except Exception as e:
            print(f"⚠️ Nie można sprawdzić rozmiaru głównego pliku: {e}")
        
    else:
        print("❌ Generowanie galerii nie powiodło się lub nie znaleziono index.json w głównym katalogu.")
        
    return root_gallery_html_path


if __name__ == "__main__":
    import subprocess
    import sys

    subprocess.run([sys.executable, "scanner_logic.py"])

    test_scan_dir = "/tmp/test_scan_py_no_archive"
    if not os.path.exists(os.path.join(test_scan_dir, "index.json")):
        print(f"Please run scanner_logic.py first to create test data in {test_scan_dir}")
    else:
        print(f"Generating gallery for: {test_scan_dir}")
        gallery_cache = "_test_gallery_cache"
        os.makedirs(gallery_cache, exist_ok=True)

        if not os.path.exists("templates"):
            os.makedirs("templates")
        if not os.path.exists("templates/gallery_template.html"):
            with open("templates/gallery_template.html", "w") as f:
                f.write("<html><body><h1>Test Template for {{ current_folder_display_name }}</h1></body></html>")
        if not os.path.exists("templates/gallery_styles.css"):
            with open("templates/gallery_styles.css", "w") as f:
                f.write("/* Test CSS */ body { background-color: #eee; }")

        root_html = generate_full_gallery(test_scan_dir, gallery_cache_root_dir=gallery_cache)
        if root_html:
            print(f"Test gallery generated. Open: file://{os.path.abspath(root_html)}")
Główne poprawki:

Usunięto błędną zmienną start_time - była używana przed zdefiniowaniem
Poprawiono obsługę os.scandir() - używam with statement dla właściwego zamykania
Usunięto skomplikowany timeout z signal - zastąpiono prostym sprawdzaniem czasu
Zmniejszono limity - 500 obrazów zamiast 1000, 5 sekund zamiast 10
Dodano continue w except blocks żeby nie przerywać całej pętli
Uproszczono logikę timeout - prostsze sprawdzanie czasu bez threading

Teraz kod powinien działać bez zawieszania się na początku.