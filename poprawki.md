Zidentyfikowane problemy w kodzie
1. Problem z progami podobieństwa
Aktualne progi są zbyt rygorystyczne:

similarity_threshold = 0.30
high_confidence_threshold = 0.60
low_similarity_threshold = 0.20
2. Problem z przypisywaniem poziomów pewności
W metodzie find_best_matches nie ma logiki przypisującej confidence_level.

3. Problem z bardzo prostym dopasowaniem
Warunki są zbyt restrykcyjne.

Proponowane zmiany
Zmiana w pliku ai_sbert_matcher.py, w metodzie __init__
python
# Dostosowane progi dla lepszego dopasowywania plików
self.similarity_threshold = 0.15  # Obniżony z 0.30
self.high_confidence_threshold = 0.40  # Obniżony z 0.60
self.very_high_confidence_threshold = 0.70  # Obniżony z 0.80
self.low_similarity_threshold = 0.10  # Obniżony z 0.20
Zmiana w pliku ai_sbert_matcher.py, w metodzie find_best_matches
python
def find_best_matches(self, archive_files: List[str], image_files: List[str]) -> List[Dict]:
    """
    Znajduje najlepsze dopasowania między plikami archiwum a obrazami
    """
    matches = []
    used_images = set()

    for archive_file in archive_files:
        best_similarity = 0.0
        best_image_idx = -1
        best_method = "NO_MATCH"

        # Pierwsza faza: SBERT
        try:
            embeddings = self.calculate_embeddings([archive_file] + image_files)
            if len(embeddings) > 1:
                archive_embedding = embeddings[0]
                image_embeddings = embeddings[1:]
                
                similarities = cosine_similarity([archive_embedding], image_embeddings)[0]
                
                for j, similarity in enumerate(similarities):
                    if j in used_images:
                        continue
                        
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_image_idx = j
                        best_method = "SBERT"
        except Exception as e:
            logger.warning(f"Błąd SBERT dla {archive_file}: {e}")

        # Druga faza: proste dopasowanie
        if best_image_idx == -1 or best_similarity < self.similarity_threshold:
            for j, image_file in enumerate(image_files):
                if j in used_images:
                    continue
                
                simple_similarity = self.simple_string_similarity(archive_file, image_file)
                if simple_similarity > best_similarity and simple_similarity >= self.low_similarity_threshold:
                    best_similarity = simple_similarity
                    best_image_idx = j
                    best_method = "SIMPLE_MATCH"

        # Trzecia faza: bardzo proste dopasowania - ULEPSZONA
        if best_image_idx == -1 or best_similarity < self.low_similarity_threshold:
            logger.debug(f"Próbuję bardzo proste dopasowanie dla '{archive_file}'")
            
            for j, image_file in enumerate(image_files):
                if j in used_images:
                    continue
                
                # Ulepszone bardzo proste dopasowanie
                archive_base = os.path.splitext(archive_file)[0].lower()
                image_base = os.path.splitext(image_file)[0].lower()
                
                # Usuń wszystkie separatory i porównaj
                archive_clean = re.sub(r'[_\-\.\s]', '', archive_base)
                image_clean = re.sub(r'[_\-\.\s]', '', image_base)
                
                very_simple_similarity = 0.0
                
                # Sprawdź dokładne dopasowanie po czyszczeniu
                if archive_clean == image_clean and len(archive_clean) > 2:
                    very_simple_similarity = 0.85
                # Sprawdź czy jedna nazwa zawiera drugą (min 60% długości)
                elif len(archive_clean) > 3 and len(image_clean) > 3:
                    shorter_len = min(len(archive_clean), len(image_clean))
                    longer_len = max(len(archive_clean), len(image_clean))
                    
                    if shorter_len / longer_len >= 0.6:  # Co najmniej 60% podobieństwa długości
                        if archive_clean in image_clean or image_clean in archive_clean:
                            very_simple_similarity = 0.5
                # Sprawdź podobieństwo początkowych znaków
                elif len(archive_clean) > 4 and len(image_clean) > 4:
                    # Sprawdź pierwsze 70% znaków
                    check_len = min(int(len(archive_clean) * 0.7), int(len(image_clean) * 0.7))
                    if check_len > 3 and archive_clean[:check_len] == image_clean[:check_len]:
                        very_simple_similarity = 0.3
                
                if very_simple_similarity > best_similarity:
                    best_similarity = very_simple_similarity
                    best_image_idx = j
                    best_method = "VERY_SIMPLE_MATCH"

        # Przypisanie poziomu pewności - NOWA LOGIKA
        if best_image_idx != -1:
            used_images.add(best_image_idx)
            
            # Określ poziom pewności
            if best_similarity >= self.very_high_confidence_threshold:
                confidence_level = "VERY_HIGH"
            elif best_similarity >= self.high_confidence_threshold:
                confidence_level = "HIGH" 
            elif best_similarity >= self.similarity_threshold:
                confidence_level = "MEDIUM"
            else:
                confidence_level = "LOW"
            
            matches.append({
                "archive_file": archive_file,
                "image_file": image_files[best_image_idx],
                "similarity": float(best_similarity),
                "confidence_level": confidence_level,  # DODANE
                "similarity_score": float(best_similarity),  # DODANE dla kompatybilności
                "method": best_method,
                "matching_method": best_method,  # DODANE dla kompatybilności
                "timestamp": datetime.now().isoformat()  # DODANE
            })

    return matches
