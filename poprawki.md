🛠️ Proponowane zmiany w Markdown
Zmiana 1: Obniżenie progów podobieństwa
Plik: ai_sbert_matcher.py
Funkcja: __init__
Zmiana: Obniżenie progów dla lepszego dopasowania prostych przypadków
python# Zmień obecne progi:
self.similarity_threshold = 0.30  # Obniżone z 0.45 na 0.30
self.high_confidence_threshold = 0.60  # Obniżone z 0.70 na 0.60
self.very_high_confidence_threshold = 0.80  # Obniżone z 0.85 na 0.80

# Dodaj dodatkowy próg dla bardzo prostych przypadków:
self.low_similarity_threshold = 0.20  # Nowy próg dla fallback
Zmiana 2: Ulepszone preprocessing z zachowaniem więcej informacji
Plik: ai_sbert_matcher.py
Funkcja: preprocess_filename
Zmiana: Lepsze zachowanie ważnych części nazw plików
pythondef preprocess_filename(self, filename: str) -> str:
    """
    Ulepszone przetwarzanie z zachowaniem więcej kontekstu
    """
    # Usuń rozszerzenie
    name_without_ext = os.path.splitext(filename)[0]
    
    # Zachowaj więcej informacji - zamień tylko podkreślenia i myślniki
    processed = re.sub(r"[_\-]", " ", name_without_ext)
    
    # Zachowaj kropki jako separatory dla numerów/wersji
    processed = re.sub(r"\.(?=\d)", " ", processed)  # Kropka przed cyfrą -> spacja
    processed = re.sub(r"(?<=\d)\.(?=\d)", " ", processed)  # Kropka między cyframi -> spacja
    
    # Usuń wielokrotne spacje
    processed = re.sub(r"\s+", " ", processed).strip()
    
    logger.debug(f"Preprocessing: '{filename}' -> '{processed}'")
    return processed
Zmiana 3: Bardziej agresywny fallback dla prostych przypadków
Plik: ai_sbert_matcher.py
Funkcja: find_best_matches
Zmiana: Dodanie trzeciej fazy dla bardzo prostych dopasowań
python# W funkcji find_best_matches(), po drugiej fazie dodaj trzecią fazę:

# Trzecia faza: bardzo proste dopasowania dla pozostałych plików
if best_image_idx == -1:
    logger.debug(f"Próbuję bardzo proste dopasowanie dla '{archive_file}'")
    
    for j, image_file in enumerate(image_files):
        if j in used_images:
            continue
        
        # Bardzo proste dopasowanie - tylko nazwy bez rozszerzeń
        archive_base = os.path.splitext(archive_file)[0].lower()
        image_base = os.path.splitext(image_file)[0].lower()
        
        # Usuń wszystkie separatory i porównaj
        archive_clean = re.sub(r'[_\-\.\s]', '', archive_base)
        image_clean = re.sub(r'[_\-\.\s]', '', image_base)
        
        # Sprawdź czy jedna nazwa zawiera drugą
        if (archive_clean in image_clean or image_clean in archive_clean) and len(archive_clean) > 2:
            very_simple_similarity = 0.25  # Przypisz stały wynik dla tego typu dopasowania
            if very_simple_similarity > best_similarity:
                best_similarity = very_simple_similarity
                best_image_idx = j
                best_method = "VERY_SIMPLE_MATCH"
Zmiana 4: Dodanie funkcji debugowania dla konkretnego przypadku
Plik: ai_sbert_matcher.py
Nowa funkcja: Dodanie na końcu klasy SBERTFileMatcher
pythondef debug_specific_case(self, archive_name: str, image_name: str) -> Dict:
    """
    Szczegółowe debugowanie konkretnego przypadku
    """
    debug_result = {
        "archive_name": archive_name,
        "image_name": image_name,
        "preprocessing": {
            "archive_processed": self.preprocess_filename(archive_name),
            "image_processed": self.preprocess_filename(image_name)
        }
    }
    
    # Test SBERT
    try:
        embeddings = self.calculate_embeddings([archive_name, image_name])
        if len(embeddings) >= 2:
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            debug_result["sbert_similarity"] = float(similarity)
            debug_result["sbert_threshold_met"] = similarity >= self.similarity_threshold
        else:
            debug_result["sbert_error"] = "Nie udało się obliczyć embeddings"
    except Exception as e:
        debug_result["sbert_error"] = str(e)
    
    # Test prostego dopasowania
    simple_sim = self.simple_string_similarity(archive_name, image_name)
    debug_result["simple_similarity"] = simple_sim
    debug_result["simple_threshold_met"] = simple_sim >= 0.3
    
    # Test bardzo prostego dopasowania
    archive_clean = re.sub(r'[_\-\.\s]', '', os.path.splitext(archive_name)[0].lower())
    image_clean = re.sub(r'[_\-\.\s]', '', os.path.splitext(image_name)[0].lower())
    
    debug_result["very_simple"] = {
        "archive_clean": archive_clean,
        "image_clean": image_clean,
        "archive_in_image": archive_clean in image_clean,
        "image_in_archive": image_clean in archive_clean,
        "would_match": (archive_clean in image_clean or image_clean in archive_clean) and len(archive_clean) > 2
    }
    
    return debug_result
Zmiana 5: Funkcja testowa w main()
Plik: ai_sbert_matcher.py
Funkcja: main
Zmiana: Dodanie opcji testowania konkretnego przypadku
python# W funkcji main(), po istniejących opcjach dodaj:

elif choice == "5":
    # Test konkretnego przypadku
    print("\n🔍 Test konkretnego przypadku:")
    archive_name = input("Podaj nazwę pliku archiwum: ").strip()
    image_name = input("Podaj nazwę pliku obrazu: ").strip()
    
    if archive_name and image_name:
        debug_result = processor.matcher.debug_specific_case(archive_name, image_name)
        print("\n📊 WYNIKI DEBUGOWANIA:")
        print("-" * 50)
        import json
        print(json.dumps(debug_result, indent=2, ensure_ascii=False))
    else:
        print("❌ Nie podano nazw plików")
🎯 Dlaczego proste przypadki mogą nie działać:

Zbyt wysokie progi - 45% podobieństwa to dużo dla prostych nazw
Model SBERT może nie rozpoznawać prostych podobieństw leksykalnych
Preprocessing może gubić ważne informacje
Brak dedykowanego algorytmu dla bardzo prostych przypadków

Te zmiany powinny znacznie poprawić dopasowywanie prostych przypadków. Przetestuj je i daj znać jak działają!