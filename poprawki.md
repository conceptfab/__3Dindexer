Przeanalizowałem Twój kod i widzę problem z dopasowywaniem plików z podglądami. Obecna funkcja find_matching_preview_for_file jest zbyt restrykcyjna i nie obsługuje przypadków, gdzie:

Podkreślenia (_) w nazwach archiwów są zastępowane spacjami w obrazach
Obrazy mają dodatkowe cyfry lub tekst na końcu nazwy
Różne kombinacje separatorów i dodatkowych znaków

Zmiany w kodzie
Zmiana w pliku scanner_logic.py
pythondef find_matching_preview_for_file(base_filename, image_files_in_folder):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    Dopasowuje na podstawie nazwy bazowej z obsługą różnych wariantów:
    - zamiana podkreśleń na spacje i odwrotnie
    - dodatkowe cyfry i tekst na końcu nazwy obrazu
    - różne separatory (_, -, spacja)
    - ignorowanie wielkości liter
    """
    if not base_filename:
        return None
        
    base_name = base_filename.lower().strip()
    
    # Twórz różne warianty nazwy bazowej
    name_variants = set()
    
    # Podstawowy wariant
    name_variants.add(base_name)
    
    # Zamiana podkreśleń na spacje i odwrotnie
    name_variants.add(base_name.replace('_', ' '))
    name_variants.add(base_name.replace(' ', '_'))
    name_variants.add(base_name.replace('-', ' '))
    name_variants.add(base_name.replace(' ', '-'))
    name_variants.add(base_name.replace('_', '-'))
    name_variants.add(base_name.replace('-', '_'))
    
    # Usuń wielokrotne spacje/podkreślenia
    cleaned_variants = set()
    for variant in name_variants:
        # Normalizuj wielokrotne separatory
        import re
        normalized = re.sub(r'[\s_-]+', ' ', variant).strip()
        cleaned_variants.add(normalized)
        cleaned_variants.add(normalized.replace(' ', '_'))
        cleaned_variants.add(normalized.replace(' ', '-'))
    
    name_variants.update(cleaned_variants)
    
    # Dodaj warianty z typowymi sufiksami
    extended_variants = set(name_variants)
    for variant in name_variants:
        for separator in ['_', '-', ' ', '']:
            for suffix in ['001', 'preview', 'thumb', '1', '2', '3', '0']:
                if separator or suffix.isdigit():
                    extended_variants.add(variant + separator + suffix)
    
    logger.debug(f"Szukam podglądu dla '{base_filename}' z {len(extended_variants)} wariantami")
    
    for img_path in image_files_in_folder:
        img_name = os.path.basename(img_path)
        img_base, img_ext = os.path.splitext(img_name)
        
        # Sprawdź czy to obsługiwane rozszerzenie obrazu
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue
            
        img_base_clean = img_base.lower().strip()
        
        # Dokładne dopasowanie
        if img_base_clean in extended_variants:
            logger.debug(f"✅ Dokładne dopasowanie: '{img_name}' dla '{base_filename}'")
            return img_path
        
        # Sprawdzenie czy obraz zaczyna się od któregoś z wariantów
        for variant in name_variants:
            if len(variant) >= 3:  # Minimalna długość dla bezpiecznego dopasowania
                # Obraz zaczyna się od wariantu + separator/cyfra
                if (img_base_clean.startswith(variant + ' ') or 
                    img_base_clean.startswith(variant + '_') or 
                    img_base_clean.startswith(variant + '-') or
                    (img_base_clean.startswith(variant) and 
                     len(img_base_clean) > len(variant) and 
                     img_base_clean[len(variant):][0].isdigit())):
                    logger.debug(f"✅ Dopasowanie z prefiksem: '{img_name}' dla '{base_filename}' (wariant: '{variant}')")
                    return img_path
    
    logger.debug(f"❌ Nie znaleziono podglądu dla: '{base_filename}'")
    return None
Zmiana w pliku scanner_logic.py - dodanie funkcji debugowej
pythondef debug_name_matching(base_filename, image_files_in_folder):
    """
    Funkcja debugowa do sprawdzenia wszystkich możliwych dopasowań.
    Użyj do diagnozowania problemów z dopasowywaniem nazw.
    """
    print(f"\n🔍 DEBUG dla: '{base_filename}'")
    
    base_name = base_filename.lower().strip()
    
    # Twórz warianty tak samo jak w głównej funkcji
    name_variants = {base_name}
    name_variants.add(base_name.replace('_', ' '))
    name_variants.add(base_name.replace(' ', '_'))
    name_variants.add(base_name.replace('-', ' '))
    name_variants.add(base_name.replace(' ', '-'))
    
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
                if (img_base_clean.startswith(variant + ' ') or 
                    img_base_clean.startswith(variant + '_') or 
                    img_base_clean.startswith(variant + '-')):
                    print(f"   ✅ PREFIKS dopasowanie z wariantem: '{variant}'")
                elif (img_base_clean.startswith(variant) and 
                      len(img_base_clean) > len(variant) and 
                      img_base_clean[len(variant):][0].isdigit()):
                    print(f"   ✅ PREFIKS+CYFRA dopasowanie z wariantem: '{variant}'")
Zmiana w pliku scanner_logic.py - aktualizacja funkcji process_folder
pythondef process_folder(folder_path, progress_callback=None):
    """
    Przetwarza pojedynczy folder: zbiera informacje i generuje index.json.
    Rekursywnie wywołuje się dla podfolderów.
    """
    logger.info(f"Rozpoczęcie przetwarzania folderu: {folder_path}")

    if progress_callback:
        progress_callback(f"Przetwarzanie folderu: {folder_path}")

    # DODAJ DEBUG MATCHING dla konkretnych problemowych plików (opcjonalnie)
    # debug_name_matching("Volvo_S90", ["/path/to/Volvo s90.jpg"])

    # ... reszta funkcji pozostaje bez zmian do momentu przetwarzania plików ...

    for file_name in other_filenames:
        file_path = os.path.join(folder_path, file_name)
        file_basename, _ = os.path.splitext(file_name)  # file_basename bez rozszerzenia

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

        # ULEPSZONE dopasowywanie podglądu
        preview_file_path = find_matching_preview_for_file(
            file_basename, full_path_image_files
        )

        if preview_file_path:
            file_info["preview_found"] = True
            file_info["preview_name"] = os.path.basename(preview_file_path)
            file_info["preview_path_absolute"] = os.path.abspath(preview_file_path)
            index_data["files_with_previews"].append(file_info)
            found_previews_paths.add(preview_file_path)
            logger.info(f"✅ Dopasowano: '{file_name}' ↔ '{os.path.basename(preview_file_path)}'")
        else:
            file_info["preview_found"] = False
            index_data["files_without_previews"].append(file_info)
            logger.debug(f"❌ Brak podglądu dla: '{file_name}'")

    # ... reszta funkcji pozostaje bez zmian ...
Podsumowanie zmian
Główne usprawnienia w funkcji find_matching_preview_for_file:

Normalizacja separatorów - automatyczna zamiana _, -, i spacji między sobą
Dopasowanie prefiksowe - obraz może mieć dodatkowy tekst/cyfry na końcu
Lepsza obsługa wariantów - więcej kombinacji nazw bazowych
Funkcja debugowa - do łatwego testowania dopasowań

