🔧 Poprawka w pliku scanner_logic.py
Zmiana w funkcji find_matching_preview_for_file
pythondef find_matching_preview_for_file(base_filename, image_files_in_folder):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    Dopasowuje na podstawie identycznej nazwy bazowej (bez rozszerzenia),
    ignorując wielkość liter i obsługując wszystkie warianty rozszerzeń.
    """
    # UWAGA: base_filename już jest nazwą bazową bez rozszerzenia!
    # Nie rób ponownie os.path.splitext()
    base_name = base_filename.lower().strip()
    
    # Lista możliwych wzorców dla nazwy bazowej
    possible_patterns = [
        base_name,  # dokładna nazwa
        base_name + "_001",  # z sufiksem _001
        base_name + "_preview",  # z sufiksem _preview
        base_name + "_thumb",  # z sufiksem _thumb
    ]
    
    # Dodaj wzorce z różnymi separatorami
    for separator in ["_", "-", " "]:
        for suffix in ["001", "preview", "thumb", "1"]:
            pattern = base_name + separator + suffix
            if pattern not in possible_patterns:
                possible_patterns.append(pattern)
    
    logger.debug(
        f"Szukam podglądu dla '{base_filename}' z wzorcami: {possible_patterns}"
    )
    
    for img_path in image_files_in_folder:
        img_name = os.path.basename(img_path)
        img_base, img_ext = os.path.splitext(img_name)
        
        # Sprawdź czy to obsługiwane rozszerzenie obrazu
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue
            
        img_base_clean = img_base.lower().strip()
        
        # Sprawdź wszystkie możliwe wzorce
        for pattern in possible_patterns:
            if img_base_clean == pattern:
                logger.debug(
                    f"✅ Dopasowano podgląd: '{img_name}' dla '{base_filename}' (wzorzec: '{pattern}')"
                )
                return img_path
    
    logger.debug(f"❌ Nie znaleziono podglądu dla: '{base_filename}'")
    return None
Zmiana w funkcji process_folder - gdzie wywołujemy funkcję
Problem był też w tym, że przekazywaliśmy file_basename (który już jest bez rozszerzenia), ale funkcja robiła ponownie splitext(). Sprawdź tę część w funkcji process_folder:
pythonfor file_name in other_filenames:
    file_path = os.path.join(folder_path, file_name)
    file_basename, _ = os.path.splitext(file_name)  # To już jest nazwa bez rozszerzenia

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

    # TUTAJ PRZEKAZUJEMY file_basename (już bez rozszerzenia!)
    preview_file_path = find_matching_preview_for_file(
        file_basename, full_path_image_files  # file_basename to np. "dokument" dla "dokument.pdf"
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