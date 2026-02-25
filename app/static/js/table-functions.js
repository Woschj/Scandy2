function initializeTable(tableId, options = {}) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const searchInput = document.getElementById('searchInput');
    const tbody = table.querySelector('tbody');
    // Nur echte Daten-Zeilen (nicht die "Keine Ergebnisse"-Zeile)
    const rows = Array.from(tbody.querySelectorAll('tr:not(#noResultsRow)'));
    let sortDirection = {};

    // Filter-Funktion
    function filterTable() {
        const searchTerm = searchInput?.value.toLowerCase() || '';
        const filters = {};
        
        // Sammle alle aktiven Filter
        document.querySelectorAll('select[id^="filter"]').forEach(select => {
            filters[select.id] = select.value.toLowerCase();
        });

        rows.forEach(row => {
            let showRow = true;
            
            // Suche
            if (searchTerm) {
                const text = row.textContent.toLowerCase();
                showRow = text.includes(searchTerm);
            }

            // Filter
            if (showRow) {
                Object.entries(filters).forEach(([filterId, filterValue]) => {
                    if (filterValue) {
                        const columnIndex = options.filterColumns?.[filterId] || 0;
                        const cell = row.cells[columnIndex];
                        const cellText = cell?.textContent.toLowerCase() || '';
                        showRow = showRow && cellText.includes(filterValue);
                    }
                });
            }

            row.style.display = showRow ? '' : 'none';
        });
        checkNoResults();
    }

    // Hilfsfunktion für "Keine Ergebnisse"
    function checkNoResults() {
        const noResultsRow = document.getElementById('noResultsRow');
        if (!noResultsRow) return;

        const visibleRowsCount = rows.filter(row => row.style.display !== 'none').length;
        noResultsRow.style.display = visibleRowsCount === 0 ? '' : 'none';
    }

    // Sortier-Funktion
    function sortTable(columnIndex) {
        const direction = sortDirection[columnIndex] = !sortDirection[columnIndex];
        
        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex].textContent.trim();
            const bValue = b.cells[columnIndex].textContent.trim();
            
            if (direction) {
                return aValue.localeCompare(bValue);
            } else {
                return bValue.localeCompare(aValue);
            }
        });

        rows.forEach(row => tbody.appendChild(row));
    }

    // Event Listener
    if (searchInput) {
        searchInput.addEventListener('input', filterTable);
    }

    document.querySelectorAll('select[id^="filter"]').forEach(select => {
        select.addEventListener('change', filterTable);
    });

    // Sortierbare Spalten
    table.querySelectorAll('th').forEach((th, index) => {
        if (!th.classList.contains('no-sort')) {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => sortTable(index));
        }
    });
} 