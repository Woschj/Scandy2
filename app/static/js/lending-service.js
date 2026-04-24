// Lending Service - Zentrale Verwaltung für Ausleihe/Rückgabe
(function() {
    'use strict';

    // Utility-Funktionen
    function log(message, data = null) {
        // Logging deaktiviert für Produktion
    }

    // Service-Initialisierung
    function initializeLendingService() {
        log('=== LENDING SERVICE INITIALIZATION START ===');
        log('Script location:', document.currentScript?.src || 'Unknown location');

        // Event-Listener für Rückgabe-Buttons
        initializeReturnButtons();

        // Event-Listener für Ausleihe-Buttons
        initializeLendButtons();

        // Event-Listener für Material-Entnahme
        initializeMaterialConsumption();

        // Event-Listener für Arbeitszeiten
        initializeWorkTimeTracking();

        log('=== LENDING SERVICE INITIALIZATION COMPLETE ===');
    }

    // Rückgabe-Funktionalität
    async function returnTool(barcode, button = null) {
        log('Starte Rückgabe für:', barcode);
        const confirmed = await window.confirmAction({
            title: 'Werkzeug zurückgeben?',
            message: 'Möchten Sie dieses Werkzeug wirklich zurückgeben?',
            confirmText: 'Rückgabe'
        });
        if (!confirmed) {
            if (button) { button.disabled = false; button.style.opacity = '1'; }
            return;
        }
        try {
            const response = await fetch('/api/lending/return', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tool_barcode: barcode})
            });
            const result = await response.json();
            if (result.success) {
                showLendingToast('success', 'Werkzeug erfolgreich zurückgegeben');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showLendingToast('error', result.message || 'Fehler bei der Rückgabe');
                if (button) { button.disabled = false; button.style.opacity = '1'; }
            }
        } catch (error) {
            showLendingToast('error', 'Ein Fehler ist aufgetreten');
            if (button) { button.disabled = false; button.style.opacity = '1'; }
        }
    }

    // Ausleihe-Funktionalität
    function lendTool(toolBarcode, workerBarcode) {
        fetch('/api/lending/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tool_barcode: toolBarcode,
                worker_barcode: workerBarcode,
                action: 'lend'
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showLendingToast('success', 'Werkzeug erfolgreich ausgeliehen');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showLendingToast('error', result.message || 'Fehler bei der Ausleihe');
            }
        })
        .catch(error => {
            showLendingToast('error', 'Ein Fehler ist aufgetreten');
        });
    }

    // Material-Verbrauch
    function consumeMaterial(materialBarcode, workerBarcode, quantity) {
        fetch('/api/lending/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                item_barcode: materialBarcode,
                worker_barcode: workerBarcode,
                action: 'consume',
                item_type: 'consumable',
                quantity: quantity
            })
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showLendingToast('success', 'Material erfolgreich entnommen');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                showLendingToast('error', result.message || 'Fehler bei der Materialentnahme');
            }
        })
        .catch(error => {
            showLendingToast('error', 'Ein Fehler ist aufgetreten');
        });
    }

    // Event-Listener für Rückgabe-Buttons
    function initializeReturnButtons() {
        log('Initialisiere Event-Listener');

        // Event-Delegation statt individuelle Event-Listener
        document.addEventListener('click', function(e) {
            const button = e.target.closest('[data-action="return"]');
            if (!button) return;

            e.preventDefault();
            e.stopPropagation();

            const barcode = button.dataset.barcode;
            if (!barcode) return;

            // Verhindere mehrfache Klicks
            if (button.disabled) return;

            button.disabled = true;
            button.style.opacity = '0.6';

            // Sofortige visuelle Rückmeldung
            requestAnimationFrame(() => {
                returnTool(barcode, button);
            });
        });
    }

    // Event-Listener für Ausleihe-Buttons
    function initializeLendButtons() {
        function addLendButtonListeners() {
            const lendButtons = document.querySelectorAll('[data-action="lend"]');

            lendButtons.forEach(button => {
                const barcode = button.dataset.barcode;
                log('Initialisiere Button mit Barcode:', barcode);

                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    const workerBarcode = prompt('Bitte geben Sie den Mitarbeiter-Barcode ein:');
                    if (workerBarcode) {
                        lendTool(barcode, workerBarcode);
                    }
                });
            });
        }

        addLendButtonListeners();
    }

    // Material-Verbrauch Event-Listener
    function initializeMaterialConsumption() {
        // Material-Zeile hinzufügen - nur wenn materialContainer existiert (für Lending)
        const materialContainer = document.getElementById('materialContainer');
        if (materialContainer) {
            window.addMaterialRow = function() {
                log('Füge neue Materialzeile hinzu (Lending)');
                const materialRow = document.createElement('div');
                materialRow.className = 'material-row flex gap-2 mb-2';
                materialRow.innerHTML = `
                    <input type="text" name="material_barcode[]" placeholder="Material-Barcode" class="input input-bordered flex-1" required>
                    <input type="number" name="material_quantity[]" placeholder="Menge" class="input input-bordered w-24" min="1" value="1" required>
                    <button type="button" class="btn btn-error btn-sm" onclick="removeMaterialRow(this)">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
                materialContainer.appendChild(materialRow);
            };
        }

        // Material-Zeile entfernen - nur wenn materialContainer existiert (für Lending)
        if (materialContainer) {
            window.removeMaterialRow = function(button) {
                log('Entferne Materialzeile (Lending)');
                button.closest('.material-row').remove();
            };
        }
    }

    // Arbeitszeiten Event-Listener
    function initializeWorkTimeTracking() {
        // Arbeitszeit-Zeile hinzufügen - nur wenn workTimeContainer existiert
        const workTimeContainer = document.getElementById('workTimeContainer');
        if (workTimeContainer) {
            window.addWorkTimeRow = function() {
                log('Füge neue Arbeitszeile hinzu');
                const workTimeRow = document.createElement('div');
                workTimeRow.className = 'work-time-row flex gap-2 mb-2';
                workTimeRow.innerHTML = `
                    <input type="date" name="work_date[]" class="input input-bordered" required>
                    <input type="number" name="work_hours[]" placeholder="Stunden" class="input input-bordered w-24" min="0.5" step="0.5" value="8" required>
                    <input type="text" name="work_description[]" placeholder="Beschreibung" class="input input-bordered flex-1" required>
                    <button type="button" class="btn btn-error btn-sm" onclick="removeWorkTimeRow(this)">
                        <i class="fas fa-trash"></i>
                    </button>
                `;
                workTimeContainer.appendChild(workTimeRow);
            };

            // Arbeitszeit-Zeile entfernen
            window.removeWorkTimeRow = function(button) {
                log('Entferne Arbeitszeile');
                button.closest('.work-time-row').remove();
            };
        }
    }

    // Auftragsdetails speichern
    window.saveAuftragDetails = function(ticketId) {
        log('Leite zur Auftragsdetails-Seite weiter...');

        // Sammle alle Formulardaten
        const formData = new FormData();

        // Material-Daten
        const materialBarcodes = document.querySelectorAll('input[name="material_barcode[]"]');
        const materialQuantities = document.querySelectorAll('input[name="material_quantity[]"]');

        for (let i = 0; i < materialBarcodes.length; i++) {
            if (materialBarcodes[i].value && materialQuantities[i].value) {
                formData.append('material_barcode[]', materialBarcodes[i].value);
                formData.append('material_quantity[]', materialQuantities[i].value);
            }
        }

        // Arbeitszeit-Daten
        const workDates = document.querySelectorAll('input[name="work_date[]"]');
        const workHours = document.querySelectorAll('input[name="work_hours[]"]');
        const workDescriptions = document.querySelectorAll('input[name="work_description[]"]');

        for (let i = 0; i < workDates.length; i++) {
            if (workDates[i].value && workHours[i].value && workDescriptions[i].value) {
                formData.append('work_date[]', workDates[i].value);
                formData.append('work_hours[]', workHours[i].value);
                formData.append('work_description[]', workDescriptions[i].value);
            }
        }

        // Speichere Daten
        fetch(`/tickets/${ticketId}/auftrag-details`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showLendingToast('success', 'Auftragsdetails erfolgreich gespeichert');
                setTimeout(() => {
                    window.location.href = `/tickets/${ticketId}/auftrag-details`;
                }, 1000);
            } else {
                showLendingToast('error', result.message || 'Fehler beim Speichern');
            }
        })
        .catch(error => {
            showLendingToast('error', 'Ein Fehler ist aufgetreten');
        });
    };

    // Toast-Funktion
    function showLendingToast(type, message) {
        // Verwende globale showToast Funktion oder Fallback
        if (typeof window.showToast === 'function') {
            window.showLendingToast(type, message);
        } else {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type} fixed bottom-4 right-4 z-50`;
            toast.innerHTML = `
                <div class="alert alert-${type}">
                    <span>${message}</span>
                </div>
            `;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.remove();
            }, 3000);
        }
    }

    // Globale returnItem-Funktion für manuelle Ausleihe
    window.LendingService = {
        returnItem: async function(barcode) {
            const button = event?.target?.closest('[data-action="return"]');
            if (button) { button.disabled = true; button.style.opacity = '0.6'; }
            const confirmed = await window.confirmAction({
                title: 'Werkzeug zurückgeben?',
                message: 'Möchten Sie dieses Werkzeug wirklich zurückgeben?',
                confirmText: 'Rückgabe'
            });
            if (!confirmed) {
                if (button) { button.disabled = false; button.style.opacity = '1'; }
                return false;
            }
            try {
                const response = await fetch('/api/lending/return', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                    body: JSON.stringify({tool_barcode: barcode, worker_barcode: null})
                });
                const result = await response.json();
                if (result.success) {
                    showLendingToast('success', 'Werkzeug erfolgreich zurückgegeben');
                    return true;
                } else {
                    showLendingToast('error', result.message || 'Fehler bei der Rückgabe');
                    if (button) { button.disabled = false; button.style.opacity = '1'; }
                    return false;
                }
            } catch (error) {
                showLendingToast('error', 'Ein Fehler ist aufgetreten');
                if (button) { button.disabled = false; button.style.opacity = '1'; }
                return false;
            }
        }
    };

    // Auftragsdetails-Funktionen (für Ticket-Details-Seite)
    function initializeAuftragDetails() {
        log('Initialisiere Auftragsdetails-Funktionen');

        // Material-Zeile hinzufügen für Auftragsdetails (Tabelle)
        const materialRows = document.getElementById('materialRows');
        if (materialRows) {
            window.addMaterialRow = function() {
                log('Füge neue Materialzeile hinzu (Auftragsdetails)');
                const newRow = document.createElement('tr');
                newRow.className = 'material-row';
                newRow.innerHTML = `
                    <td><input type="text" name="material" class="material-input input input-bordered w-full"></td>
                    <td><input type="number" name="menge" class="menge-input input input-bordered w-24" min="0" step="any"></td>
                    <td><input type="number" name="einzelpreis" class="einzelpreis-input input input-bordered w-24" min="0" step="any"></td>
                    <td><input type="text" name="gesamtpreis" class="input input-bordered w-32" readonly></td>
                    <td><button type="button" class="btn btn-error btn-sm delete-material-btn"><i class="fas fa-trash"></i></button></td>
                `;
                materialRows.appendChild(newRow);
                initializeMaterialRowEvents(newRow);
            };
        }

        // Arbeit-Zeile hinzufügen für Auftragsdetails
        const arbeitenRows = document.getElementById('arbeitenRows');
        if (arbeitenRows) {
            window.addArbeitRow = function() {
                log('Füge neue Arbeitszeile hinzu (Auftragsdetails)');
                const newRow = document.createElement('tr');
                newRow.className = 'arbeit-row';
                newRow.innerHTML = `
                    <td><input type="text" name="arbeit" class="arbeit-input input input-bordered w-full"></td>
                    <td><input type="number" name="arbeitsstunden" class="arbeitsstunden-input input input-bordered w-full" min="0" step="0.5"></td>
                    <td><input type="text" name="leistungskategorie" class="leistungskategorie-input input input-bordered w-full"></td>
                    <td><button type="button" class="btn btn-error btn-sm delete-arbeit-btn"><i class="fas fa-trash"></i></button></td>
                `;
                arbeitenRows.appendChild(newRow);
                initializeArbeitRowEvents(newRow);
            };
        }

        // Event-Listener für bestehende Zeilen initialisieren
        initializeExistingRows();

        // Initiale Berechnungen durchführen
        updateSummeMaterial();
        updateSummeArbeit();
        updateGesamtsumme();
    }

    // Hilfsfunktionen für Auftragsdetails
    function initializeMaterialRowEvents(row) {
        // Event-Listener für Menge und Einzelpreis
        const mengeInput = row.querySelector('.menge-input');
        const einzelpreisInput = row.querySelector('.einzelpreis-input');

        if (mengeInput) {
            mengeInput.addEventListener('input', () => {
                updateRowSum(row);
            });
        }

        if (einzelpreisInput) {
            einzelpreisInput.addEventListener('input', () => {
                updateRowSum(row);
            });
        }

        // Event-Listener für Löschen-Button
        const deleteBtn = row.querySelector('.delete-material-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                row.remove();
                updateSummeMaterial();
                updateGesamtsumme();
            });
        }

        // Initiale Berechnung
        updateRowSum(row);
    }

    function initializeArbeitRowEvents(row) {
        // Event-Listener für Arbeitsstunden
        const arbeitsstundenInput = row.querySelector('.arbeitsstunden-input');
        if (arbeitsstundenInput) {
            arbeitsstundenInput.addEventListener('input', () => {
                updateSummeArbeit();
                updateGesamtsumme();
            });
        }

        // Event-Listener für Löschen-Button
        const deleteBtn = row.querySelector('.delete-arbeit-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                row.remove();
                updateSummeArbeit();
                updateGesamtsumme();
            });
        }
    }

    function initializeExistingRows() {
        // Materialzeilen
        document.querySelectorAll('#materialRows .material-row').forEach(row => {
            initializeMaterialRowEvents(row);
        });

        // Arbeitszeilen
        document.querySelectorAll('#arbeitenRows .arbeit-row').forEach(row => {
            initializeArbeitRowEvents(row);
        });
    }

    function updateRowSum(row) {
        const mengeInput = row.querySelector('.menge-input');
        const einzelpreisInput = row.querySelector('.einzelpreis-input');
        const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');

        if (!mengeInput || !einzelpreisInput || !gesamtpreisInput) {
            return;
        }

        const menge = parseFloat(mengeInput.value) || 0;
        const einzelpreis = parseFloat(einzelpreisInput.value) || 0;
        const gesamtpreis = menge * einzelpreis;

        gesamtpreisInput.value = gesamtpreis.toFixed(2);

        updateSummeMaterial();
        updateGesamtsumme();
    }

    function updateSummeMaterial() {
        let summe = 0;

        document.querySelectorAll('#materialRows .material-row').forEach(row => {
            const gesamtpreisInput = row.querySelector('input[name="gesamtpreis"]');
            if (gesamtpreisInput) {
                const gesamtpreis = parseFloat(gesamtpreisInput.value) || 0;
                summe += gesamtpreis;
            }
        });

        const summeElement = document.getElementById('summeMaterial');
        if (summeElement) {
            summeElement.textContent = summe.toFixed(2) + ' €';
            log('Materialsumme gesetzt auf:', summe.toFixed(2));
        }

        updateGesamtsumme();
    }

    function updateSummeArbeit() {
        let summe = 0;

        document.querySelectorAll('#arbeitenRows .arbeit-row').forEach(row => {
            const arbeitsstundenInput = row.querySelector('.arbeitsstunden-input');
            if (arbeitsstundenInput) {
                const stunden = parseFloat(arbeitsstundenInput.value) || 0;
                summe += stunden;
            }
        });

        const summeElement = document.getElementById('summeArbeit');
        if (summeElement) {
            summeElement.textContent = summe.toFixed(2) + ' h';
            log('Arbeitssumme gesetzt auf:', summe.toFixed(2));
        }

        updateGesamtsumme();
    }

    function updateGesamtsumme() {
        const summeMaterialElement = document.getElementById('summeMaterial');
        const gesamtsummeElement = document.getElementById('gesamtsumme');

        if (!summeMaterialElement || !gesamtsummeElement) {
            return;
        }

        const summeMaterialText = summeMaterialElement.textContent;
        const summeMaterial = parseFloat(summeMaterialText.replace(' €', '')) || 0;

        gesamtsummeElement.textContent = summeMaterial.toFixed(2) + ' €';
        log('Gesamtsumme gesetzt auf:', summeMaterial.toFixed(2));
    }

    // Service starten wenn DOM geladen ist
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOMContentLoaded - Lending Service wird initialisiert');
            try {
                initializeLendingService();
                initializeAuftragDetails();
                console.log('Lending Service erfolgreich initialisiert');
            } catch (error) {
                console.error('Fehler beim Initialisieren des Lending Service:', error);
            }
        });
    } else {
        console.log('DOM bereits geladen - Lending Service wird initialisiert');
        try {
            initializeLendingService();
            initializeAuftragDetails();
            console.log('Lending Service erfolgreich initialisiert');
        } catch (error) {
            console.error('Fehler beim Initialisieren des Lending Service:', error);
        }
    }

})();