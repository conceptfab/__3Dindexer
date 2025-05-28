Zmiana w pliku scanner_logic.py
Przywróć ORYGINALNĄ funkcję find_matching_preview_for_file i dodaj tylko inteligentną analizę wzorców:
pythondef extract_learning_patterns(learning_data):
    """Analizuje dane uczenia i wyciąga proste wzorce"""
    patterns = {
        'separator_changes': [],  # _ na . itp.
        'suffix_additions': [],   # dodatkowe części
        'exact_mappings': {}      # dokładne mapowania
    }
    
    for match_entry in learning_data:
        archive_base = match_entry.get("archive_basename", "").lower().strip()
        image_base = match_entry.get("image_basename", "").lower().strip()
        
        if not archive_base or not image_base:
            continue
            
        # Dokładne mapowanie
        patterns['exact_mappings'][archive_base] = image_base
        
        # Analiza separatorów: _ vs .
        if '_' in archive_base and '.' in image_base:
            archive_clean = archive_base.replace('_', '')
            image_clean = image_base.replace('.', '')
            if archive_clean == image_clean:
                patterns['separator_changes'].append({
                    'from': '_',
                    'to': '.',
                    'example_archive': archive_base,
                    'example_image': image_base
                })
        
        # Analiza dodatkowych części (space vs _)
        if ' ' in image_base and '_' in archive_base:
            archive_normalized = archive_base.replace('_', ' ')
            if archive_normalized.strip() == image_base.strip():
                patterns['suffix_additions'].append({
                    'pattern': 'underscore_to_space',
                    'example_archive': archive_base,
                    'example_image': image_base
                })
    
    logger.info(f"📚 Wyciągnięto wzorce: {len(patterns['exact_mappings'])} dokładnych, {len(patterns['separator_changes'])} separatorów, {len(patterns['suffix_additions'])} przestrzeni")
    return patterns

def apply_learned_patterns(base_filename, image_files_in_folder, patterns):
    """Stosuje TYLKO proste wzorce z uczenia"""
    base_lower = base_filename.lower().strip()
    
    # 1. Dokładne mapowanie
    if base_lower in patterns['exact_mappings']:
        target_image_base = patterns['exact_mappings'][base_lower]
        for img_path in image_files_in_folder:
            img_name = os.path.basename(img_path)
            img_base, img_ext = os.path.splitext(img_name)
            if img_ext.lower() in IMAGE_EXTENSIONS:
                if img_base.lower().strip() == target_image_base:
                    logger.info(f"🎓 DOKŁADNE MAPOWANIE: '{base_filename}' ↔ '{img_name}'")
                    return img_path
    
    # 2. Wzorce separatorów (np. _ na .)
    for pattern in patterns['separator_changes']:
        if pattern['from'] == '_' and pattern['to'] == '.':
            # Zamień _ na . w nazwie archiwum
            modified_base = base_lower.replace('_', '.')
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    if img_base.lower().strip() == modified_base:
                        logger.info(f"🎓 WZORZEC SEPARATORA: '{base_filename}' ↔ '{img_name}' (_ na .)")
                        return img_path
    
    # 3. Wzorce przestrzeni (_ na spacja)
    for pattern in patterns['suffix_additions']:
        if pattern['pattern'] == 'underscore_to_space':
            modified_base = base_lower.replace('_', ' ').strip()
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    if img_base.lower().strip() == modified_base:
                        logger.info(f"🎓 WZORZEC PRZESTRZENI: '{base_filename}' ↔ '{img_name}' (_ na spacja)")
                        return img_path
    
    return None

def find_matching_preview_for_file(base_filename, image_files_in_folder, learning_data=None):
    """
    PRZYWRÓCONA oryginalna funkcja + inteligentne wzorce
    """
    logger.debug(f"🔍 Szukam podglądu dla: '{base_filename}'")

    if not base_filename:
        logger.warning("❌ Przekazano pustą nazwę")
        return None

    # 1. NAJPIERW: Zastosuj wzorce z uczenia
    if learning_data:
        patterns = extract_learning_patterns(learning_data)
        learned_match = apply_learned_patterns(base_filename, image_files_in_folder, patterns)
        if learned_match:
            return learned_match

    # 2. ORYGINALNY ALGORYTM (który działał!)
    normalized_base_filename = base_filename.lower().strip()
    
    # Podstawowe warianty
    name_variants = set([normalized_base_filename])
    name_variants.add(normalized_base_filename.replace("_", " "))
    name_variants.add(normalized_base_filename.replace(" ", "_"))
    name_variants.add(normalized_base_filename.replace("-", " "))
    name_variants.add(normalized_base_filename.replace(" ", "-"))
    name_variants.add(normalized_base_filename.replace("_", "-"))
    name_variants.add(normalized_base_filename.replace("-", "_"))
    
    # Dodaj warianty z typowymi sufiksami
    extended_variants = set(name_variants)
    common_suffixes = ["001", "preview", "thumb", "1", "2", "3", "0", "cover"]
    for variant in name_variants:
        for separator in ["_", "-", " "]:
            for suffix in common_suffixes:
                extended_variants.add(variant + separator + suffix)
    
    # Sprawdź dokładne dopasowania
    for img_full_path in image_files_in_folder:
        img_name = os.path.basename(img_full_path)
        img_base, img_ext = os.path.splitext(img_name)
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue
            
        img_base_lower = img_base.lower().strip()
        if img_base_lower in extended_variants:
            logger.info(f"✅ Dopasowanie: '{base_filename}' ↔ '{img_name}'")
            return img_full_path
    
    # Sprawdź prefiksy
    for img_full_path in image_files_in_folder:
        img_name = os.path.basename(img_full_path)
        img_base, img_ext = os.path.splitext(img_name)
        if img_ext.lower() not in IMAGE_EXTENSIONS:
            continue
            
        img_base_lower = img_base.lower().strip()
        for variant in name_variants:
            if len(variant) >= 3 and img_base_lower.startswith(variant):
                remaining = img_base_lower[len(variant):]
                if not remaining or remaining[0] in [' ', '_', '-'] or remaining[0].isdigit():
                    logger.info(f"✅ Dopasowanie prefiksu: '{base_filename}' ↔ '{img_name}'")
                    return img_full_path

    logger.debug(f"❌ Nie znaleziono podglądu dla: '{base_filename}'")
    return None
Główne zmiany:

Przywróciłem oryginalny algorytm - ten który działał dla prostych przypadków
Dodałem tylko proste wzorce z danych uczenia:

Dokładne mapowania (archive_basename → image_basename)
Zamiana _ na . (328995_55c5cfe0d1a6d → 328995.55c5cfe0d1a6d)
Zamiana _ na spację (dla przypadków Porsche)


Wzorce działają PRZED oryginalnym algorytmem, więc nie psują istniejących dopasowań

Teraz system powinien:

Nadal działać dla wszystkich prostych przypadków jak wcześniej
DODATKOWO stosować nauczone wzorce dla skomplikowanych przypadków
Wyciągać wnioski z przykładów zamiast je zapamiętywać

Sprawdź czy teraz działa dla Twoich przykładów!