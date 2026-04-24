/**
 * Generische Funktion zum Löschen von Einträgen (Werkzeuge, Verbrauchsmaterialien, Mitarbeiter)
 * @param {string} type - Der Typ des Eintrags ('tool', 'consumable', 'worker')
 * @param {string} barcode - Der Barcode des zu löschenden Eintrags
 * @returns {Promise} - Ein Promise mit dem Ergebnis der Löschoperation
 */
async function deleteItem(type, barcode) {
    const typeNames = {'tool': 'Werkzeug', 'consumable': 'Verbrauchsmaterial', 'worker': 'Mitarbeiter'};
    const confirmed = await window.confirmAction({
        title: `${typeNames[type]} löschen?`,
        message: `Möchten Sie ${type === 'worker' ? 'diesen' : 'dieses'} ${typeNames[type]} wirklich in den Papierkorb verschieben?`,
        confirmText: 'Löschen', confirmClass: 'btn-error'
    });
    if (!confirmed) return;
    
    // Barcode bereinigen
    const cleanBarcode = barcode.trim();
    
    // URL und Request-Konfiguration - alle verwenden jetzt Barcode im JSON-Body
    const urls = {
        'tool': '/admin/tools/delete',
        'consumable': '/admin/consumables/delete',
        'worker': '/admin/workers/delete'
    };
    
    const url = urls[type];
    const requestConfig = {
        method: 'DELETE',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ barcode: cleanBarcode })
    };
    
    try {
        const response = await fetch(url, requestConfig);
        const data = await response.json();
        if (data.success) {
            showNotification(data.message || `${typeNames[type]} gelöscht`, 'success');
            const row = document.querySelector(`[data-barcode="${cleanBarcode}"]`);
            if (row) { row.remove(); if (window.updateSearchUI) window.updateSearchUI(); }
            else window.location.reload();
        } else throw new Error(data.message);
    } catch (error) {
        showNotification(error.message || 'Fehler beim Löschen', 'error');
    }
}

/**
 * Zeigt eine Benachrichtigung an
 * @param {string} message - Die anzuzeigende Nachricht
 * @param {string} type - Der Typ der Nachricht ('success', 'error', 'info', 'warning')
 */
function showNotification(message, type = 'info') {
    // Prüfe ob Toast-Container existiert
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        `;
        document.body.appendChild(container);
    }
    
    // Toast-Element erstellen
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 4px;
        color: white;
        opacity: 0;
        transition: opacity 0.3s ease-in;
    `;
    
    // Hintergrundfarbe basierend auf Typ
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    toast.style.backgroundColor = colors[type] || colors.info;
    
    // Nachricht einfügen
    toast.textContent = message;
    
    // Toast anzeigen
    container.appendChild(toast);
    setTimeout(() => toast.style.opacity = '1', 10);
    
    // Toast nach 3 Sekunden ausblenden und entfernen
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
} 