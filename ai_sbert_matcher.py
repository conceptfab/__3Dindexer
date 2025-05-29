# ai_sbert_matcher.py
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Potrzebne biblioteki - zainstaluj przez: pip install sentence-transformers numpy scikit-learn
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import config_manager

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rozszerzenia obrazów
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".png",
    ".apng",
    ".gif",
    ".bmp",
    ".dib",
    ".webp",
    ".tiff",
    ".tif",
    ".svg",
    ".svgz",
    ".ico",
    ".avif",
    ".heic",
    ".heif",
)


class SBERTFileMatcher:
    """
    Klasa do dopasowywania nazw plików używając Sentence-BERT
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicjalizacja z wyborem modelu SBERT

        Modele do wyboru:
        - 'all-MiniLM-L6-v2' - szybki, dobry stosunek jakość/prędkość (22MB)
        - 'all-MiniLM-L12-v2' - większy, lepszy (43MB)
        - 'paraphrase-MiniLM-L6-v2' - dobry do parafraz (22MB)
        """
        logger.info(f"Ładowanie modelu SBERT: {model_name}")
        start_time = time.time()

        try:
            self.model = SentenceTransformer(model_name)
            load_time = time.time() - start_time
            logger.info(f"Model załadowany w {load_time:.2f}s")
        except Exception as e:
            logger.error(f"Błąd ładowania modelu: {e}")
            raise

        # Obniżone progi dla lepszej czułości
        self.similarity_threshold = 0.45  # Bardziej tolerancyjny próg
        self.high_confidence_threshold = 0.70  # Realistyczny próg wysokiej pewności
        self.very_high_confidence_threshold = 0.85  # Dla wyjątkowych dopasowań

    def preprocess_filename(self, filename: str) -> str:
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

    def simple_string_similarity(self, str1: str, str2: str) -> float:
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

    def calculate_embeddings(self, filenames: List[str]) -> np.ndarray:
        """
        Oblicza embeddings dla listy nazw plików
        """
        if not filenames:
            return np.array([])

        # Przetwarzaj nazwy plików
        processed_names = [self.preprocess_filename(name) for name in filenames]

        logger.debug(f"Obliczanie embeddings dla {len(processed_names)} plików")
        start_time = time.time()

        # Oblicz embeddings
        embeddings = self.model.encode(processed_names, show_progress_bar=False)

        calc_time = time.time() - start_time
        logger.debug(f"Embeddings obliczone w {calc_time:.2f}s")

        return embeddings

    def find_best_matches(self, archive_files: List[str], image_files: List[str]) -> List[Dict]:
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

    def debug_matching_process(self, archive_file: str, image_files: List[str]) -> Dict:
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

    def analyze_similarity_details(self, file1: str, file2: str) -> Dict:
        """
        Szczegółowa analiza podobieństwa między dwoma plikami
        """
        processed1 = self.preprocess_filename(file1)
        processed2 = self.preprocess_filename(file2)

        # Oblicz embeddings
        embeddings = self.model.encode([processed1, processed2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

        # Analiza słów kluczowych
        words1 = set(processed1.lower().split())
        words2 = set(processed2.lower().split())

        common_words = words1.intersection(words2)
        word_overlap = len(common_words) / max(len(words1.union(words2)), 1)

        analysis = {
            "file1": file1,
            "file2": file2,
            "processed1": processed1,
            "processed2": processed2,
            "sbert_similarity": float(similarity),
            "common_words": list(common_words),
            "word_overlap_ratio": float(word_overlap),
            "words_file1": list(words1),
            "words_file2": list(words2),
        }

        return analysis


def get_work_directory_from_config():
    """Pobiera folder roboczy z konfiguracji lub None jeśli nie ustawiony"""
    try:
        work_dir = config_manager.get_work_directory()
        if work_dir and os.path.isdir(work_dir):
            logger.info(f"📁 Znaleziono folder roboczy w konfiguracji: {work_dir}")
            return work_dir
        else:
            logger.warning("⚠️ Brak prawidłowego folderu roboczego w konfiguracji")
            return None
    except Exception as e:
        logger.error(f"❌ Błąd pobierania folderu roboczego z konfiguracji: {e}")
        return None


class AIFolderProcessor:
    """
    Klasa do przetwarzania folderów i dodawania danych AI do index.json
    """

    def __init__(self):
        self.matcher = SBERTFileMatcher()
        # Pobierz folder roboczy z konfiguracji
        self.work_directory = get_work_directory_from_config()
        if not self.work_directory:
            logger.warning("Brak folderu roboczego w konfiguracji")

    def load_existing_index(self, folder_path: str) -> Dict:
        """
        Ładuje istniejący plik index.json
        """
        index_path = os.path.join(folder_path, "index.json")

        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Błąd odczytu {index_path}: {e}")
                return {}
        else:
            logger.info(f"Brak pliku index.json w {folder_path}")
            return {}

    def save_index_with_ai_data(self, folder_path: str, index_data: Dict):
        """
        Zapisuje plik index.json z danymi AI
        """
        index_path = os.path.join(folder_path, "index.json")

        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=4, ensure_ascii=False)
            logger.info(f"💾 Zapisano AI dane do: {index_path}")
        except Exception as e:
            logger.error(f"Błąd zapisu {index_path}: {e}")

    def collect_files_in_folder(self, folder_path: str) -> Tuple[List[str], List[str]]:
        """
        Zbiera pliki archiwów i obrazów w folderze
        """
        archive_files = []
        image_files = []
        start_time = time.time()
        SCAN_TIMEOUT_SECONDS = 30  # Timeout dla skanowania pojedynczego folderu

        try:
            for entry in os.scandir(folder_path):
                if time.time() - start_time > SCAN_TIMEOUT_SECONDS:
                    logger.warning(f"⏰ Przekroczono limit czasu skanowania ({SCAN_TIMEOUT_SECONDS}s) w folderze {folder_path}")
                    break

                try:
                    if entry.is_file(follow_symlinks=False):
                        filename = entry.name.lower()

                        if filename == "index.json":
                            continue

                        if filename.endswith(IMAGE_EXTENSIONS):
                            image_files.append(entry.name)
                        else:
                            # Wszystkie inne pliki traktujemy jako archiwa/modele
                            archive_files.append(entry.name)
                except UnicodeEncodeError as e:
                    logger.error(f"Błąd kodowania nazwy pliku w {folder_path}: {e}")
                    continue
                except OSError as e:
                    logger.error(f"Błąd dostępu do pliku w {folder_path}: {e}")
                    continue

        except OSError as e:
            logger.error(f"Błąd skanowania folderu {folder_path}: {e}")
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas skanowania {folder_path}: {e}")

        return archive_files, image_files

    def process_folder(self, folder_path: str, progress_callback=None) -> bool:
        """
        Przetwarza jeden folder - dodaje dane AI do index.json
        """
        logger.info(f"🔍 Przetwarzanie AI folderu: {folder_path}")

        if progress_callback:
            progress_callback(f"🔍 Przetwarzanie AI folderu: {folder_path}")

        if not os.path.isdir(folder_path):
            logger.error(f"❌ Ścieżka nie jest folderem: {folder_path}")
            return False

        # Sprawdź czy istnieje index.json (folder musi być już przeskanowany)
        index_json_path = os.path.join(folder_path, "index.json")
        if not os.path.exists(index_json_path):
            logger.warning(f"⚠️ Brak index.json w folderze: {folder_path}")
            if progress_callback:
                progress_callback(f"⚠️ Brak index.json w folderze: {folder_path}")
            return False

        # Zbierz pliki
        archive_files, image_files = self.collect_files_in_folder(folder_path)

        if not archive_files and not image_files:
            logger.info(f"⚠️ Folder pusty (brak plików do analizy AI): {folder_path}")
            if progress_callback:
                progress_callback(
                    f"⚠️ Folder pusty (brak plików do analizy AI): {folder_path}"
                )
            return True

        logger.info(
            f"📊 Znaleziono: {len(archive_files)} archiwów, {len(image_files)} obrazów"
        )

        # Załaduj istniejący index.json
        index_data = self.load_existing_index(folder_path)

        # Sprawdź czy AI już przetwarzało ten folder
        if "AI_processing_date" in index_data:
            logger.info(f"🔄 Aktualizuję istniejące dane AI dla: {folder_path}")
            if progress_callback:
                progress_callback(
                    f"🔄 Aktualizuję istniejące dane AI dla: {folder_path}"
                )
        else:
            logger.info(f"🆕 Pierwsze przetwarzanie AI dla: {folder_path}")
            if progress_callback:
                progress_callback(f"🆕 Pierwsze przetwarzanie AI dla: {folder_path}")

        # Jeśli nie ma podstawowej struktury, utwórz ją
        if "folder_info" not in index_data:
            index_data["folder_info"] = {
                "path": os.path.abspath(folder_path),
                "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # Dodaj sekcję AI
        ai_data = {
            "AI_processing_date": datetime.now().isoformat(),
            "AI_model_info": {
                "name": "sentence-transformers/all-MiniLM-L6-v2",
                "type": "SBERT",
                "version": "1.0",
            },
            "AI_file_analysis": {
                "total_archive_files": len(archive_files),
                "total_image_files": len(image_files),
                "archive_files": archive_files,
                "image_files": image_files,
            },
        }

        # Znajdź dopasowania AI
        if archive_files and image_files:
            logger.info("🤖 Uruchamiam analizę AI...")
            if progress_callback:
                progress_callback("🤖 Uruchamiam analizę AI...")

            start_time = time.time()

            matches = self.matcher.find_best_matches(archive_files, image_files)

            ai_time = time.time() - start_time
            logger.info(f"⏱️ Analiza AI zakończona w {ai_time:.2f}s")
            if progress_callback:
                progress_callback(f"⏱️ Analiza AI zakończona w {ai_time:.2f}s")

            ai_data["AI_matches"] = matches
            ai_data["AI_statistics"] = {
                "total_possible_pairs": len(archive_files) * len(image_files),
                "found_matches": len(matches),
                "match_rate": len(matches) / len(archive_files) if archive_files else 0,
                "processing_time_seconds": ai_time,
                "high_confidence_matches": len(
                    [m for m in matches if m["confidence_level"] == "HIGH"]
                ),
                "medium_confidence_matches": len(
                    [m for m in matches if m["confidence_level"] == "MEDIUM"]
                ),
            }

            # Dodaj szczegółowe analizy dla najlepszych dopasowań
            detailed_analyses = []
            for match in matches[:3]:  # Tylko 3 najlepsze dla oszczędności miejsca
                analysis = self.matcher.analyze_similarity_details(
                    match["archive_file"], match["image_file"]
                )
                detailed_analyses.append(analysis)

            ai_data["AI_detailed_analysis_samples"] = detailed_analyses

            if progress_callback:
                progress_callback(f"✅ Znaleziono {len(matches)} dopasowań AI")

        else:
            ai_data["AI_matches"] = []
            ai_data["AI_statistics"] = {
                "total_possible_pairs": 0,
                "found_matches": 0,
                "match_rate": 0,
                "reason": "Brak plików archiwów lub obrazów do dopasowania",
            }

        # Dodaj dane AI do index_data
        for key, value in ai_data.items():
            index_data[key] = value

        # Zapisz plik
        self.save_index_with_ai_data(folder_path, index_data)

        return True

    def process_folder_recursive(self, root_folder_path: str, progress_callback=None):
        """
        Przetwarza folder rekurencyjnie (łącznie z podfolderami)
        """
        logger.info(f"🚀 Rozpoczynam rekurencyjne przetwarzanie AI: {root_folder_path}")

        if progress_callback:
            progress_callback(
                f"🚀 Rozpoczynam rekurencyjne przetwarzanie AI: {root_folder_path}"
            )

        processed_folders = 0
        error_folders = 0

        try:
            for root, dirs, files in os.walk(root_folder_path, onerror=lambda e: logger.error(f"Błąd podczas chodzenia po katalogu: {e}")):
                try:
                    # Pomiń linki symboliczne
                    if os.path.islink(root):
                        continue

                    # Sprawdź czy folder zawiera index.json (został już przeskanowany)
                    index_json_path = os.path.join(root, "index.json")
                    if not os.path.exists(index_json_path):
                        logger.debug(f"⏭️ Pomijam folder bez index.json: {root}")
                        continue

                    logger.info(f"📁 Przetwarzam AI dla folderu: {root}")
                    if progress_callback:
                        progress_callback(f"📁 Przetwarzam AI dla folderu: {root}")

                    if self.process_folder(root, progress_callback):
                        processed_folders += 1
                    else:
                        error_folders += 1

                except UnicodeEncodeError as e:
                    logger.error(f"Błąd kodowania w folderze {root}: {e}")
                    error_folders += 1
                    continue
                except OSError as e:
                    logger.error(f"Błąd systemowy w folderze {root}: {e}")
                    error_folders += 1
                    continue
                except Exception as e:
                    logger.error(f"Nieoczekiwany błąd w folderze {root}: {e}")
                    error_folders += 1
                    continue

        except Exception as e:
            logger.error(f"Krytyczny błąd podczas rekurencyjnego przetwarzania: {e}")
            if progress_callback:
                progress_callback(f"❌ Krytyczny błąd: {e}")

        success_msg = f"✅ Przetwarzanie AI zakończone: {processed_folders} folderów OK, {error_folders} błędów"
        logger.info(success_msg)
        if progress_callback:
            progress_callback(success_msg)

        return processed_folders > 0

    def start_ai_processing(self, progress_callback=None):
        """Rozpoczyna przetwarzanie AI od folderu roboczego z konfiguracji"""
        if not self.work_directory:
            logger.error("Brak folderu roboczego w konfiguracji")
            if progress_callback:
                progress_callback("❌ Brak folderu roboczego w konfiguracji")
            return False

        if not os.path.isdir(self.work_directory):
            logger.error(f"Folder roboczy nie istnieje: {self.work_directory}")
            if progress_callback:
                progress_callback(
                    f"❌ Folder roboczy nie istnieje: {self.work_directory}"
                )
            return False

        logger.info(f"🤖 Rozpoczynam przetwarzanie AI dla: {self.work_directory}")
        if progress_callback:
            progress_callback(
                f"🤖 Rozpoczynam przetwarzanie AI dla: {self.work_directory}"
            )

        return self.process_folder_recursive(self.work_directory, progress_callback)


def main():
    """
    Funkcja główna - automatycznie pobiera folder roboczy z konfiguracji
    """
    print("🤖 AI SBERT File Matcher - Automatyczne przetwarzanie")
    print("=" * 60)

    # Utwórz procesor i sprawdź konfigurację
    processor = AIFolderProcessor()

    if not processor.work_directory:
        print("❌ Brak folderu roboczego w konfiguracji!")
        print("💡 Uruchom najpierw główną aplikację i ustaw folder roboczy.")
        return

    print(f"📁 Folder roboczy z konfiguracji: {processor.work_directory}")

    if not os.path.exists(processor.work_directory):
        print(f"❌ Folder roboczy nie istnieje: {processor.work_directory}")
        return

    # Zapytaj o tryb przetwarzania
    print("\n🔄 Tryby przetwarzania:")
    print("1. Automatyczne (cały folder roboczy)")
    print("2. Konkretny folder")
    print("3. Wyjście")

    choice = input("\nWybierz opcję (1-3): ").strip()

    if choice == "1":
        # Automatyczne przetwarzanie całego folderu roboczego
        print(f"\n🚀 Rozpoczynam automatyczne przetwarzanie AI...")
        processor.start_ai_processing(print)

    elif choice == "2":
        # Konkretny folder
        test_folder = input("Podaj ścieżkę do konkretnego folderu: ").strip()
        if not test_folder:
            print("❌ Nie podano ścieżki")
            return

        if not os.path.exists(test_folder):
            print(f"❌ Folder nie istnieje: {test_folder}")
            return

        print(f"🔍 Przetwarzam konkretny folder: {test_folder}")
        processor.process_folder_recursive(test_folder, print)

    elif choice == "3":
        print("👋 Do widzenia!")
        return
    else:
        print("❌ Nieprawidłowy wybór")
        return

    print("\n🎉 Przetwarzanie AI zakończone! Sprawdź pliki index.json w folderach.")
    print("🔍 Wyszukaj klucze zaczynające się od 'AI_' aby zobaczyć wyniki.")


def generate_ai_only_gallery_data(folder_path: str) -> Dict:
    """
    Generuje dane galerii zawierające tylko dopasowania AI
    """
    index_path = os.path.join(folder_path, "index.json")

    if not os.path.exists(index_path):
        logger.warning(f"Brak index.json w {folder_path}")
        return {}

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Błąd odczytu index.json w {folder_path}: {e}")
        return {}

    # Sprawdź czy są dane AI
    if "AI_matches" not in data:
        logger.debug(f"Brak danych AI_matches w {folder_path}")
        return {}

    ai_matches = data.get("AI_matches", [])
    if not ai_matches:
        logger.debug(f"Pusta lista AI_matches w {folder_path}")
        return {}

    logger.info(
        f"Generuję dane galerii AI dla {folder_path} z {len(ai_matches)} dopasowaniami"
    )

    # Utwórz strukturę danych tylko z dopasowaniami AI
    ai_gallery_data = {
        "folder_info": data.get("folder_info", {}).copy(),
        "files_with_previews": [],
        "files_without_previews": [],
        "other_images": [],
        "ai_info": {
            "processing_date": data.get("AI_processing_date"),
            "model_info": data.get("AI_model_info", {}),
            "statistics": data.get("AI_statistics", {}),
            "total_matches": len(ai_matches),
        },
    }

    # Dodaj informacje AI do folder_info
    ai_gallery_data["folder_info"]["gallery_type"] = "AI_POWERED"
    ai_gallery_data["folder_info"]["ai_matches_count"] = len(ai_matches)
    ai_gallery_data["folder_info"]["ai_scan_date"] = data.get("AI_processing_date")

    # Konwertuj dopasowania AI na format galerii
    processed_matches = 0
    for match in ai_matches:
        archive_file = match.get("archive_file")
        image_file = match.get("image_file")

        if not archive_file or not image_file:
            logger.warning(f"Niepełne dopasowanie AI: {match}")
            continue

        # Znajdź pełne ścieżki plików
        archive_path = os.path.join(folder_path, archive_file)
        image_path = os.path.join(folder_path, image_file)

        if not os.path.exists(archive_path):
            logger.warning(f"Plik archiwum nie istnieje: {archive_path}")
            continue

        if not os.path.exists(image_path):
            logger.warning(f"Plik obrazu nie istnieje: {image_path}")
            continue

        try:
            archive_size = os.path.getsize(archive_path)
        except OSError:
            archive_size = 0

        file_info = {
            "name": archive_file,
            "path_absolute": os.path.abspath(archive_path),
            "size_bytes": archive_size,
            "size_readable": get_file_size_readable_ai(archive_size),
            "preview_found": True,
            "preview_name": image_file,
            "preview_path_absolute": os.path.abspath(image_path),
            "preview_relative_path": f"file:///{os.path.abspath(image_path).replace(os.sep, '/')}",
            "archive_link": f"file:///{os.path.abspath(archive_path).replace(os.sep, '/')}",
            "ai_match": True,
            "ai_confidence": match.get("confidence_level", "UNKNOWN"),
            "ai_similarity_score": match.get("similarity_score", 0.0),
            "ai_matching_method": match.get("matching_method", "SBERT"),
            "ai_timestamp": match.get("timestamp"),
        }

        # Dodaj kolor archiwum jeśli dostępny
        file_ext = os.path.splitext(archive_file)[1].lower()
        try:
            import config_manager

            file_info["archive_color"] = config_manager.get_archive_color(file_ext)
        except:
            file_info["archive_color"] = "#6c757d"

        ai_gallery_data["files_with_previews"].append(file_info)
        processed_matches += 1

    logger.info(
        f"Przetworzone {processed_matches}/{len(ai_matches)} dopasowań AI dla {folder_path}"
    )

    return ai_gallery_data


def get_file_size_readable_ai(size_bytes):
    """Funkcja pomocnicza do konwersji rozmiaru pliku dla AI"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    size_float = float(size_bytes)
    while size_float >= 1024 and i < len(size_name) - 1:
        size_float /= 1024.0
        i += 1
    return f"{size_float:.2f} {size_name[i]}"


if __name__ == "__main__":
    main()
