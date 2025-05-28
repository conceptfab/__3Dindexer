1. Zmiany w scanner_logic.py
Plik: scanner_logic.py
Problem: Timeout mechanizm może powodować zawieszenia przy skomplikowanych strukturach folderów.
pythondef process_folder(folder_path, progress_callback=None):
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

    # RESZTA FUNKCJI POZOSTAJE BEZ ZMIAN...
    # [kod przetwarzania plików i tworzenia index.json]
2. Zmiany w gallery_generator.py
Plik: gallery_generator.py
Problem: Błędy przy kopiowaniu CSS i tworzeniu plików HTML.
pythondef process_single_index_json(
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
    
    # ULEPSZONE TWORZENIE KATALOGU
    try:
        os.makedirs(current_gallery_html_dir, exist_ok=True)
        
        # Sprawdź czy katalog został utworzony i jest zapisywalny
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

    # Użyj inteligentnego cachowania
    if os.path.exists(output_html_file) and not should_regenerate_gallery(
        index_json_path, output_html_file
    ):
        print(f"ℹ️ Galeria {output_html_file} jest aktualna, pomijam.")
        if progress_callback:
            progress_callback(f"ℹ️ Galeria {output_html_file} jest aktualna, pomijam.")
        return output_html_file

    print("🔄 Przygotowywanie danych do szablonu...")
    
    # SPRAWDZENIE SZABLONU PRZED UŻYCIEM
    try:
        template = template_env.get_template("gallery_template.html")
        print("✅ Szablon załadowany pomyślnie")
    except Exception as e:
        print(f"❌ Błąd ładowania szablonu: {e}")
        if progress_callback:
            progress_callback(f"❌ Błąd ładowania szablonu: {e}")
        return None

    # [RESZTA KODU PRZETWARZANIA DANYCH...]

    print("📝 Generowanie HTML...")
    try:
        print(f"📊 Dane do szablonu: {len(template_data['files_with_previews'])} plików z podglądami, {len(template_data['files_without_previews'])} bez podglądów, {len(template_data['other_images'])} innych obrazów")
        print("🔄 Renderowanie szablonu...")
        html_content = template.render(template_data)
        print(f"✅ Szablon wyrenderowany, rozmiar: {len(html_content)} bajtów")
        
        # ULEPSZONE SPRAWDZENIE I ZAPIS HTML
        if not html_content or len(html_content) < 100:
            raise ValueError("Wygenerowany HTML jest pusty lub zbyt krótki")
        
        print(f"💾 Zapisuję plik HTML: {output_html_file}")
        
        # Dodatkowe sprawdzenia przed zapisem
        output_dir = os.path.dirname(output_html_file)
        if not os.path.exists(output_dir):
            print(f"📂 Tworzę katalog: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # ATOMOWY ZAPIS - zapisz do pliku tymczasowego, potem przenieś
        temp_html_file = output_html_file + ".tmp"
        try:
            with open(temp_html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Sprawdź czy plik tymczasowy został zapisany poprawnie
            if os.path.exists(temp_html_file) and os.path.getsize(temp_html_file) > 0:
                # Przenieś z tymczasowego do docelowego
                if os.path.exists(output_html_file):
                    os.remove(output_html_file)
                os.rename(temp_html_file, output_html_file)
                print(f"✅ Zapisano galerię: {output_html_file}")
            else:
                raise IOError("Plik tymczasowy nie został zapisany poprawnie")
                
        except Exception as write_error:
            # Usuń plik tymczasowy w przypadku błędu
            if os.path.exists(temp_html_file):
                try:
                    os.remove(temp_html_file)
                except:
                    pass
            raise write_error
            
        # Sprawdź czy plik został zapisany
        if os.path.exists(output_html_file):
            file_size = os.path.getsize(output_html_file)
            print(f"✅ Plik zapisany, rozmiar: {file_size} bajtów")
            
            # Dodatkowa walidacja HTML
            if file_size < 100:
                raise ValueError(f"Zapisany plik HTML jest zbyt mały: {file_size} bajtów")
        else:
            raise IOError("Plik nie został zapisany mimo braku błędów!")
            
        if progress_callback:
            progress_callback(f"✅ Zapisano galerię: {output_html_file}")
            
    except Exception as e:
        print(f"❌ Błąd generowania HTML dla {index_json_path}: {e}")
        print(f"📊 Stan template_data: {list(template_data.keys()) if 'template_data' in locals() else 'template_data nie istnieje'}")
        if progress_callback:
            progress_callback(f"❌ Błąd generowania HTML dla {index_json_path}: {e}")
        return None

    return output_html_file
3. Zmiany w generate_full_gallery
Plik: gallery_generator.py
Problem: CSS nie jest kopiowany poprawnie.
pythondef generate_full_gallery(scanned_root_path, gallery_cache_root_dir="."):
    """
    Generates the full gallery.
    scanned_root_path: The original directory that was scanned (e.g. W:/3Dsky/ARCHITECTURE)
    gallery_cache_root_dir: The base directory where all galleries are stored (e.g. _gallery_cache)
    """
    print(f"🚀 Rozpoczynam generowanie galerii dla: {scanned_root_path}")
    
    if not os.path.isdir(scanned_root_path):
        print(f"❌ Błąd: Ścieżka {scanned_root_path} nie jest katalogiem.")
        return None

    sanitized_folder_name = sanitize_path_for_foldername(scanned_root_path)
    gallery_output_base_path = os.path.join(
        gallery_cache_root_dir, sanitized_folder_name
    )
    print(f"📂 Katalog wyjściowy galerii: {gallery_output_base_path}")
    
    # ULEPSZONE TWORZENIE KATALOGÓW
    try:
        os.makedirs(gallery_output_base_path, exist_ok=True)
        
        # Sprawdź uprawnienia
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

    # SPRAWDZENIE SZABLONÓW
    template_html_path = os.path.join(template_dir, "gallery_template.html")
    if not os.path.exists(template_html_path):
        print(f"❌ Nie znaleziono szablonu HTML: {template_html_path}")
        return None

    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        # Test ładowania szablonu
        test_template = env.get_template("gallery_template.html")
        print("✅ Zainicjalizowano środowisko szablonów")
    except Exception as e:
        print(f"❌ Błąd inicjalizacji szablonów: {e}")
        return None

    # ULEPSZONE KOPIOWANIE CSS
    css_src_path = os.path.join(template_dir, "gallery_styles.css")
    css_dest_path = os.path.join(gallery_output_base_path, "gallery_styles.css")
    
    print(f"📄 Kopiowanie CSS z {css_src_path} do {css_dest_path}")
    
    if os.path.exists(css_src_path):
        try:
            # Sprawdź czy plik CSS nie jest pusty
            css_size = os.path.getsize(css_src_path)
            if css_size == 0:
                print(f"⚠️ Plik CSS jest pusty: {css_src_path}")
            else:
                print(f"📄 Rozmiar pliku CSS: {css_size} bajtów")
            
            # Kopiuj z zachowaniem metadanych
            shutil.copy2(css_src_path, css_dest_path)
            
            # Sprawdź czy skopiowano poprawnie
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
    
    # ULEPSZONE PRZETWARZANIE Z LEPSZĄ OBSŁUGĄ BŁĘDÓW
    for dirpath, dirnames, filenames in os.walk(scanned_root_path):
        # Pomijaj linki symboliczne
        if os.path.islink(dirpath):
            print(f"⚠️ Pomijam link symboliczny: {dirpath}")
            continue
            
        if "index.json" in filenames:
            index_json_file = os.path.join(dirpath, "index.json")
            print(f"📄 Przetwarzanie: {index_json_file}")
            
            try:
                # Sprawdź czy plik index.json nie jest uszkodzony
                with open(index_json_file, 'r', encoding='utf-8') as f:
                    json.load(f)  # Test czy JSON jest poprawny
                
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
        
        # DODATKOWA WALIDACJA GŁÓWNEGO PLIKU
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
Kluczowe zmiany:

Scanner Logic: Usunięto timeout threading, dodano sprawdzanie linków symbolicznych, uproszczono mechanizm skanowania
Gallery Generator: Dodano atomowy zapis plików, lepsze sprawdzanie CSS, walidację HTML
Lepsze logowanie: Więcej szczegółowych komunikatów o błędach
Obsługa błędów: Bardziej granularne sprawdzanie na każdym etapie

Te zmiany powinny znacznie poprawić stabilność obu modułów i zmniejszyć problemy z zawieszaniem się oraz pustymi plikami HTML.