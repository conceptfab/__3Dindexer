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

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", auto_optimize: bool = True):
        """
        Inicjalizacja z automatyczną optymalizacją sprzętową
        
        Args:
            model_name: Nazwa modelu SBERT
            auto_optimize: Czy automatycznie optymalizować dla dostępnego sprzętu
        """
        self.hardware_config = None
        
        if auto_optimize:
            try:
                from hardware_detector import get_hardware_detector
                detector = get_hardware_detector()
                self.hardware_config = detector.optimal_config
                
                logger.info("🔍 Wykryte sprzęt:")
                logger.info(detector.get_hardware_summary())
                
            except ImportError as e:
                logger.warning(f"Moduł hardware_detector niedostępny: {e}")
                auto_optimize = False
            except Exception as e:
                logger.warning(f"Błąd automatycznej optymalizacji: {e}")
                auto_optimize = False
        
        # Ustaw zmienne środowiskowe dla optymalizacji CPU
        if auto_optimize and self.hardware_config:
            self._setup_cpu_optimization()
        
        logger.info(f"Ładowanie modelu SBERT: {model_name}")
        start_time = time.time()

        try:
            # Konfiguracja device i model
            device = self._get_optimal_device() if auto_optimize else None
            
            if device:
                logger.info(f"🚀 Używam urządzenia: {device}")
                self.model = SentenceTransformer(model_name, device=device)
            else:
                self.model = SentenceTransformer(model_name)
            
            # Optymalizacje modelu
            if auto_optimize and self.hardware_config:
                self._apply_model_optimizations()
            
            load_time = time.time() - start_time
            logger.info(f"Model załadowany w {load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Błąd ładowania modelu: {e}")
            logger.info("Próbuję załadować model bez optymalizacji...")
            self.model = SentenceTransformer(model_name)

        # Zachowaj oryginalne progi
        self.similarity_threshold = 0.30
        self.high_confidence_threshold = 0.60
        self.very_high_confidence_threshold = 0.80
        self.low_similarity_threshold = 0.20

    def _setup_cpu_optimization(self):
        """Konfiguruje optymalizacje CPU"""
        if not self.hardware_config:
            return
        
        # Ustaw liczbę wątków
        num_threads = str(self.hardware_config.get('num_threads', 4))
        os.environ['OMP_NUM_THREADS'] = num_threads
        os.environ['MKL_NUM_THREADS'] = num_threads
        os.environ['NUMEXPR_NUM_THREADS'] = num_threads
        
        # Optymalizacje Intel MKL
        if self.hardware_config.get('optimization_level') in ['optimized_cpu', 'basic_cpu']:
            os.environ['MKL_ENABLE_INSTRUCTIONS'] = 'AVX2' if self.hardware_config.get('use_avx_optimization') else 'SSE4_2'
        
        logger.info(f"🔧 CPU zoptymalizowany: {num_threads} wątków")

    def _get_optimal_device(self) -> Optional[str]:
        """Zwraca optymalne urządzenie dla modelu"""
        if not self.hardware_config:
            return None
        
        device_type = self.hardware_config.get('device', 'cpu')
        
        if device_type == 'cuda':
            try:
                import torch
                if torch.cuda.is_available():
                    return 'cuda'
            except ImportError:
                logger.warning("PyTorch/CUDA niedostępne")
        
        elif device_type == 'mps':
            try:
                import torch
                if torch.backends.mps.is_available():
                    return 'mps'
            except ImportError:
                logger.warning("PyTorch/MPS niedostępne")
        
        return 'cpu'

    def _apply_model_optimizations(self):
        """Stosuje optymalizacje modelu"""
        if not self.hardware_config:
            return
        
        try:
            # Optymalizacja precyzji dla GPU
            if self.hardware_config.get('device') in ['cuda', 'mps'] and self.hardware_config.get('model_precision') == 'float16':
                self.model = self.model.half()
                logger.info("🔧 Model przełączony na float16")
            
            # Kompilacja modelu dla PyTorch 2.0+
            if hasattr(self.model, '_modules'):
                try:
                    import torch
                    if hasattr(torch, 'compile') and torch.__version__ >= '2.0':
                        self.model = torch.compile(self.model, mode='reduce-overhead')
                        logger.info("🚀 Model skompilowany z PyTorch 2.0")
                except Exception as e:
                    logger.debug(f"Kompilacja modelu nieudana: {e}")
            
        except Exception as e:
            logger.warning(f"Błąd podczas optymalizacji modelu: {e}")

    def preprocess_filename(self, filename: str) -> str:
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

    def calculate_embeddings(self, filenames: List[str]) -> np.ndarray:
        """
        Oblicza embeddings z optymalizacjami sprzętowymi
        """
        if not filenames:
            return np.array([])

        processed_names = [self.preprocess_filename(name) for name in filenames]
        
        logger.debug(f"Obliczanie embeddings dla {len(processed_names)} plików")
        start_time = time.time()

        # Użyj optymalnego batch_size
        batch_size = self.hardware_config.get('batch_size', 32) if self.hardware_config else 32
        
        try:
            # Oblicz embeddings z optymalnym batch_size
            embeddings = self.model.encode(
                processed_names, 
                batch_size=batch_size,
                show_progress_bar=len(processed_names) > 50,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalizacja dla lepszej wydajności cosine similarity
            )
            
            calc_time = time.time() - start_time
            performance_info = f"Embeddings obliczone w {calc_time:.2f}s"
            
            if self.hardware_config:
                items_per_second = len(processed_names) / calc_time if calc_time > 0 else 0
                performance_info += f" ({items_per_second:.1f} plików/s, batch_size: {batch_size})"
            
            logger.debug(performance_info)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Błąd podczas obliczania embeddings: {e}")
            # Fallback bez optymalizacji
            return self.model.encode(processed_names, show_progress_bar=False)

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
            if best_image_idx == -1:
                for j, image_file in enumerate(image_files):
                    if j in used_images:
                        continue
                    
                    simple_similarity = self.simple_string_similarity(archive_file, image_file)
                    if simple_similarity > best_similarity and simple_similarity >= self.low_similarity_threshold:
                        best_similarity = simple_similarity
                        best_image_idx = j
                        best_method = "SIMPLE_MATCH"

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

            if best_image_idx != -1:
                used_images.add(best_image_idx)
                matches.append({
                    "archive_file": archive_file,
                    "image_file": image_files[best_image_idx],
                    "similarity": float(best_similarity),
                    "method": best_method
                })

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
                    "simple_threshold_met": simple_sim >= self.low_similarity_threshold,
                    "would_match": sbert_sim >= self.similarity_threshold or simple_sim >= self.low_similarity_threshold
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

    def debug_specific_case(self, archive_name: str, image_name: str) -> Dict:
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
        debug_result["simple_threshold_met"] = simple_sim >= self.low_similarity_threshold
        
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
    Klasa do przetwarzania folderów z wykorzystaniem AI
    """

    def __init__(self, enable_hardware_optimization: bool = True):
        """
        Inicjalizacja z opcjonalną optymalizacją sprzętową
        """
        # Utwórz matcher z optymalizacją sprzętową
        self.matcher = SBERTFileMatcher(auto_optimize=enable_hardware_optimization)
        
        # Pobierz folder roboczy z konfiguracji
        self.work_directory = get_work_directory_from_config()
        if not self.work_directory:
            logger.warning("Brak folderu roboczego w konfiguracji")
        
        # Loguj informacje o optymalizacji
        if enable_hardware_optimization and hasattr(self.matcher, 'hardware_config') and self.matcher.hardware_config:
            optimization_level = self.matcher.hardware_config.get('optimization_level', 'basic')
            device = self.matcher.hardware_config.get('device', 'cpu').upper()
            logger.info(f"🚀 AI Procesor zoptymalizowany: {optimization_level} na {device}")

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
            # Dodaj obsługę kodowania UTF-8
            folder_path = os.path.abspath(folder_path)
            
            for entry in os.scandir(folder_path):
                if time.time() - start_time > SCAN_TIMEOUT_SECONDS:
                    logger.warning(f"⏰ Przekroczono limit czasu skanowania ({SCAN_TIMEOUT_SECONDS}s) w folderze {folder_path}")
                    break

                try:
                    if entry.is_file(follow_symlinks=False):
                        # Użyj str() zamiast bezpośredniego odczytu name
                        filename = str(entry.name).lower()

                        if filename == "index.json":
                            continue

                        if filename.endswith(IMAGE_EXTENSIONS):
                            image_files.append(str(entry.name))
                        else:
                            # Wszystkie inne pliki traktujemy jako archiwa/modele
                            archive_files.append(str(entry.name))
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

        # Sprawdź czy istnieje index.json
        index_json_path = os.path.join(folder_path, "index.json")
        if not os.path.exists(index_json_path):
            # Utwórz podstawowy index.json jeśli nie istnieje
            logger.info(f"📝 Tworzę nowy index.json dla: {folder_path}")
            if progress_callback:
                progress_callback(f"📝 Tworzę nowy index.json dla: {folder_path}")
            
            basic_index_data = {
                "folder_info": {
                    "path": os.path.abspath(folder_path),
                    "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_size_bytes": 0,
                    "file_count": 0,
                    "subdir_count": 0,
                    "archive_count": 0
                },
                "files_with_previews": [],
                "files_without_previews": [],
                "other_images": []
            }
            
            try:
                with open(index_json_path, "w", encoding="utf-8") as f:
                    json.dump(basic_index_data, f, indent=4, ensure_ascii=False)
                logger.info(f"✅ Utworzono index.json dla: {folder_path}")
            except Exception as e:
                logger.error(f"❌ Błąd tworzenia index.json dla {folder_path}: {e}")
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
            # Dodaj obsługę kodowania UTF-8
            root_folder_path = os.path.abspath(root_folder_path)
            
            for root, dirs, files in os.walk(root_folder_path, onerror=lambda e: logger.error(f"Błąd podczas chodzenia po katalogu: {e}")):
                try:
                    # Pomiń linki symboliczne
                    if os.path.islink(root):
                        continue

                    # Konwertuj ścieżkę na UTF-8
                    root = str(root)
                    
                    # Sprawdź czy folder zawiera index.json
                    index_json_path = os.path.join(root, "index.json")
                    if not os.path.exists(index_json_path):
                        # Utwórz podstawowy index.json jeśli nie istnieje
                        logger.info(f"📝 Tworzę nowy index.json dla: {root}")
                        if progress_callback:
                            progress_callback(f"📝 Tworzę nowy index.json dla: {root}")
                        
                        basic_index_data = {
                            "folder_info": {
                                "path": os.path.abspath(root),
                                "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "total_size_bytes": 0,
                                "file_count": 0,
                                "subdir_count": 0,
                                "archive_count": 0
                            },
                            "files_with_previews": [],
                            "files_without_previews": [],
                            "other_images": []
                        }
                        
                        try:
                            with open(index_json_path, "w", encoding="utf-8") as f:
                                json.dump(basic_index_data, f, indent=4, ensure_ascii=False)
                            logger.info(f"✅ Utworzono index.json dla: {root}")
                        except Exception as e:
                            logger.error(f"❌ Błąd tworzenia index.json dla {root}: {e}")
                            error_folders += 1
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
    Główna funkcja programu
    """
    print("\n🤖 AI File Matcher - Dopasowywanie plików")
    print("=" * 50)
    
    while True:
        print("\n📋 Dostępne opcje:")
        print("1. Przetwórz folder")
        print("2. Przetwórz folder rekurencyjnie")
        print("3. Wygeneruj galerię AI")
        print("4. Wyjście")
        print("5. Test konkretnego przypadku")
        
        choice = input("\nWybierz opcję (1-5): ").strip()
        
        if choice == "1":
            folder_path = input("\nPodaj ścieżkę do folderu: ").strip()
            if folder_path:
                processor = AIFolderProcessor()
                processor.process_folder(folder_path)
            else:
                print("❌ Nie podano ścieżki")
                
        elif choice == "2":
            folder_path = input("\nPodaj ścieżkę do folderu głównego: ").strip()
            if folder_path:
                processor = AIFolderProcessor()
                processor.process_folder_recursive(folder_path)
            else:
                print("❌ Nie podano ścieżki")
                
        elif choice == "3":
            folder_path = input("\nPodaj ścieżkę do folderu: ").strip()
            if folder_path:
                gallery_data = generate_ai_only_gallery_data(folder_path)
                print("\n✅ Galeria AI wygenerowana")
            else:
                print("❌ Nie podano ścieżki")
                
        elif choice == "4":
            print("\n👋 Do widzenia!")
            break
            
        elif choice == "5":
            # Test konkretnego przypadku
            print("\n🔍 Test konkretnego przypadku:")
            archive_name = input("Podaj nazwę pliku archiwum: ").strip()
            image_name = input("Podaj nazwę pliku obrazu: ").strip()
            
            if archive_name and image_name:
                processor = AIFolderProcessor()
                debug_result = processor.matcher.debug_specific_case(archive_name, image_name)
                print("\n📊 WYNIKI DEBUGOWANIA:")
                print("-" * 50)
                import json
                print(json.dumps(debug_result, indent=2, ensure_ascii=False))
            else:
                print("❌ Nie podano nazw plików")
                
        else:
            print("❌ Nieprawidłowa opcja")


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
