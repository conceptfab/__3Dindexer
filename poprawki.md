Zmiany w pliku: templates/gallery_template.html
Poprawka JavaScript w szablonie
html<script>
// Przekazanie danych z Pythona do JS dla większej niezawodności
window.galleryConfig = {
    currentFolderAbsPath: {{ folder_info.path_absolute | tojson | safe if folder_info and folder_info.path_absolute else 'null' }},
    isRootIndex: {{ is_root_gallery_index | tojson | safe }},
    scannedRootPath: {{ scanned_root_path_abs_for_template | tojson | safe }}
};

console.log("Gallery Config from Python:", window.galleryConfig);

function getCurrentFolder() {
  if (window.galleryConfig && window.galleryConfig.currentFolderAbsPath) {
      return window.galleryConfig.currentFolderAbsPath.replace(/\\/g, '/');
  }
  console.warn("getCurrentFolder: Fallback, window.galleryConfig.currentFolderAbsPath not available.");
  // POPRAWIONE: Usunięcie błędnego .format()
  const fallbackPath = {{ folder_info.path_absolute | tojson | safe if folder_info and folder_info.path_absolute else "'.'"}};
  return fallbackPath.replace(/\\/g, '/');
}
window.getCurrentFolder = getCurrentFolder;

document.addEventListener('DOMContentLoaded', function () {
  console.log('=== ROZPOCZYNAM INICJALIZACJĘ GALERII ===');
  
  const galleries = [
    document.getElementById('filesWithPreviewsGallery'),
  ].filter(Boolean);

  const previewModal = document.getElementById('previewModal');
  const previewBackdrop = document.getElementById('previewBackdrop');
  const previewImg = document.getElementById('previewImg');
  const matchBtn = document.getElementById('matchPreviewBtn');
  const matchStatus = document.getElementById('matchStatus');

  console.log('Elementy galerii:', {
    galleries: galleries.length,
    previewModal: !!previewModal,
    matchBtn: !!matchBtn
  });

  function showPreview(imageSrc) {
    console.log('showPreview wywołane z:', imageSrc);
    if (!imageSrc) return;
    if (!previewModal || !previewBackdrop || !previewImg) {
      console.error('Brak elementów modal');
      return;
    }
    previewImg.src = imageSrc;
    previewModal.classList.add('show');
    previewBackdrop.classList.add('show');
    console.log('Podgląd wyświetlony');
  }

  function hidePreview() {
    console.log('hidePreview wywołane');
    if (!previewModal || !previewBackdrop || !previewImg) return;
    previewModal.classList.remove('show');
    previewBackdrop.classList.remove('show');
    previewImg.src = '';
  }

  // === OBSŁUGA PODGLĄDU OBRAZÓW ===
  console.log('Inicjalizuję obsługę podglądu obrazów...');
  
  // Obrazy w galerii z podglądem
  galleries.forEach((gallery) => {
    const images = gallery.querySelectorAll('.preview-image');
    console.log(`Znaleziono ${images.length} obrazów podglądu w galerii`);
    
    images.forEach((img, index) => {
      console.log(`Dodaję listenery do obrazu ${index}:`, img.src);
      let hoverTimeout;
      
      img.addEventListener('mouseenter', function () {
        console.log('MOUSEENTER na obrazie:', this.src);
        hoverTimeout = setTimeout(() => {
          console.log('Timeout - pokazuję podgląd obrazu');
          showPreview(this.src);
        }, 1000); // Zmniejszone na 1 sekundę dla testów
      });
      
      img.addEventListener('mouseleave', function () {
        console.log('MOUSELEAVE na obrazie');
        clearTimeout(hoverTimeout);
        hidePreview();
      });
    });
  });

  // Linki podglądu w prawej kolumnie
  const previewLinks = document.querySelectorAll('.preview-link');
  console.log(`Znaleziono ${previewLinks.length} linków podglądu`);
  
  previewLinks.forEach((link, index) => {
    const previewSrc = link.getAttribute('data-preview-src');
    console.log(`Link ${index} ma data-preview-src:`, previewSrc);
    
    let hoverTimeout;
    link.addEventListener('mouseenter', function () {
      const src = this.getAttribute('data-preview-src');
      console.log('MOUSEENTER na linku z src:', src);
      if (src) {
        hoverTimeout = setTimeout(() => {
          console.log('Timeout - pokazuję podgląd linku');
          showPreview(src);
        }, 1000);
      }
    });
    
    link.addEventListener('mouseleave', function () {
      console.log('MOUSELEAVE na linku');
      clearTimeout(hoverTimeout);
      hidePreview();
    });
  });

  // Zamykanie podglądu
  if (previewBackdrop) {
    previewBackdrop.addEventListener('click', hidePreview);
  }
  if (previewModal) {
    previewModal.addEventListener('click', (e) => { 
      if(e.target === previewModal) hidePreview(); 
    });
  }
  document.addEventListener('keydown', function (e) { 
    if (e.key === 'Escape') hidePreview(); 
  });

  // === OBSŁUGA PRZYCISKU DOPASOWANIA ===
  if (matchBtn) {
    console.log('=== INICJALIZUJĘ FUNKCJĘ DOPASOWANIA ===');
    
    let localStorageAvailable = false;
    try {
        if (typeof Storage !== 'undefined' && localStorage) {
            localStorage.setItem('test','test');
            localStorage.removeItem('test');
            localStorageAvailable = true;
            console.log('localStorage jest dostępny');
        }
    } catch (e) {
        console.warn('localStorage nie jest dostępny:', e);
    }

    if (!localStorageAvailable) {
        matchBtn.style.display = 'none';
        if(matchStatus) matchStatus.textContent = '⚠️ Funkcje uczenia niedostępne.';
        return;
    }

    // POPRAWIONY SELEKTOR - wszystkie checkboxy
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    console.log('=== CHECKBOXY ===');
    console.log('Wszystkich checkboxów:', checkboxes.length);
    
    // Debugowanie każdego checkboxa
    checkboxes.forEach((cb, i) => {
      console.log(`Checkbox ${i}:`, {
        file: cb.dataset.file,
        type: cb.dataset.type,
        hasGalleryClass: cb.classList.contains('gallery-checkbox'),
        hasFileClass: cb.classList.contains('file-checkbox')
      });
    });

    function updateMatchButton() {
        console.log('=== AKTUALIZUJĘ STAN PRZYCISKU ===');
        
        const archiveChecked = [];
        const imageChecked = [];
        
        checkboxes.forEach((cb) => {
            if (cb.checked) {
                const isArchive = cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox');
                const isImage = cb.dataset.type === 'image';
                
                console.log(`Zaznaczony checkbox ${cb.dataset.file}:`, {
                  type: cb.dataset.type,
                  isArchive,
                  isImage,
                  hasGalleryClass: cb.classList.contains('gallery-checkbox')
                });
                
                if (isArchive) {
                    archiveChecked.push(cb);
                } else if (isImage) {
                    imageChecked.push(cb);
                }
            }
        });

        console.log('Archiwów zaznaczonych:', archiveChecked.length);
        console.log('Obrazów zaznaczonych:', imageChecked.length);

        const canMatch = archiveChecked.length === 1 && imageChecked.length === 1;
        matchBtn.disabled = !canMatch;

        if (matchStatus) {
            if (canMatch) {
                const archiveName = archiveChecked[0].dataset.file;
                const imageName = imageChecked[0].dataset.file;
                matchStatus.textContent = `Gotowy: ${archiveName} ↔ ${imageName}`;
                console.log('PRZYCISK AKTYWNY - gotowy do dopasowania');
            } else if (archiveChecked.length === 0 && imageChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 archiwum i 1 obraz';
            } else if (archiveChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 archiwum';
            } else if (imageChecked.length === 0) {
                matchStatus.textContent = 'Zaznacz 1 obraz';
            } else {
                matchStatus.textContent = 'Zaznacz tylko 1 archiwum i 1 obraz';
            }
        }
    }

    // DODAJ LISTENERY DO WSZYSTKICH CHECKBOXÓW
    checkboxes.forEach((checkbox, index) => {
        console.log(`Dodaję listener do checkboxa ${index}:`, checkbox.dataset.file);
        
        checkbox.addEventListener('change', function () {
            console.log(`=== CHECKBOX ZMIENIONY ===`);
            console.log('Plik:', this.dataset.file);
            console.log('Nowy stan:', this.checked);
            console.log('Typ:', this.dataset.type);
            
            if (this.checked) {
                const currentType = this.dataset.type || (this.classList.contains('gallery-checkbox') ? 'archive' : 'unknown');
                console.log('Typ bieżącego checkboxa:', currentType);
                
                // Odznacz inne checkboxy tego samego typu
                checkboxes.forEach((otherCb) => {
                    if (otherCb !== this) {
                        const otherType = otherCb.dataset.type || (otherCb.classList.contains('gallery-checkbox') ? 'archive' : 'unknown');
                        if (otherType === currentType && otherCb.checked) {
                            console.log(`Odznaczam ${otherCb.dataset.file} (ten sam typ)`);
                            otherCb.checked = false;
                        }
                    }
                });
            }
            updateMatchButton();
        });
    });

    matchBtn.addEventListener('click', function () {
        console.log('=== KLIKNIĘTO PRZYCISK DOPASOWANIA ===');
        
        const archiveCb = Array.from(checkboxes).find(cb => {
            return cb.checked && (cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox'));
        });
        const imageCb = Array.from(checkboxes).find(cb => {
            return cb.checked && cb.dataset.type === 'image';
        });

        console.log('Znaleziony checkbox archiwum:', archiveCb?.dataset.file);
        console.log('Znaleziony checkbox obrazu:', imageCb?.dataset.file);

        if (archiveCb && imageCb) {
            const getBasename = (filename) => {
                const lastDotIndex = filename.lastIndexOf('.');
                return lastDotIndex > 0 ? filename.substring(0, lastDotIndex) : filename;
            };

            const matchData = {
                archiveFile: archiveCb.dataset.file,
                archivePath: archiveCb.dataset.path.replace(/\\/g, '/'),
                imageFile: imageCb.dataset.file,
                imagePath: imageCb.dataset.path.replace(/\\/g, '/'),
                archiveBasename: getBasename(archiveCb.dataset.file),
                imageBasename: getBasename(imageCb.dataset.file),
                timestamp: new Date().toISOString(),
                currentFolder: getCurrentFolder()
            };

            console.log('🎯 ZAPISUJĘ DOPASOWANIE:', matchData);

            const matchKey = 'learningMatch_' + Date.now();
            localStorage.setItem(matchKey, JSON.stringify(matchData));
            localStorage.setItem('latestLearningMatch', matchKey);

            if(matchStatus) matchStatus.textContent = '✅ Zapisano! Nauka algorytmu...';
            matchBtn.disabled = true;
            matchBtn.textContent = '⏳ Przetwarzanie...';

            // Odznacz checkboxy
            archiveCb.checked = false;
            imageCb.checked = false;

            setTimeout(() => {
                matchBtn.disabled = false;
                matchBtn.textContent = '🎯 Dopasuj podgląd';
                if(matchStatus) matchStatus.textContent = '';
                updateMatchButton();
            }, 3000);
        } else {
            console.error('NIE ZNALEZIONO ODPOWIEDNICH CHECKBOXÓW!');
        }
    });

    // Inicjalne sprawdzenie
    updateMatchButton();
    console.log('=== DOPASOWANIE ZAINICJALIZOWANE ===');
  } else {
    console.log('Brak przycisku dopasowania na tej stronie');
  }

  // Pozostałe funkcje (usuwanie, localStorage itp.)
  const deleteButtons = document.querySelectorAll('.delete-image-btn');
  deleteButtons.forEach((button) => {
    button.addEventListener('click', function (e) {
      e.preventDefault(); 
      e.stopPropagation();
      const filePath = this.dataset.filePath;
      const fileName = this.dataset.fileName;
      if (confirm(`Czy na pewno chcesz usunąć plik "${fileName}" do kosza?`)) {
        try {
          if (typeof Storage === 'undefined' || !localStorage) { 
            alert('Funkcja usuwania nie jest dostępna.'); 
            return; 
          }
          const deleteData = { 
            action: 'deleteFile', 
            filePath: filePath, 
            fileName: fileName, 
            timestamp: new Date().toISOString() 
          };
          console.log('🗑️ Usuwanie pliku:', deleteData);
          const deleteKey = 'deleteFile_' + Date.now();
          localStorage.setItem(deleteKey, JSON.stringify(deleteData));
          localStorage.setItem('latestDelete', deleteKey);
          this.textContent = '⏳'; 
          this.disabled = true; 
          this.style.opacity = '0.5';
        } catch (err) { 
          console.error('Błąd usuwania pliku:', err); 
          alert('Wystąpił błąd podczas usuwania.'); 
        }
      }
    });
  });

  // Przywracanie rozmiaru kafelków z localStorage
  if (typeof localStorage !== 'undefined' && localStorage.getItem('galleryTileSize')) {
      const savedSize = localStorage.getItem('galleryTileSize');
      const galleriesToResize = document.querySelectorAll('.gallery');
      galleriesToResize.forEach(gallery => {
          gallery.style.gridTemplateColumns = `repeat(auto-fill, minmax(${savedSize}px, 1fr))`;
      });
  }

  console.log('=== INICJALIZACJA GALERII ZAKOŃCZONA ===');
});
</script>
Główne poprawki:

Usunięcie błędnego .format() w funkcji getCurrentFolder()
Dodanie szczegółowego debugowania - console.log w każdym kroku
Skrócenie czasu hover z 2000ms na 1000ms dla szybszego testowania
Lepsze sprawdzanie elementów modal przed użyciem
Dodanie logowania dla każdego checkboxa i jego właściwości
Sprawdzenie czy funkcja updateMatchButton działa poprawnie

Jak debugować:

Otwórz konsolę przeglądarki (F12)
Odśwież galerię
Sprawdź komunikaty inicjalizacji
Zaznacz archiwum i obraz
Sprawdź czy w konsoli pojawiają się komunikaty o zmianie checkboxów
Sprawdź czy przycisk "Dopasuj podgląd" staje się aktywny

Jeśli nadal nie działa, wyślij mi zrzut ekranu konsoli z błędami!