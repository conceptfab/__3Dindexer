# gallery_generator.py
import json
import os
import re
import shutil

from jinja2 import Environment, FileSystemLoader


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
        # print(f"Warning: Source preview not found: {src_path}")
        return False  # Indicate failure

    if not os.path.exists(dest_path_in_gallery_previews_dir) or os.path.getmtime(
        src_path
    ) > os.path.getmtime(dest_path_in_gallery_previews_dir):
        try:
            shutil.copy2(src_path, dest_path_in_gallery_previews_dir)
            return True  # Indicate success
        except Exception as e:
            # print(f"Error copying {src_path} to {dest_path_in_gallery_previews_dir}: {e}")
            return False  # Indicate failure
    return True  # Already up-to-date


def generate_breadcrumb(relative_path_from_scanned_root, gallery_root_name):
    parts = []
    if relative_path_from_scanned_root == ".":
        parts.append({"name": gallery_root_name, "link": None})
        return parts, 0  # depth 0

    path_components = relative_path_from_scanned_root.split(os.sep)
    current_link_path = ""
    depth = len(path_components)

    # Root breadcrumb part
    parts.append({"name": gallery_root_name, "link": "../" * depth + "index.html"})

    for i, component in enumerate(path_components):
        if i < len(path_components) - 1:
            current_link_path += component + "/"
            parts.append(
                {
                    "name": component,
                    "link": "../" * (depth - 1 - i)
                    + "index.html",  # Link to its own index.html
                }
            )
        else:  # Last component is current folder
            parts.append({"name": component, "link": None})
    return parts, depth


