Plik templates/gallery_styles.css - DODAJ STYLE DLA DWÓCH KOLUMN
css/* DWIE KOLUMNY NA DOLE */
.bottom-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-top: 32px;
}

.left-column, .right-column {
  /* Każda kolumna zajmuje 50% szerokości */
}

.image-list {
  list-style: none;
  padding: 0;
  background: var(--bg-tertiary);
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
}

.image-list li {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-muted);
  transition: var(--transition);
}

.image-list li:last-child {
  border-bottom: none;
}

.image-list li:hover {
  background: var(--bg-quaternary);
}

.image-list a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
}

.image-list a:hover {
  color: var(--accent);
}

/* RESPONSIVE dla dwóch kolumn */
@media (max-width: 768px) {
  .bottom-columns {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}

/* Reszta stylów bez zmian... */
Co zostało naprawione:

✅ USUNIĘTO NAGŁÓWEK H1 - zostaje tylko breadcrumb ze ścieżką
✅ USUNIĘTO NAGŁÓWEK "📁 Podfoldery" - zbędny tekst
✅ DWIE KOLUMNY NA DOLE - "Pliki bez podglądu" po lewej, "Pozostałe obrazy" po prawej
✅ RESPONSIVE - na mobile kolumny się układają jedna pod drugą
✅ JEDNOLITY LAYOUT - wszystkie strony wyglądają tak samo

Teraz na górze jest TYLKO ŚCIEŻKA i dół ma DWE KOLUMNY!