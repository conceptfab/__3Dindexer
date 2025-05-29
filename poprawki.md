Analiza problemów w ai_sbert_matcher.py
1. Problemy z preprocessing nazw plików
Plik: ai_sbert_matcher.py
Funkcja: preprocess_filename()
pythondef preprocess_filename(self, filename: str) -> str:
    """
    Przygotowuje nazwę pliku do analizy przez model
    """
    # Usuń rozszerzenie
    name_without_ext = os.path.splitext(filename)[0]

    # Zamień różne separatory na spacje
    processed = re.sub(r"[_\-\.]", " ", name_without_ext)

    # PROBLEM: Ta logika może zbyt mocno modyfikować nazwy
    # Usuń wielokrotne spacje
    processed = re.sub(r"\s+", " ", processed)

    # PROBLEM: Aggressive regex może zniszczyć ważne informacje
    # Wydziel numery wersji
    processed = re.sub(r"(\d+)", r" \1 ", processed)

    # PROBLEM: Może rozdzielić ważne numery ID
    processed = re.sub(r"\s+", " ", processed).strip()

    return processed
Proponowane zmiany:
pythondef preprocess_filename(self, filename: str) -> str:
    """
    Ulepszone przetwarzanie nazw plików z zachowaniem kluczowych informacji
    """
    # Usuń rozszerzenie
    name_without_ext = os.path.splitext(filename)[0]
    
    # Zachowaj oryginalne ID i numery seryjne
    # Zamień separatory na spacje, ale zachowaj numery
    processed = re.sub(r"[_\-]", " ", name_without_ext)
    processed = re.sub(r"\.(?=\D)", " ", processed)  # Kropki tylko przed literami
    
    # Zachowaj długie numery (prawdopodobnie ID)
    processed = re.sub(r"(\d{6,})", r" ID\1 ", processed)
    
    # Oznacz krótkie numery jako wersje
    processed = re.sub(r"\b(\d{1,3})\b", r" VER\1 ", processed)
    
    # Wyczyść wielokrotne spacje
    processed = re.sub(r"\s+", " ", processed).strip()
    
    logger.debug(f"Preprocessing: '{filename}' -> '{processed}'")
    return processed
2. Zbyt wysoki próg podobieństwa
Plik: ai_sbert_matcher.py
Funkcja: __init__()
pythondef __init__(self, model_name: str = "all-MiniLM-L6-v2"):
    # PROBLEM: Zbyt wysokie progi mogą odrzucać dobre dopasowania
    self.similarity_threshold = 0.65  # Minimalny próg podobieństwa
    self.high_confidence_threshold = 0.80  # Próg wysokiej pewności
Proponowane zmiany:
pythondef __init__(self, model_name: str = "all-MiniLM-L6-v2"):
    # Obniżone progi dla lepszej czułości
    self.similarity_threshold = 0.45  # Bardziej tolerancyjny próg
    self.high_confidence_threshold = 0.70  # Realistyczny próg wysokiej pewności
    self.very_high_confidence_threshold = 0.85  # Dla wyjątkowych dopasowań
