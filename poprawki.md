Widzę problemy! Oto poprawki do templates/gallery_template.html:
Poprawka JavaScript w szablonie
html<script>
document.addEventListener('DOMContentLoaded', function () {
    const galleries = [
      document.getElementById('filesWithPreviewsGallery'),
    ].filter(Boolean);

    const previewModal = document.getElementById('previewModal');
    const previewBackdrop = document.getElementById('previewBackdrop');
    const previewImg = document.getElementById('previewImg');
    const matchBtn = document.getElementById('matchPreviewBtn');
    const matchStatus = document.getElementById('matchStatus');

    function showPreview(imageSrc) {
      if (!imageSrc) return;
      console.log('Pokazuję podgląd:', imageSrc);
      previewImg.src = imageSrc;
      previewModal.classList.add('show');
      previewBackdrop.classList.add('show');
    }

    function hidePreview() {
      previewModal.classList.remove('show');
      previewBackdrop.classList.remove('show');
      previewImg.src = '';
    }

    // === OBSŁUGA PODGLĄDU OBRAZÓW - HOVER Z OPÓŹNIENIEM ===
    galleries.forEach((gallery) => {
      const images = gallery.querySelectorAll('.preview-image');
      images.forEach((img) => {
        let hoverTimeout;
        img.addEventListener('mouseenter', function () { 
          hoverTimeout = setTimeout(() => { 
            console.log('Hover na obrazie, pokazuję podgląd');
            showPreview(this.src); 
          }, 2000); // ZMIENIONO NA 2 SEKUNDY
        });
        img.addEventListener('mouseleave', function () { 
          clearTimeout(hoverTimeout); 
          hidePreview(); // DODANO - ukryj od razu po opuszczeniu
        });
      });
    });

    const previewLinks = document.querySelectorAll('.preview-link');
    previewLinks.forEach((link) => {
      let hoverTimeout;
      link.addEventListener('mouseenter', function () {
        const previewSrc = this.getAttribute('data-preview-src');
        if (previewSrc) { 
          hoverTimeout = setTimeout(() => { 
            console.log('Hover na linku, pokazuję podgląd:', previewSrc);
            showPreview(previewSrc); 
          }, 2000); // ZMIENIONO NA 2 SEKUNDY
        }
      });
      link.addEventListener('mouseleave', function () { 
        clearTimeout(hoverTimeout); 
        hidePreview(); // DODANO - ukryj od razu po opuszczeniu
      });
    });

    previewBackdrop.addEventListener('click', hidePreview);
    previewModal.addEventListener('click', (e) => { if(e.target === previewModal) hidePreview(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hidePreview(); });

    // === FUNKCJA DOPASOWANIA PODGLĄDU - NAPRAWIONA ===
    if (matchBtn) {
      console.log('Inicjalizuję funkcję dopasowania podglądu');
      
      let localStorageAvailable = false;
      try {
          if (typeof Storage !== 'undefined' && localStorage) {
              localStorage.setItem('test','test');
              localStorage.removeItem('test');
              localStorageAvailable = true;
              console.log('localStorage dostępny');
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
      console.log('Znaleziono checkboxów:', checkboxes.length);

      function updateMatchButton() {
          console.log('Aktualizuję stan przycisku dopasowania');
          
          const archiveChecked = Array.from(checkboxes).filter(cb => {
              const isArchive = cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox');
              console.log(`Checkbox ${cb.dataset.file}: checked=${cb.checked}, isArchive=${isArchive}`);
              return cb.checked && isArchive;
          });
          
          const imageChecked = Array.from(checkboxes).filter(cb => {
              const isImage = cb.dataset.type === 'image';
              console.log(`Checkbox ${cb.dataset.file}: checked=${cb.checked}, isImage=${isImage}`);
              return cb.checked && isImage;
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
                  console.log('Przycisk gotowy do dopasowania');
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
              console.log(`Checkbox ${this.dataset.file} zmieniony na:`, this.checked);
              
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
          console.log('Kliknięto przycisk dopasowania');
          
          const archiveCb = Array.from(checkboxes).find(cb => {
              return cb.checked && (cb.dataset.type === 'archive' || cb.classList.contains('gallery-checkbox'));
          });
          const imageCb = Array.from(checkboxes).find(cb => {
              return cb.checked && cb.dataset.type === 'image';
          });

          console.log('Znaleziony checkbox archiwum:', archiveCb?.dataset.file);
          console.log('Znaleziony checkbox obrazu:', imageCb?.dataset.file);

          if (archiveCb && imageCb) {
              // Pobierz basename z nazwy pliku
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

              console.log('🎯 Zapisuję dopasowanie:', matchData);

              const matchKey = 'learningMatch_' + Date.now();
              localStorage.setItem(matchKey, JSON.stringify(matchData));
              localStorage.setItem('latestLearningMatch', matchKey);

              if(matchStatus) matchStatus.textContent = '✅ Zapisano! Nauka algorytmu...';
              matchBtn.disabled = true;
              matchBtn.textContent = '⏳ Przetwarzanie...';

              // Odznacz checkboxy
              archiveCb.checked = false;
              imageCb.checked = false;

              // Przywróć stan przycisku po 3 sekundach
              setTimeout(() => {
                  matchBtn.disabled = false;
                  matchBtn.textContent = '🎯 Dopasuj podgląd';
                  if(matchStatus) matchStatus.textContent = '';
                  updateMatchButton(); // Odśwież stan
              }, 3000);
          } else {
              console.error('Nie znaleziono odpowiednich checkboxów!');
          }
      });

      // Inicjalne sprawdzenie
      updateMatchButton();
    }

    // Reszta kodu pozostaje bez zmian...
    // [usuwanie plików, localStorage itp.]
    
    const deleteButtons = document.querySelectorAll('.delete-image-btn');
    deleteButtons.forEach((button) => {
      button.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        const filePath = this.dataset.filePath;
        const fileName = this.dataset.fileName;
        if (confirm(`Czy na pewno chcesz usunąć plik "${fileName}" do kosza?`)) {
          try {
            if (typeof Storage === 'undefined' || !localStorage) { alert('Funkcja usuwania nie jest dostępna.'); return; }
            const deleteData = { action: 'deleteFile', filePath: filePath, fileName: fileName, timestamp: new Date().toISOString() };
            console.log('🗑️ Usuwanie pliku:', deleteData);
            const deleteKey = 'deleteFile_' + Date.now();
            localStorage.setItem(deleteKey, JSON.stringify(deleteData));
            localStorage.setItem('latestDelete', deleteKey);
            this.textContent = '⏳'; this.disabled = true; this.style.opacity = '0.5';
            const statusDiv = document.createElement('div');
            statusDiv.className = 'file-operation-notification warning';
            statusDiv.textContent = `⏳ Usuwanie "${fileName}"...`;
            document.body.appendChild(statusDiv);
            setTimeout(() => { if (statusDiv.parentNode) statusDiv.parentNode.removeChild(statusDiv); }, 5000);
          } catch (err) { console.error('Błąd usuwania pliku:', err); alert('Wystąpił błąd podczas usuwania.'); }
        }
      });
    });

    // Logika dla przywracania rozmiaru kafelków z localStorage
    if (typeof localStorage !== 'undefined' && localStorage.getItem('galleryTileSize')) {
        const savedSize = localStorage.getItem('galleryTileSize');
        const galleriesToResize = document.querySelectorAll('.gallery');
        galleriesToResize.forEach(gallery => {
            gallery.style.gridTemplateColumns = `repeat(auto-fill, minmax(${savedSize}px, 1fr))`;
        });
    }
});
</script>
Główne poprawki:

Selektor checkboxów: Zmieniono z document.querySelectorAll('.file-checkbox, .gallery-checkbox') na document.querySelectorAll('input[type="checkbox"]') - to złapie wszystkie checkboxy
Opóźnienie podglądu: Zmieniono z 1000ms na 2000ms (2 sekundy)
Ukrywanie podglądu: Dodano hidePreview() w mouseleave aby podgląd znikał od razu po opuszczeniu
Debugowanie: Dodano console.log() w kluczowych miejscach żeby zobaczyć co się dzieje
Inicjalizacja: Dodano sprawdzenie czy funkcje są poprawnie inicjalizowane

Testowanie:

Otwórz konsolę przeglądarki (F12)
Zaznacz archiwum i obraz
Sprawdź czy w konsoli pojawiają się komunikaty o znalezionych checkboxach
Sprawdź czy przycisk "Dopasuj podgląd" staje się aktywny

Jeśli dalej nie działa, sprawdź w konsoli:

Ile checkboxów zostało znalezionych
Jakie typy mają zaznaczone checkboxy
Czy localStorage zapisuje dane

Te informacje pomogą dalej debugować problem.