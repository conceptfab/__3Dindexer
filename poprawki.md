Zmiany w pliku scanner_logic.py
Zmiana w funkcji find_matching_preview_for_file
Problem: Funkcja nie uwzględnia wszystkich możliwych wariantów nazw plików i rozszerzeń.
pythondef find_matching_preview_for_file(base_filename, image_files_in_folder):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku.
    Dopasowuje na podstawie identycznej nazwy bazowej (bez rozszerzenia),
    ignorując wielkość liter i obsługując wszystkie warianty rozszerzeń.
    """
    base_name = os.path.splitext(base_filename)[0].lower().strip()
    
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
    
    logger.debug(f"Szukam podglądu dla '{base_filename}' z wzorcami: {possible_patterns}")
    
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
                logger.debug(f"✅ Dopasowano podgląd: '{img_name}' dla '{base_filename}' (wzorzec: '{pattern}')")
                return img_path
    
    logger.debug(f"❌ Nie znaleziono podglądu dla: '{base_filename}'")
    return None
Zmiana w stałej IMAGE_EXTENSIONS
Problem: Brak obsługi niektórych formatów obrazów i niejednoznaczności z JPEG.
python# Rozszerzona lista rozszerzeń obrazów z obsługą różnych wariantów
IMAGE_EXTENSIONS = (
    ".jpg", ".jpeg", ".jpe", ".jfif",  # JPEG i warianty
    ".png", ".apng",  # PNG i animowane PNG
    ".gif",  # GIF
    ".bmp", ".dib",  # Bitmap
    ".webp",  # WebP
    ".tiff", ".tif",  # TIFF
    ".svg", ".svgz",  # SVG
    ".ico",  # Ikony
    ".avif",  # AVIF (nowoczesny format)
    ".heic", ".heif",  # HEIC/HEIF (Apple)
)
Dodatkowa funkcja pomocnicza dla lepszego logowania
pythondef log_file_matching_debug(folder_path, progress_callback=None):
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
        image_files = [f for f in all_files if any(f.lower().endswith(ext) for ext in IMAGE_EXTENSIONS)]
        other_files = [f for f in all_files if f not in image_files and f.lower() != "index.json"]
        
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
                logger.info(f"✅ DOPASOWANIE: '{other_file}' ↔ '{os.path.basename(match)}'")
                if progress_callback:
                    progress_callback(f"Dopasowano: {other_file} ↔ {os.path.basename(match)}")
            else:
                logger.info(f"❌ BRAK: '{other_file}' (szukano dla '{base_name}')")
                if progress_callback:
                    progress_callback(f"Brak podglądu dla: {other_file}")
        
        logger.info(f"📊 PODSUMOWANIE: {matches_found}/{len(other_files)} plików ma podgląd")
        
    except Exception as e:
        logger.error(f"Błąd podczas debugowania: {e}")
Zmiana w funkcji process_folder - dodanie debugowania
Dodaj wywołanie funkcji debugowej przed główną logiką:
pythondef process_folder(folder_path, progress_callback=None):
    """
    Przetwarza pojedynczy folder: zbiera informacje i generuje index.json.
    Rekursywnie wywołuje się dla podfolderów.
    """
    logger.info(f"Rozpoczęcie przetwarzania folderu: {folder_path}")

    if progress_callback:
        progress_callback(f"Przetwarzanie folderu: {folder_path}")

    # DODAJ DEBUG MATCHING (opcjonalnie, tylko dla problemów)
    # log_file_matching_debug(folder_path, progress_callback)

    # ... reszta funkcji pozostaje bez zmian ...