Zmiany w pliku scanner_logic.py
Zmiana w funkcji find_matching_preview_for_file
pythondef extract_learning_patterns(learning_data):
    """Analizuje dane uczenia i wyciąga wzorce dopasowania"""
    patterns = {
        'exact_match': [],
        'suffix_patterns': [],
        'prefix_patterns': [],
        'transformation_rules': []
    }
    
    for match_entry in learning_data:
        archive_basename = match_entry.get("archive_basename", "").lower().strip()
        image_basename = match_entry.get("image_basename", "").lower().strip()
        
        if not archive_basename or not image_basename:
            continue
            
        # 1. Dokładne dopasowanie (po usunięciu znaków specjalnych)
        archive_clean = re.sub(r'[_\-\s\.]+', '', archive_basename)
        image_clean = re.sub(r'[_\-\s\.]+', '', image_basename)
        if archive_clean == image_clean:
            patterns['exact_match'].append({
                'archive_pattern': archive_basename,
                'image_pattern': image_basename,
                'type': 'exact_clean'
            })
            continue
            
        # 2. Wzorce sufiksów - obraz ma dodatkowy sufiks
        if image_basename.startswith(archive_basename):
            suffix = image_basename[len(archive_basename):].strip('_- ')
            if suffix:
                patterns['suffix_patterns'].append({
                    'base_pattern': archive_basename,
                    'suffix': suffix,
                    'type': 'image_has_suffix'
                })
                
        # 3. Wzorce prefiksów - archiwum ma dodatkowy prefiks
        elif archive_basename.startswith(image_basename):
            prefix = archive_basename[len(image_basename):].strip('_- ')
            if prefix:
                patterns['prefix_patterns'].append({
                    'base_pattern': image_basename,
                    'prefix': prefix,
                    'type': 'archive_has_prefix'
                })
                
        # 4. Transformacje - różne separatory, dodatkowe elementy
        else:
            # Sprawdź czy po normalizacji separatorów pasują
            archive_normalized = re.sub(r'[_\-\s]+', '_', archive_basename)
            image_normalized = re.sub(r'[_\-\s]+', '_', image_basename)
            
            # Znajdź wspólną część
            common_parts = []
            archive_parts = archive_normalized.split('_')
            image_parts = image_normalized.split('_')
            
            for arch_part in archive_parts:
                for img_part in image_parts:
                    if len(arch_part) > 3 and len(img_part) > 3:
                        if arch_part == img_part or arch_part in img_part or img_part in arch_part:
                            common_parts.append((arch_part, img_part))
                            
            if common_parts:
                patterns['transformation_rules'].append({
                    'archive_pattern': archive_basename,
                    'image_pattern': image_basename,
                    'common_parts': common_parts,
                    'type': 'partial_match'
                })
    
    logger.info(f"📚 Wyciągnięto wzorce z danych uczenia:")
    logger.info(f"  - Dokładne dopasowania: {len(patterns['exact_match'])}")
    logger.info(f"  - Wzorce sufiksów: {len(patterns['suffix_patterns'])}")
    logger.info(f"  - Wzorce prefiksów: {len(patterns['prefix_patterns'])}")
    logger.info(f"  - Reguły transformacji: {len(patterns['transformation_rules'])}")
    
    return patterns

