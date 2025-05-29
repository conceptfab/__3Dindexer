Zmiana 1: Nowy moduł wykrywania sprzętu
Plik: hardware_detector.py (nowy plik)
python# hardware_detector.py
import logging
import platform
import subprocess
import os
from typing import Dict, List, Optional, Tuple

import psutil
import cpuinfo

logger = logging.getLogger(__name__)

class HardwareDetector:
    """
    Klasa do automatycznego wykrywania i optymalizacji sprzętu
    """
    
    def __init__(self):
        self.cpu_info = self._get_cpu_info()
        self.gpu_info = self._get_gpu_info()
        self.memory_info = self._get_memory_info()
        self.optimal_config = self._determine_optimal_config()
    
    def _get_cpu_info(self) -> Dict:
        """Pobiera informacje o CPU"""
        try:
            cpu_data = cpuinfo.get_cpu_info()
            cpu_cores = psutil.cpu_count(logical=False)
            cpu_threads = psutil.cpu_count(logical=True)
            
            # Wykryj producenta i architekturę
            cpu_brand = cpu_data.get('brand_raw', '').lower()
            cpu_vendor = cpu_data.get('vendor_id_raw', '').lower()
            
            is_intel = 'intel' in cpu_brand or 'genuineintel' in cpu_vendor
            is_amd = 'amd' in cpu_brand or 'authenticamd' in cpu_vendor
            is_apple_silicon = 'apple' in cpu_brand or platform.processor() == 'arm'
            
            # Wykryj instrukcje SIMD
            flags = cpu_data.get('flags', [])
            has_avx = 'avx' in flags
            has_avx2 = 'avx2' in flags
            has_avx512 = any('avx512' in flag for flag in flags)
            
            return {
                'brand': cpu_data.get('brand_raw', 'Unknown'),
                'vendor': cpu_vendor,
                'cores': cpu_cores,
                'threads': cpu_threads,
                'is_intel': is_intel,
                'is_amd': is_amd,
                'is_apple_silicon': is_apple_silicon,
                'has_avx': has_avx,
                'has_avx2': has_avx2,
                'has_avx512': has_avx512,
                'architecture': cpu_data.get('arch_string_raw', platform.machine()),
                'frequency_mhz': cpu_data.get('hz_advertised_friendly', 'Unknown')
            }
        except Exception as e:
            logger.warning(f"Błąd podczas wykrywania CPU: {e}")
            return {'brand': 'Unknown', 'cores': psutil.cpu_count() or 4, 'threads': psutil.cpu_count() or 4}
    
    def _get_gpu_info(self) -> Dict:
        """Pobiera informacje o GPU"""
        gpu_info = {
            'nvidia_available': False,
            'nvidia_devices': [],
            'amd_available': False,
            'intel_gpu_available': False,
            'apple_metal_available': False,
            'cuda_version': None,
            'memory_total_mb': 0
        }
        
        try:
            # Sprawdź NVIDIA CUDA
            import torch
            if torch.cuda.is_available():
                gpu_info['nvidia_available'] = True
                gpu_info['cuda_version'] = torch.version.cuda
                
                for i in range(torch.cuda.device_count()):
                    device_props = torch.cuda.get_device_properties(i)
                    gpu_info['nvidia_devices'].append({
                        'name': device_props.name,
                        'memory_mb': device_props.total_memory // (1024 * 1024),
                        'compute_capability': f"{device_props.major}.{device_props.minor}",
                        'multiprocessors': device_props.multi_processor_count
                    })
                    gpu_info['memory_total_mb'] += device_props.total_memory // (1024 * 1024)
            
            # Sprawdź MPS (Apple Silicon)
            if torch.backends.mps.is_available():
                gpu_info['apple_metal_available'] = True
        
        except ImportError:
            logger.info("PyTorch nie zainstalowany - brak wsparcia GPU")
        except Exception as e:
            logger.warning(f"Błąd podczas wykrywania GPU: {e}")
        
        # Sprawdź Intel GPU przez system
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                      capture_output=True, text=True, timeout=5)
                if "Intel" in result.stdout:
                    gpu_info['intel_gpu_available'] = True
            elif platform.system() == "Linux":
                result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
                if "Intel" in result.stdout and "VGA" in result.stdout:
                    gpu_info['intel_gpu_available'] = True
        except Exception:
            pass
        
        return gpu_info
    
    def _get_memory_info(self) -> Dict:
        """Pobiera informacje o pamięci RAM"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': round(mem.total / (1024**3), 2),
            'available_gb': round(mem.available / (1024**3), 2),
            'usage_percent': mem.percent
        }
    
    def _determine_optimal_config(self) -> Dict:
        """Określa optymalną konfigurację na podstawie dostępnego sprzętu"""
        config = {
            'device': 'cpu',
            'num_threads': min(self.cpu_info.get('threads', 4), 8),
            'batch_size': 32,
            'model_precision': 'float32',
            'use_fast_tokenizers': True,
            'optimization_level': 'balanced'
        }
        
        # Priorytet: NVIDIA GPU > Apple MPS > Intel/AMD z AVX > CPU podstawowy
        if self.gpu_info['nvidia_available']:
            # Konfiguracja NVIDIA CUDA
            largest_gpu = max(self.gpu_info['nvidia_devices'], key=lambda x: x['memory_mb'])
            
            config.update({
                'device': 'cuda',
                'gpu_memory_mb': largest_gpu['memory_mb'],
                'batch_size': min(128, largest_gpu['memory_mb'] // 100),  # Dynamiczny batch size
                'model_precision': 'float16' if largest_gpu['memory_mb'] > 4000 else 'float32',
                'optimization_level': 'high_performance'
            })
            
        elif self.gpu_info['apple_metal_available']:
            # Konfiguracja Apple MPS
            config.update({
                'device': 'mps',
                'batch_size': 64,
                'model_precision': 'float16',
                'optimization_level': 'high_performance'
            })
            
        elif self.cpu_info.get('has_avx2'):
            # CPU z AVX2 - zwiększona wydajność
            config.update({
                'device': 'cpu',
                'num_threads': min(self.cpu_info.get('threads', 4), 12),
                'batch_size': 64,
                'use_avx_optimization': True,
                'optimization_level': 'optimized_cpu'
            })
            
        elif self.cpu_info.get('has_avx'):
            # CPU z AVX - podstawowa optymalizacja
            config.update({
                'device': 'cpu',
                'num_threads': min(self.cpu_info.get('threads', 4), 8),
                'batch_size': 48,
                'use_avx_optimization': True,
                'optimization_level': 'basic_cpu'
            })
        
        # Dostosuj do dostępnej pamięci RAM
        if self.memory_info['available_gb'] < 4:
            config['batch_size'] = min(config['batch_size'], 16)
            config['model_precision'] = 'float32'  # Mniej pamięci ale bezpieczniej
        elif self.memory_info['available_gb'] > 16:
            config['batch_size'] = min(config['batch_size'] * 2, 256)
        
        return config
    
    def get_hardware_summary(self) -> str:
        """Zwraca podsumowanie wykrytego sprzętu"""
        summary = [
            f"🖥️  CPU: {self.cpu_info.get('brand', 'Unknown')}",
            f"⚙️  Rdzenie: {self.cpu_info.get('cores')}/{self.cpu_info.get('threads')} (fizyczne/logiczne)",
            f"💾 RAM: {self.memory_info['available_gb']:.1f}GB dostępne z {self.memory_info['total_gb']:.1f}GB",
        ]
        
        if self.cpu_info.get('has_avx512'):
            summary.append("🚀 AVX-512: Dostępne")
        elif self.cpu_info.get('has_avx2'):
            summary.append("⚡ AVX2: Dostępne")
        elif self.cpu_info.get('has_avx'):
            summary.append("📈 AVX: Dostępne")
        
        if self.gpu_info['nvidia_available']:
            for gpu in self.gpu_info['nvidia_devices']:
                summary.append(f"🎮 NVIDIA: {gpu['name']} ({gpu['memory_mb']}MB)")
        
        if self.gpu_info['apple_metal_available']:
            summary.append("🍎 Apple Metal: Dostępne")
        
        summary.append(f"⚙️  Optymalna konfiguracja: {self.optimal_config['optimization_level']}")
        summary.append(f"🔧 Urządzenie: {self.optimal_config['device'].upper()}")
        
        return "\n".join(summary)

# Singleton instance
_hardware_detector = None

def get_hardware_detector() -> HardwareDetector:
    """Zwraca singleton instance HardwareDetector"""
    global _hardware_detector
    if _hardware_detector is None:
        _hardware_detector = HardwareDetector()
    return _hardware_detector
Zmiana 2: Optymalizacja klasy SBERTFileMatcher
Plik: ai_sbert_matcher.py
Funkcja: SBERTFileMatcher.__init__
pythondef __init__(self, model_name: str = "all-MiniLM-L6-v2", auto_optimize: bool = True):
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
    self.similarity_threshold = 0.45
    self.high_confidence_threshold = 0.70
    self.very_high_confidence_threshold = 0.85
Zmiana 3: Metody optymalizacji w SBERTFileMatcher
Plik: ai_sbert_matcher.py
Dodaj nowe metody:
pythondef _setup_cpu_optimization(self):
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
Zmiana 4: Instalacja wymaganych bibliotek
Plik: requirements_hardware.txt (nowy plik)
txt# Podstawowe biblioteki (już obecne)
sentence-transformers
numpy
scikit-learn

# Nowe biblioteki do wykrywania sprzętu
psutil>=5.9.0
py-cpuinfo>=9.0.0

# PyTorch z obsługą CUDA/CPU (automatyczne wykrywanie)
torch>=2.0.0
torchvision>=0.15.0
torchaudio>=2.0.0

# Opcjonalne akceleratory Intel
# mkl>=2023.0.0  # Odkomentuj dla Intel CPU
# intel-extension-for-pytorch  # Odkomentuj dla Intel GPU
Zmiana 5: Aktualizacja głównej klasy AIFolderProcessor
Plik: ai_sbert_matcher.py
Funkcja: AIFolderProcessor.__init__
pythondef __init__(self, enable_hardware_optimization: bool = True):
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
Zmiana 6: Funkcja main z informacjami o sprzęcie
Plik: ai_sbert_matcher.py
Funkcja: main
pythondef main():
    """
    Funkcja główna z wyświetlaniem informacji o sprzęcie
    """
    print("🤖 AI SBERT File Matcher - Automatyczne przetwarzanie")
    print("=" * 60)

    # Wyświetl informacje o sprzęcie
    try:
        from hardware_detector import get_hardware_detector
        detector = get_hardware_detector()
        print("\n🔍 WYKRYTE SPRZĘT:")
        print("-" * 40)
        print(detector.get_hardware_summary())
    except ImportError:
        print("\n⚠️  Moduł wykrywania sprzętu niedostępny")
        print("💡 Zainstaluj: pip install psutil py-cpuinfo torch")
    except Exception as e:
        print(f"\n⚠️  Błąd wykrywania sprzętu: {e}")

    print("\n" + "=" * 60)

    # Utwórz procesor i sprawdź konfigurację
    processor = AIFolderProcessor(enable_hardware_optimization=True)

    if not processor.work_directory:
        print("❌ Brak folderu roboczego w konfiguracji!")
        print("💡 Uruchom najpierw główną aplikację i ustaw folder roboczy.")
        return

    print(f"📁 Folder roboczy z konfiguracji: {processor.work_directory}")

    if not os.path.exists(processor.work_directory):
        print(f"❌ Folder roboczy nie istnieje: {processor.work_directory}")
        return

    # Reszta funkcji bez zmian...
    print("\n🔄 Tryby przetwarzania:")
    print("1. Automatyczne (cały folder roboczy)")
    print("2. Konkretny folder")
    print("3. Test wydajności sprzętu")
    print("4. Wyjście")

    choice = input("\nWybierz opcję (1-4): ").strip()

    if choice == "1":
        print(f"\n🚀 Rozpoczynam automatyczne przetwarzanie AI...")
        processor.start_ai_processing(print)
    elif choice == "2":
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
        # Test wydajności
        print("\n🧪 Test wydajności sprzętu...")
        test_files = [f"test_file_{i}.zip" for i in range(100)]
        start_time = time.time()
        embeddings = processor.matcher.calculate_embeddings(test_files)
        test_time = time.time() - start_time
        print(f"⏱️  Test 100 plików: {test_time:.2f}s ({100/test_time:.1f} plików/s)")
    elif choice == "4" or choice == "":
        print("👋 Do widzenia!")
        return
    else:
        print("❌ Nieprawidłowy wybór")
        return

    print("\n🎉 Przetwarzanie AI zakończone! Sprawdź pliki index.json w folderach.")
Podsumowanie zmian
Zmiany dodają kompleksową optymalizację sprzętową, która automatycznie:

Wykrywa sprzęt: CPU (Intel/AMD), GPU (NVIDIA CUDA, Apple MPS), pamięć RAM
Optymalizuje CPU: Instrukcje AVX/AVX2/AVX-512, wielowątkowość
Wykorzystuje GPU: CUDA dla NVIDIA, MPS dla Apple Silicon
Dostosowuje parametry: Batch size, precyzja, liczba wątków
Monitoruje wydajność: Czas przetwarzania, przepustowość

Kod automatycznie wybierze najlepszą konfigurację dla dostępnego sprzętu bez ingerencji użytkownika.