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