def apply_learned_patterns(base_filename, image_files_in_folder, patterns):
    """Stosuje nauczone wzorce do znalezienia podglądu"""
    base_filename_lower = base_filename.lower().strip()
    
    # 1. Sprawdź dokładne dopasowania
    for pattern in patterns['exact_match']:
        archive_pattern = pattern['archive_pattern']
        image_pattern = pattern['image_pattern']
        
        # Sprawdź czy nazwa archiwum pasuje do wzorca
        if base_filename_lower == archive_pattern:
            # Szukaj obrazu pasującego do wzorca obrazu
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    if img_base.lower().strip() == image_pattern:
                        logger.info(f"🎓 WZORZEC DOKŁADNY: '{base_filename}' ↔ '{img_name}'")
                        return img_path
    
    # 2. Sprawdź wzorce sufiksów
    for pattern in patterns['suffix_patterns']:
        base_pattern = pattern['base_pattern']
        suffix = pattern['suffix']
        
        if base_filename_lower.startswith(base_pattern) or base_pattern in base_filename_lower:
            # Szukaj obrazu z tym sufiksem
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    img_base_lower = img_base.lower().strip()
                    # Sprawdź czy obraz ma ten sufiks
                    if suffix in img_base_lower:
                        logger.info(f"🎓 WZORZEC SUFIKS: '{base_filename}' ↔ '{img_name}' (sufiks: {suffix})")
                        return img_path
    
    # 3. Sprawdź wzorce prefiksów
    for pattern in patterns['prefix_patterns']:
        base_pattern = pattern['base_pattern']
        prefix = pattern['prefix']
        
        if base_filename_lower.endswith(base_pattern) or base_pattern in base_filename_lower:
            # Szukaj obrazu bez tego prefiksu
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    img_base_lower = img_base.lower().strip()
                    if img_base_lower == base_pattern:
                        logger.info(f"🎓 WZORZEC PREFIKS: '{base_filename}' ↔ '{img_name}' (prefiks: {prefix})")
                        return img_path
    
    # 4. Sprawdź reguły transformacji
    for pattern in patterns['transformation_rules']:
        common_parts = pattern['common_parts']
        
        # Sprawdź czy nazwa archiwum zawiera wspólne części
        matches_count = 0
        for arch_part, img_part in common_parts:
            if arch_part in base_filename_lower:
                matches_count += 1
                
        if matches_count > 0:
            # Szukaj obrazu zawierającego odpowiednie części
            for img_path in image_files_in_folder:
                img_name = os.path.basename(img_path)
                img_base, img_ext = os.path.splitext(img_name)
                if img_ext.lower() in IMAGE_EXTENSIONS:
                    img_base_lower = img_base.lower().strip()
                    img_matches = 0
                    for arch_part, img_part in common_parts:
                        if img_part in img_base_lower:
                            img_matches += 1
                    
                    if img_matches >= matches_count:
                        logger.info(f"🎓 WZORZEC TRANSFORMACJA: '{base_filename}' ↔ '{img_name}' (wspólne części: {matches_count})")
                        return img_path
    
    return None

def find_matching_preview_for_file(
    base_filename, image_files_in_folder, learning_data=None
):
    """
    Szuka pasującego pliku podglądu dla dowolnego pliku używając wzorców z uczenia.
    """
    logger.debug(f"🔍 Rozpoczynam szukanie podglądu dla pliku bazowego: '{base_filename}'")
    
    if not base_filename:
        logger.warning("❌ Przekazano pustą nazwę bazową pliku")
        return None

    # 1. PIERWSZEŃSTWO: Zastosuj nauczone wzorce
    if learning_data:
        logger.debug(f"📚 Analizuję dane uczenia dla: '{base_filename}'")
        patterns = extract_learning_patterns(learning_data)
        
        learned_match = apply_learned_patterns(base_filename, image_files_in_folder, patterns)
        if learned_match:
            logger.info(f"🎓 ZNALEZIONO DOPASOWANIE PRZEZ WZORCE UCZENIA: '{base_filename}' ↔ '{os.path.basename(learned_match)}'")
            return learned_match
        else:
            logger.debug(f"📚 Wzorce uczenia nie dały rezultatu dla '{base_filename}'")

    # 2. FALLBACK: Standardowy algorytm dopasowania (pozostaje bez zmian)
    logger.debug(f"⚙️ Używam standardowego algorytmu dopasowania dla: '{base_filename}'")
    
    # ... reszta funkcji pozostaje bez zmian ...
Zmiana w funkcji load_learning_data
pythondef load_learning_data():
    """Wczytuje dane uczenia się z pliku JSON"""
    try:
        learning_file = config_manager.get_config_value("learning_data_file", "learning_data.json")
        if os.path.exists(learning_file):
            with open(learning_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"Wczytano {len(data)} wpisów z danych uczenia się ({learning_file}).")
                
                # Analiza jakości danych uczenia
                valid_entries = 0
                for entry in data:
                    if entry.get("archive_basename") and entry.get("image_basename"):
                        valid_entries += 1
                
                logger.info(f"📊 Jakość danych uczenia: {valid_entries}/{len(data)} prawidłowych wpisów")
                
                return data
        logger.info(f"Plik danych uczenia się ({learning_file}) nie istnieje.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Błąd dekodowania JSON w pliku danych uczenia się: {e}")
        return []
    except Exception as e:
        logger.error(f"Błąd wczytywania danych uczenia się: {e}", exc_info=True)
        return []
Główne zmiany:

Wyciąganie wzorców zamiast zapamiętywania konkretnych przypadków
Analiza typów dopasowań:

Dokładne dopasowania (po oczyszczeniu ze znaków specjalnych)
Wzorce sufiksów (obraz ma dodatkowy sufiks)
Wzorce prefiksów (archiwum ma dodatkowy prefiks)
Reguły transformacji (wspólne części w różnych formatach)


Inteligentne stosowanie wyciągniętych wzorców do nowych plików

Teraz system będzie:

Z przykładu "Porsche..." wyciągnie wzorzec, że obrazy mogą mieć spacje tam gdzie archiwum ma podkreślniki
Z przykładu "328995..." nauczy się, że kropki mogą być zamieniane na podkreślniki
Te wzorce będzie stosował do nowych, niewidzianych wcześniej plików