def should_regenerate_gallery(index_json_path, output_html_path):
    """Sprawdza czy galeria powinna być wygenerowana ponownie."""
    if not os.path.exists(output_html_path):
        return True

    # Sprawdź czy template lub CSS się zmieniły
    template_files = ["gallery_template.html", "gallery_styles.css"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates")

    if not os.path.isdir(template_dir):
        alt_template_dir = "templates"
        if os.path.isdir(alt_template_dir):
            template_dir = alt_template_dir
        else:
            return True  # Jeśli nie znaleziono szablonów, regeneruj

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
        progress_callback(f"Generowanie galerii dla: {index_json_path}")

    try:
        with open(index_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if progress_callback:
            progress_callback(f"Błąd odczytu {index_json_path}: {e}")
        return None

    current_folder_abs_path = os.path.dirname(index_json_path)
    relative_path_from_scanned_root = os.path.relpath(
        current_folder_abs_path, scanned_root_path
    )

    current_gallery_html_dir = os.path.join(
        gallery_output_base_path,
        (
            relative_path_from_scanned_root
            if relative_path_from_scanned_root != "."
            else ""
        ),
    )
    os.makedirs(current_gallery_html_dir, exist_ok=True)

    output_html_file = os.path.join(current_gallery_html_dir, "index.html")

    # Użyj inteligentnego cachowania
    if os.path.exists(output_html_file) and not should_regenerate_gallery(
        index_json_path, output_html_file
    ):
        if progress_callback:
            progress_callback(f"Galeria {output_html_file} jest aktualna, pomijam.")
        return output_html_file

    template = template_env.get_template("gallery_template.html")

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

    # Subfolders - dodaj statystyki
    for entry in os.scandir(current_folder_abs_path):
        if entry.is_dir():
            if os.path.exists(os.path.join(entry.path, "index.json")):
                # Wczytaj statystyki z index.json podfolderu
                try:
                    with open(
                        os.path.join(entry.path, "index.json"), "r", encoding="utf-8"
                    ) as f:
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
                except:
                    template_data["subfolders"].append(
                        {
                            "name": entry.name,
                            "link": f"{entry.name}/index.html",
                            "total_size_readable": "0 B",
                            "file_count": 0,
                            "subdir_count": 0,
                        }
                    )

    # Files with previews - używaj bezpośrednich ścieżek
    for item in data.get("files_with_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"
        if item.get("preview_path_absolute"):
            copied_item["preview_relative_path"] = (
                f"file:///{item['preview_path_absolute']}"
            )

        # DODAJ KOLOR ARCHIWUM NA PODSTAWIE ROZSZERZENIA
        file_name = item.get("name", "")
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

        template_data["files_with_previews"].append(copied_item)

    # Files without previews
    for item in data.get("files_without_previews", []):
        copied_item = item.copy()
        copied_item["archive_link"] = f"file:///{item['path_absolute']}"

        # DODAJ KOLOR ARCHIWUM
        file_name = item.get("name", "")
        file_ext = os.path.splitext(file_name)[1].lower()
        copied_item["archive_color"] = config_manager.get_archive_color(file_ext)

        template_data["files_without_previews"].append(copied_item)

    # Other images - używaj bezpośrednich ścieżek
    for item in data.get("other_images", []):
        copied_item = item.copy()
        copied_item["file_link"] = f"file:///{item['path_absolute']}"
        if item.get("path_absolute"):
            copied_item["image_relative_path"] = f"file:///{item['path_absolute']}"
        template_data["other_images"].append(copied_item)

    try:
        html_content = template.render(template_data)
        with open(output_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        if progress_callback:
            progress_callback(f"Zapisano galerię: {output_html_file}")
    except Exception as e:
        if progress_callback:
            progress_callback(f"Błąd generowania HTML dla {index_json_path}: {e}")
        return None

    return output_html_file


def generate_full_gallery(scanned_root_path, gallery_cache_root_dir="."):
    """
    Generates the full gallery.
    scanned_root_path: The original directory that was scanned (e.g. W:/3Dsky/ARCHITECTURE)
    gallery_cache_root_dir: The base directory where all galleries are stored (e.g. _gallery_cache)
    """
    if not os.path.isdir(scanned_root_path):
        print(f"Error: Scanned root path {scanned_root_path} is not a directory.")
        return None

    sanitized_folder_name = sanitize_path_for_foldername(scanned_root_path)
    gallery_output_base_path = os.path.join(
        gallery_cache_root_dir, sanitized_folder_name
    )
    os.makedirs(gallery_output_base_path, exist_ok=True)

    # Copy CSS file to the root of this specific gallery's output
    # Assuming templates/gallery_styles.css exists relative to this script
    # For robustness, let's make template_dir an argument or discover it
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates")

    if not os.path.isdir(template_dir):
        print(f"Error: Template directory not found at {template_dir}")
        # Fallback if running from a different context (e.g. bundled app)
        # This might need adjustment based on how the app is packaged/run
        alt_template_dir = "templates"
        if os.path.isdir(alt_template_dir):
            template_dir = alt_template_dir
        else:
            print("Cannot locate templates directory.")
            return None

    env = Environment(loader=FileSystemLoader(template_dir))

    css_src_path = os.path.join(template_dir, "gallery_styles.css")
    css_dest_path = os.path.join(gallery_output_base_path, "gallery_styles.css")
    if os.path.exists(css_src_path):
        try:
            shutil.copy2(css_src_path, css_dest_path)
        except Exception as e:
            print(f"Could not copy gallery_styles.css: {e}")
    else:
        print(f"Warning: gallery_styles.css not found at {css_src_path}")

    root_gallery_html_path = None

    for dirpath, _, filenames in os.walk(scanned_root_path):
        if "index.json" in filenames:
            index_json_file = os.path.join(dirpath, "index.json")
            generated_html = process_single_index_json(
                index_json_file, scanned_root_path, gallery_output_base_path, env, print
            )
            if (
                dirpath == scanned_root_path and generated_html
            ):  # This is the root index.html for the gallery
                root_gallery_html_path = generated_html

    if root_gallery_html_path:
        print(f"Gallery generation complete. Root HTML at: {root_gallery_html_path}")
    else:
        print("Gallery generation failed or no index.json found at root.")
    return root_gallery_html_path


if __name__ == "__main__":
    # Test
    # Create dummy scanned structure first using scanner_logic.py's test
    import subprocess

    subprocess.run(
        [sys.executable, "scanner_logic.py"]
    )  # Run the test in scanner_logic.py

    test_scan_dir = "/tmp/test_scan_py_no_archive"  # Must match scanner_logic.py
    if not os.path.exists(os.path.join(test_scan_dir, "index.json")):
        print(
            f"Please run scanner_logic.py first to create test data in {test_scan_dir}"
        )
    else:
        print(f"Generating gallery for: {test_scan_dir}")
        gallery_cache = "_test_gallery_cache"
        os.makedirs(gallery_cache, exist_ok=True)

        # Ensure templates directory exists for standalone test
        if not os.path.exists("templates"):
            os.makedirs("templates")
        if not os.path.exists("templates/gallery_template.html"):
            with open("templates/gallery_template.html", "w") as f:
                f.write(
                    "<html><body><h1>Test Template for {{ current_folder_display_name }}</h1></body></html>"
                )  # Minimal template
        if not os.path.exists("templates/gallery_styles.css"):
            with open("templates/gallery_styles.css", "w") as f:
                f.write("/* Test CSS */ body { background-color: #eee; }")

        root_html = generate_full_gallery(
            test_scan_dir, gallery_cache_root_dir=gallery_cache
        )
        if root_html:
            print(f"Test gallery generated. Open: file://{os.path.abspath(root_html)}")