Zmiana w pliku ai_sbert_matcher.py, w metodzie simple_string_similarity
python
def simple_string_similarity(self, str1: str, str2: str) -> float:
    """
    Ulepszona miara podobieństwa z wieloma metodami porównywania
    """
    # Usuń rozszerzenia i normalizuj
    clean1 = os.path.splitext(str1)[0].lower()
    clean2 = os.path.splitext(str2)[0].lower()
    
    # 1. Sprawdź dokładne dopasowanie po normalizacji separatorów
    normalized1 = re.sub(r'[_\-\.\s]', '', clean1)
    normalized2 = re.sub(r'[_\-\.\s]', '', clean2)
    
    if normalized1 == normalized2 and len(normalized1) > 2:
        return 1.0
    
    # 2. Sprawdź podobieństwo Levenshtein dla krótkich nazw
    if len(normalized1) <= 10 and len(normalized2) <= 10:
        max_len = max(len(normalized1), len(normalized2))
        if max_len > 0:
            # Prosta implementacja odległości Levenshtein
            distance = self._levenshtein_distance(normalized1, normalized2)
            similarity = 1.0 - (distance / max_len)
            if similarity > 0.7:  # Próg dla podobieństwa Levenshtein
                return similarity
    
    # 3. Oryginalny algorytm Jaccard
    words1 = set(self.preprocess_filename(str1).lower().split())
    words2 = set(self.preprocess_filename(str2).lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    jaccard_similarity = intersection / union if union > 0 else 0.0
    
    # 4. Sprawdź podobieństwo podciągów
    substring_similarity = self._substring_similarity(clean1, clean2)
    
    # Zwróć najwyższy wynik
    return max(jaccard_similarity, substring_similarity)

def _levenshtein_distance(self, s1: str, s2: str) -> int:
    """Oblicza odległość Levenshtein między dwoma ciągami"""
    if len(s1) < len(s2):
        return self._levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def _substring_similarity(self, s1: str, s2: str) -> float:
    """Oblicza podobieństwo na podstawie najdłuższego wspólnego podciągu"""
    if not s1 or not s2:
        return 0.0
    
    # Znajdź najdłuższy wspólny podciąg
    longer = s1 if len(s1) > len(s2) else s2
    shorter = s2 if len(s1) > len(s2) else s1
    
    max_common_length = 0
    for i in range(len(shorter)):
        for j in range(i + 1, len(shorter) + 1):
            substring = shorter[i:j]
            if len(substring) > max_common_length and substring in longer:
                max_common_length = len(substring)
    
    # Zwróć stosunek najdłuższego wspólnego podciągu do długości krótszego ciągu
    return max_common_length / len(shorter) if len(shorter) > 0 else 0.0
Dodatkowa zmiana w pliku ai_sbert_matcher.py, nowa metoda diagnostyczna
python
def diagnose_matching_failure(self, archive_file: str, image_files: List[str]) -> Dict:
    """
    Diagnostyka gdy dopasowanie nie działa - szczegółowa analiza
    """
    diagnosis = {
        "archive_file": archive_file,
        "processed_archive": self.preprocess_filename(archive_file),
        "total_candidates": len(image_files),
        "detailed_scores": []
    }
    
    for image_file in image_files:
        # Test wszystkich metod dopasowania
        try:
            # SBERT
            embeddings = self.calculate_embeddings([archive_file, image_file])
            sbert_score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0] if len(embeddings) == 2 else 0.0
        except:
            sbert_score = 0.0
        
        # Simple similarity
        simple_score = self.simple_string_similarity(archive_file, image_file)
        
        # Very simple matching
        archive_clean = re.sub(r'[_\-\.\s]', '', os.path.splitext(archive_file)[0].lower())
        image_clean = re.sub(r'[_\-\.\s]', '', os.path.splitext(image_file)[0].lower())
        
        very_simple_exact = archive_clean == image_clean
        very_simple_contains = archive_clean in image_clean or image_clean in archive_clean
        
        score_detail = {
            "image_file": image_file,
            "processed_image": self.preprocess_filename(image_file),
            "sbert_score": float(sbert_score),
            "simple_score": float(simple_score),
            "very_simple_exact": very_simple_exact,
            "very_simple_contains": very_simple_contains,
            "archive_clean": archive_clean,
            "image_clean": image_clean,
            "max_score": max(sbert_score, simple_score),
            "would_match_old": max(sbert_score, simple_score) >= 0.20,
            "would_match_new": max(sbert_score, simple_score) >= 0.10 or very_simple_exact or very_simple_contains
        }
        
        diagnosis["detailed_scores"].append(score_detail)
    
    # Sortuj według najwyższego wyniku
    diagnosis["detailed_scores"].sort(key=lambda x: x["max_score"], reverse=True)
    diagnosis["best_candidate"] = diagnosis["detailed_scores"][0] if diagnosis["detailed_scores"] else None
    
    return diagnosis
Te zmiany powinny znacznie poprawić dopasowywanie poprzez:

Obniżenie progów - więcej plików będzie dopasowanych
Dodanie poziomu pewności - brakujące pole w strukturze wyniku
Ulepszenie bardzo prostego dopasowania - więcej wariantów porównywania
Dodanie metod pomocniczych - Levenshtein, podobieństwo podciągów
Narzędzie diagnostyczne - do debugowania konkretnych przypadków
Czy chcesz, żebym przygotował te zmiany w osobnych plikach lub wyjaśnił konkretny przypadek, który Cię frustruje?