3. Dodanie warstwy fallback dla prostych dopasowań
Nowa funkcja do dodania:
pythondef simple_string_similarity(self, str1: str, str2: str) -> float:
    """
    Prosta miara podobieństwa bazująca na wspólnych słowach
    Użyteczna jako fallback gdy SBERT zawodzi
    """
    words1 = set(self.preprocess_filename(str1).lower().split())
    words2 = set(self.preprocess_filename(str2).lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    jaccard = intersection / union if union > 0 else 0.0
    
    # Bonus za długie wspólne części
    str1_clean = self.preprocess_filename(str1).replace(" ", "").lower()
    str2_clean = self.preprocess_filename(str2).replace(" ", "").lower()
    
    # Longest common substring
    lcs_length = self.longest_common_substring_length(str1_clean, str2_clean)
    lcs_bonus = lcs_length / max(len(str1_clean), len(str2_clean))
    
    return min(1.0, jaccard + (lcs_bonus * 0.3))

def longest_common_substring_length(self, str1: str, str2: str) -> int:
    """Znajduje długość najdłuższego wspólnego podciągu"""
    m, n = len(str1), len(str2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_length = 0
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                max_length = max(max_length, dp[i][j])
            else:
                dp[i][j] = 0
    
    return max_length
4. Ulepszona logika dopasowywania z fallback
Plik: ai_sbert_matcher.py
Funkcja: find_best_matches()
pythondef find_best_matches(self, archive_files: List[str], image_files: List[str]) -> List[Dict]:
    """
    Ulepszone dopasowywanie z warstwą fallback
    """
    if not archive_files or not image_files:
        logger.warning("Brak plików do dopasowania")
        return []

    logger.info(f"Szukanie dopasowań: {len(archive_files)} archiwów vs {len(image_files)} obrazów")

    # Oblicz embeddings SBERT
    archive_embeddings = self.calculate_embeddings(archive_files)
    image_embeddings = self.calculate_embeddings(image_files)
    similarities = cosine_similarity(archive_embeddings, image_embeddings)

    matches = []
    used_images = set()

    # Pierwsza faza: dopasowania SBERT
    for i, archive_file in enumerate(archive_files):
        best_similarity = 0.0
        best_image_idx = -1
        best_method = "SBERT"

        for j, image_file in enumerate(image_files):
            if j in used_images:
                continue

            sbert_similarity = similarities[i][j]
            if sbert_similarity > best_similarity and sbert_similarity >= self.similarity_threshold:
                best_similarity = sbert_similarity
                best_image_idx = j

        # Druga faza: jeśli SBERT nie znalazł dopasowania, użyj prostego algorytmu
        if best_image_idx == -1:
            logger.debug(f"SBERT nie znalazł dopasowania dla '{archive_file}', próbuję prostego algorytmu")
            
            for j, image_file in enumerate(image_files):
                if j in used_images:
                    continue

                simple_similarity = self.simple_string_similarity(archive_file, image_file)
                # Niższy próg dla prostego algorytmu
                if simple_similarity > best_similarity and simple_similarity >= 0.3:
                    best_similarity = simple_similarity
                    best_image_idx = j
                    best_method = "SIMPLE_STRING"

        if best_image_idx != -1:
            image_file = image_files[best_image_idx]
            used_images.add(best_image_idx)

            # Określ poziom pewności
            if best_similarity >= self.very_high_confidence_threshold:
                confidence_level = "VERY_HIGH"
            elif best_similarity >= self.high_confidence_threshold:
                confidence_level = "HIGH"
            elif best_similarity >= 0.50:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"

            match_info = {
                "archive_file": archive_file,
                "image_file": image_file,
                "similarity_score": float(best_similarity),
                "confidence_level": confidence_level,
                "matching_method": best_method,
                "timestamp": datetime.now().isoformat(),
            }

            matches.append(match_info)
            logger.info(f"✅ Dopasowanie [{confidence_level}][{best_method}]: '{archive_file}' ↔ '{image_file}' (score: {best_similarity:.3f})")

    logger.info(f"Znaleziono {len(matches)} dopasowań z {len(archive_files)} archiwów")
    return matches
5. Dodanie funkcji debugowania
Nowa funkcja do dodania:
pythondef debug_matching_process(self, archive_file: str, image_files: List[str]) -> Dict:
    """
    Funkcja debugowania pokazująca dlaczego dopasowania mogą nie działać
    """
    debug_info = {
        "archive_file": archive_file,
        "processed_archive": self.preprocess_filename(archive_file),
        "candidates": []
    }
    
    archive_embedding = self.calculate_embeddings([archive_file])
    image_embeddings = self.calculate_embeddings(image_files)
    
    if len(archive_embedding) > 0 and len(image_embeddings) > 0:
        similarities = cosine_similarity(archive_embedding, image_embeddings)[0]
        
        for i, image_file in enumerate(image_files):
            sbert_sim = similarities[i]
            simple_sim = self.simple_string_similarity(archive_file, image_file)
            
            candidate_info = {
                "image_file": image_file,
                "processed_image": self.preprocess_filename(image_file),
                "sbert_similarity": float(sbert_sim),
                "simple_similarity": float(simple_sim),
                "sbert_threshold_met": sbert_sim >= self.similarity_threshold,
                "simple_threshold_met": simple_sim >= 0.3,
                "would_match": sbert_sim >= self.similarity_threshold or simple_sim >= 0.3
            }
            
            debug_info["candidates"].append(candidate_info)
    
    # Sortuj według najlepszego wyniku
    debug_info["candidates"].sort(key=lambda x: max(x["sbert_similarity"], x["simple_similarity"]), reverse=True)
    
    return debug_info
Podsumowanie głównych problemów:

Agresywny preprocessing - zbyt mocno modyfikuje nazwy plików
Wysokie progi podobieństwa - odrzuca dobre dopasowania
Brak warstwy fallback - gdy SBERT zawodzi, nie ma alternatywy
Brak debugowania - trudno zrozumieć dlaczego dopasowania nie działają

Te zmiany powinny znacznie poprawić skuteczność dopasowywania, szczególnie dla prostych przypadków z podobnymi nazwami plików.