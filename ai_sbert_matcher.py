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

        # Parametry dopasowywania
        self.similarity_threshold = 0.65  # Minimalny próg podobieństwa
        self.high_confidence_threshold = 0.80  # Próg wysokiej pewności

    def preprocess_filename(self, filename: str) -> str:
        """
        Przygotowuje nazwę pliku do analizy przez model
        """
        # Usuń rozszerzenie
        name_without_ext = os.path.splitext(filename)[0]

        # Zamień różne separatory na spacje
        processed = re.sub(r"[_\-\.]", " ", name_without_ext)

        # Usuń wielokrotne spacje
        processed = re.sub(r"\s+", " ", processed)

        # Wydziel i oznacz typowe sufiksy
        suffixes = [
            "preview",
            "thumb",
            "thumbnail",
            "render",
            "final",
            "draft",
            "v1",
            "v2",
            "v3",
            "version",
            "copy",
            "backup",
            "temp",
        ]

        for suffix in suffixes:
            if suffix in processed.lower():
                processed = processed.replace(suffix.lower(), f" {suffix.upper()}")
                processed = processed.replace(suffix.upper(), f" {suffix.upper()}")

        # Wydziel numery wersji
        processed = re.sub(r"(\d+)", r" \1 ", processed)

        # Czyść wielokrotne spacje
        processed = re.sub(r"\s+", " ", processed).strip()

        logger.debug(f"Preprocessing: '{filename}' -> '{processed}'")
        return processed

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

    def find_best_matches(
        self, archive_files: List[str], image_files: List[str]
    ) -> List[Dict]:
        """
        Znajduje najlepsze dopasowania między plikami archiwów a obrazami
        """
        if not archive_files or not image_files:
            logger.warning("Brak plików do dopasowania")
            return []

        logger.info(
            f"Szukanie dopasowań: {len(archive_files)} archiwów vs {len(image_files)} obrazów"
        )

        # Oblicz embeddings
        archive_embeddings = self.calculate_embeddings(archive_files)
        image_embeddings = self.calculate_embeddings(image_files)

        # Oblicz podobieństwa
        similarities = cosine_similarity(archive_embeddings, image_embeddings)

        matches = []
        used_images = set()

        # Dla każdego archiwum znajdź najlepszy obraz
        for i, archive_file in enumerate(archive_files):
            best_similarity = 0.0
            best_image_idx = -1

            for j, image_file in enumerate(image_files):
                if j in used_images:
                    continue  # Ten obraz już został użyty

                similarity = similarities[i][j]
                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_image_idx = j

            if best_image_idx != -1:
                image_file = image_files[best_image_idx]
                used_images.add(best_image_idx)

                confidence_level = (
                    "HIGH"
                    if best_similarity >= self.high_confidence_threshold
                    else "MEDIUM"
                )

                match_info = {
                    "archive_file": archive_file,
                    "image_file": image_file,
                    "similarity_score": float(best_similarity),
                    "confidence_level": confidence_level,
                    "matching_method": "SBERT",
                    "timestamp": datetime.now().isoformat(),
                }

                matches.append(match_info)
                logger.info(
                    f"✅ Dopasowanie [{confidence_level}]: '{archive_file}' ↔ '{image_file}' (score: {best_similarity:.3f})"
                )
            else:
                logger.debug(f"❌ Brak dopasowania dla: '{archive_file}'")

        logger.info(
            f"Znaleziono {len(matches)} dopasowań z {len(archive_files)} archiwów"
        )
        return matches

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

        try:
            for entry in os.scandir(folder_path):
                if entry.is_file(follow_symlinks=False):
                    filename = entry.name.lower()

                    if filename == "index.json":
                        continue

                    if filename.endswith(IMAGE_EXTENSIONS):
                        image_files.append(entry.name)
                    else:
                        # Wszystkie inne pliki traktujemy jako archiwa/modele
                        archive_files.append(entry.name)

        except OSError as e:
            logger.error(f"Błąd skanowania folderu {folder_path}: {e}")

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

        for root, dirs, files in os.walk(root_folder_path):
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


if __name__ == "__main__":
    main()
