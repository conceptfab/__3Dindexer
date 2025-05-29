Zmiana w pliku scanner_logic.py
W funkcji find_matching_preview_for_file, zastąp całą sekcję uczenia tym kodem:
pythondef find_matching_preview_for_file(base_filename, image_files_in_folder, learning_data=None):
    """
    Przywrócona oryginalna funkcja + RZECZYWISTE wzorce (nie mapowania!)
    """
    logger.debug(f"🔍 Szukam podglądu dla: '{base_filename}'")

    if not base_filename:
        logger.warning("❌ Przekazano pustą nazwę")
        return None

    # 1. NAJPIERW: Zastosuj WZORCE z uczenia (nie mapowania!)
    if learning_data:
        learned_match = apply_smart_patterns(base_filename, image_files_in_folder, learning_data)
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

def apply_smart_patterns(base_filename, image_files_in_folder, learning_data):
    """
    RZECZYWISTE wyciąganie wzorców - nie mapowania!
    """
    base_lower = base_filename.lower().strip()
    
    # Analizuj wszystkie przykłady uczenia, aby znaleźć WZORCE
    separator_patterns = analyze_separator_patterns(learning_data)
    space_patterns = analyze_space_patterns(learning_data)
    suffix_patterns = analyze_suffix_patterns(learning_data)
    
    logger.debug(f"📚 Znalezione wzorce - separatory: {len(separator_patterns)}, spacje: {len(space_patterns)}, sufiksy: {len(suffix_patterns)}")
    
    # Zastosuj wzorce separatorów
    for pattern in separator_patterns:
        if pattern['confidence'] >= 0.5:  # Tylko pewne wzorce
            modified_name = apply_separator_pattern(base_lower, pattern)
            if modified_name != base_lower:
                match = find_image_by_basename(modified_name, image_files_in_folder)
                if match:
                    logger.info(f"🎓 WZORZEC SEPARATORA ({pattern['from']}→{pattern['to']}): '{base_filename}' ↔ '{os.path.basename(match)}'")
                    return match
    
    # Zastosuj wzorce spacji
    for pattern in space_patterns:
        if pattern['confidence'] >= 0.5:
            modified_name = apply_space_pattern(base_lower, pattern)
            if modified_name != base_lower:
                match = find_image_by_basename(modified_name, image_files_in_folder)
                if match:
                    logger.info(f"🎓 WZORZEC SPACJI: '{base_filename}' ↔ '{os.path.basename(match)}'")
                    return match
    
    return None

def analyze_separator_patterns(learning_data):
    """Analizuje wzorce separatorów z przykładów"""
    patterns = {}
    
    for entry in learning_data:
        archive_base = entry.get("archive_basename", "").lower().strip()
        image_base = entry.get("image_basename", "").lower().strip()
        
        if not archive_base or not image_base:
            continue
            
        # Sprawdź czy to wzorzec _ → .
        if '_' in archive_base and '.' in image_base:
            archive_clean = archive_base.replace('_', '')
            image_clean = image_base.replace('.', '')
            if archive_clean == image_clean:
                key = "_to_dot"
                if key not in patterns:
                    patterns[key] = {'from': '_', 'to': '.', 'count': 0, 'examples': []}
                patterns[key]['count'] += 1
                patterns[key]['examples'].append((archive_base, image_base))
        
        # Sprawdź inne wzorce separatorów...
        # Możesz dodać więcej wzorców tutaj
    
    # Oblicz confidence dla każdego wzorca
    total_examples = len(learning_data)
    result = []
    for pattern_data in patterns.values():
        confidence = pattern_data['count'] / max(total_examples, 1)
        result.append({
            'from': pattern_data['from'],
            'to': pattern_data['to'],
            'confidence': confidence,
            'count': pattern_data['count']
        })
    
    return result

def analyze_space_patterns(learning_data):
    """Analizuje wzorce spacji"""
    patterns = {}
    
    for entry in learning_data:
        archive_base = entry.get("archive_basename", "").lower().strip()
        image_base = entry.get("image_basename", "").lower().strip()
        
        if not archive_base or not image_base:
            continue
            
        # Sprawdź wzorzec _ → spacja
        if '_' in archive_base and ' ' in image_base:
            archive_as_spaces = archive_base.replace('_', ' ')
            if archive_as_spaces == image_base:
                key = "underscore_to_space"
                if key not in patterns:
                    patterns[key] = {'pattern': key, 'count': 0}
                patterns[key]['count'] += 1
    
    # Oblicz confidence
    total_examples = len(learning_data)
    result = []
    for pattern_data in patterns.values():
        confidence = pattern_data['count'] / max(total_examples, 1)
        result.append({
            'pattern': pattern_data['pattern'],
            'confidence': confidence,
            'count': pattern_data['count']
        })
    
    return result

def analyze_suffix_patterns(learning_data):
    """Analizuje wzorce sufiksów"""
    # Implementacja dla sufiksów - na razie pusta
    return []

def apply_separator_pattern(base_name, pattern):
    """Stosuje wzorzec separatora"""
    if pattern['from'] == '_' and pattern['to'] == '.':
        return base_name.replace('_', '.')
    return base_name

def apply_space_pattern(base_name, pattern):
    """Stosuje wzorzec spacji"""
    if pattern['pattern'] == 'underscore_to_space':
        return base_name.replace('_', ' ')
    return base_name

def find_image_by_basename(target_basename, image_files_in_folder):
    """Znajduje obraz po basename"""
    for img_path in image_files_in_folder:
        img_name = os.path.basename(img_path)
        img_base, img_ext = os.path.splitext(img_name)
        if img_ext.lower() in IMAGE_EXTENSIONS:
            if img_base.lower().strip() == target_basename:
                return img_path
    return None
Główne zmiany:

Usunięte mapowania - żadne exact_mappings[archive_base] = image_base
Rzeczywiste wzorce - analizuje przykłady i wyciąga zasady (np. "_ zamienia się na ." w X% przypadków)
Confidence - stosuje tylko wzorce z odpowiednią pewnością (≥50%)
Generalizacja - dla 328995_55c5cfe0d1a6d.rar i 328995.55c5cfe0d1a6d.jpeg wyciągnie wzorzec "_ → ." i zastosuje go do innych plików

Teraz system naprawdę uczy się wzorców zamiast zapamiętywać konkretne nazwy plików!