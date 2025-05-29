Problem w funkcji preprocess_filename()
Główny problem leży w sposobie przetwarzania nazw plików w metodzie preprocess_filename() (linie 134-156):
markdown# Zmiana w pliku ai_sbert_matcher.py, w funkcji preprocess_filename(), proponowany kod do zmiany:

```python
def preprocess_filename(self, filename: str) -> str:
    """
    Ulepszone przetwarzanie nazw plików z zachowaniem kluczowych informacji
    """
    # Usuń rozszerzenie
    name_without_ext = os.path.splitext(filename)[0]
    
    # PROBLEM: Ta logika psuje proste dopasowania!
    # Zamień separatory na spacje, ale zachowaj numery
    processed = re.sub(r"[_\-]", " ", name_without_ext)  # 328995_55c5cfe0d1a6d -> 328995 55c5cfe0d1a6d
    processed = re.sub(r"\.(?=\D)", " ", processed)      # 328995.55c5cfe0d1a6d -> 328995 55c5cfe0d1a6d
    
    # PROBLEMATYCZNE: Dodaje sztuczne prefiksy
    processed = re.sub(r"(\d{6,})", r" ID\1 ", processed)    # 328995 -> ID328995, 55c5cfe0d1a6d -> ID55c5cfe0d1a6d  
    processed = re.sub(r"\b(\d{1,3})\b", r" VER\1 ", processed)  # Dodaje VER do krótkich liczb

### Co się dzieje krok po kroku:

1. **Plik 1**: `"328995_55c5cfe0d1a6d.rar"`
   - Po usunięciu rozszerzenia: `"328995_55c5cfe0d1a6d"`
   - Po zamianie `_` na spację: `"328995 55c5cfe0d1a6d"`
   - Po dodaniu prefiksów ID: `" ID328995  ID55c5cfe0d1a6d "`

2. **Plik 2**: `"328995.55c5cfe0d1a6d.jpeg"`
   - Po usunięciu rozszerzenia: `"328995.55c5cfe0d1a6d"`
   - Po zamianie `.` na spację: `"328995 55c5cfe0d1a6d"`
   - Po dodaniu prefiksów ID: `" ID328995  ID55c5cfe0d1a6d "`

### Dlaczego nie działa?

Chociaż po przetworzeniu oba ciągi wyglądają identycznie (`" ID328995  ID55c5cfe0d1a6d "`), model SBERT generuje embeddingi na podstawie kontekstu semantycznego , a słowa `"ID328995"` i `"ID55c5cfe0d1a6d"` są traktowane jako oddzielne tokeny bez znaczenia semantycznego.

## Propozycja poprawki

```markdown
# Zmiana w pliku ai_sbert_matcher.py, w funkcji preprocess_filename(), proponowany kod do zmiany:

```python
def preprocess_filename(self, filename: str) -> str:
    """
    Ulepszone przetwarzanie nazw plików - uproszczona wersja dla lepszego dopasowania
    """
    # Usuń rozszerzenie
    name_without_ext = os.path.splitext(filename)[0]
    
    # Prosta normalizacja: zamień separatory na spacje
    processed = re.sub(r"[_\-\.]", " ", name_without_ext)
    
    # Usuń wielokrotne spacje
    processed = re.sub(r"\s+", " ", processed).strip()
    
    logger.debug(f"Preprocessing: '{filename}' -> '{processed}'")
    return processed

### Dodatkowo - ulepszenie funkcji `simple_string_similarity()`

```markdown
# Zmiana w pliku ai_sbert_matcher.py, w funkcji simple_string_similarity(), proponowany kod do zmiany:

```python
def simple_string_similarity(self, str1: str, str2: str) -> float:
    """
    Prosta miara podobieństwa z priorytetem dla identycznych części
    """
    # Usuń rozszerzenia i normalizuj
    clean1 = os.path.splitext(str1)[0].lower()
    clean2 = os.path.splitext(str2)[0].lower()
    
    # Sprawdź dokładne dopasowanie po normalizacji separatorów
    normalized1 = re.sub(r"[_\-\.]", "", clean1)
    normalized2 = re.sub(r"[_\-\.]", "", clean2)
    
    if normalized1 == normalized2:
        return 1.0  # Identyczne po normalizacji = 100% dopasowania
    
    # Reszta logiki jak wcześniej...
    words1 = set(self.preprocess_filename(str1).lower().split())
    words2 = set(self.preprocess_filename(str2).lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

## Podsumowanie problemów:

1. **Nadmierne przetwarzanie**: Dodawanie prefiksów "ID" i "VER" psuje naturalne dopasowania
2. **Brak prostej normalizacji**: Model nie sprawdza identyczności po usunięciu separatorów
3. **SBERT nie radzi sobie z krótkimi identyfikatorami**: Model jest trenowany na zdaniach, nie na kodach/ID
4. **Brak priorytetyzacji**: Prosty algorytm powinien mieć wyższy priorytet dla oczywistych dopasowań

Implementacja tych zmian powinna znacząco poprawić dopasowywanie prostych przypadków jak ten, który podałeś.RetryClaude does not have the ability to run the code it generates yet.Claude can make mistakes. Please double-check cited sources.