const QuickScan = {
    currentStep: 1,
    scannedItem: null,
    scannedWorker: null,
    confirmationBarcode: null,
    lastKeyTime: 0,
    keyBuffer: '',
    isInitialized: false,
    activeInputType: null, // 'item' oder 'worker'
    
    // Neuer Zwischenspeicher für den aktuellen Prozess
    currentProcess: {
                item: null,
                worker: null,
        action: null,
        confirmed: false,
        quantity: 1  // Standardmenge auf 1 setzen
    },
            
    init() {
        this.setupEventListeners();
        this.updateButtonStates();
    },

    setupEventListeners() {
        const input = document.getElementById('quickScanActiveInput');
        if (input) {
            input.addEventListener('input', function(e) {
                checkManualInput();
            });
            
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    QuickScan.confirm();
                }
            });
            
            // Bestehende Event-Listener beibehalten
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.undoLastInput(this.activeInputType);
                }
            });
        }
        
        // Bestehende Event-Listener für Scanner
        document.addEventListener('keydown', (e) => {
            if (this.activeInputType && e.key.length === 1) {
                this.handleKeyInput(e, document.getElementById('quickScanActiveInput'));
            }
        });

        // Event-Listener für Item-Scan
        const itemInput = document.getElementById('itemScanInput');
        const confirmItemBtnElement = document.getElementById('confirmItemBtn');
        const undoItemBtnElement = document.getElementById('undoItemBtn');
        const workerInput = document.getElementById('workerScanInput');
        const confirmWorkerBtnElement = document.getElementById('confirmWorkerButton');
        const undoWorkerBtnElement = document.getElementById('undoWorkerButton');
        const modal = document.getElementById('quickScanModal');
        const activeInput = document.getElementById('quickScanActiveInput');

        // Prüfe ob wir uns auf einer QuickScan-Seite befinden
        if (!modal) {
            return;
        }

        // Event-Listener für Item-Scan
        if (itemInput) {
            itemInput.addEventListener('keydown', (e) => {
                this.handleKeyInput(e, itemInput);
            });

            if (confirmItemBtnElement) {
                confirmItemBtnElement.addEventListener('click', () => {
                    this.confirmItem();
                });
            }

            if (undoItemBtnElement) {
                undoItemBtnElement.addEventListener('click', () => {
                    this.undoLastInput('item');
                });
            }

            itemInput.addEventListener('input', (e) => {
                if (e.target.value && e.target.value.length > this.keyBuffer.length && e.target.value.includes(this.keyBuffer)) {
                    this.handleScannerInput(e.target.value, itemInput);
                    e.target.value = '';
                    this.keyBuffer = '';
                } else if (!e.target.value) {
                    this.keyBuffer = '';
                }
            });

            itemInput.addEventListener('blur', () => {
                if (this.currentStep === 1) {
                    // setTimeout(() => this.focusCurrentInput(), 100);
                }
            });
        }

        // Event-Listener für Worker-Scan
        if (workerInput) {
            workerInput.addEventListener('keydown', (e) => {
                this.handleKeyInput(e, workerInput);
            });

            if (confirmWorkerBtnElement) {
                confirmWorkerBtnElement.addEventListener('click', () => {
                    this.confirmWorker();
                });
            }

            if (undoWorkerBtnElement) {
                undoWorkerBtnElement.addEventListener('click', () => {
                    this.undoLastInput('worker');
                });
            }
            
            workerInput.addEventListener('input', (e) => {
                 if (e.target.value && e.target.value.length > this.keyBuffer.length && e.target.value.includes(this.keyBuffer)) {
                    this.handleScannerInput(e.target.value, workerInput);
                    e.target.value = '';
                    this.keyBuffer = '';
                } else if (!e.target.value) {
                    this.keyBuffer = '';
                }
            });

            workerInput.addEventListener('blur', () => {
                if (this.currentStep === 2) {
                    // setTimeout(() => this.focusCurrentInput(), 100);
                }
            });
        }

        // Event-Listener für Modal-Schließen
        if (modal) {
            modal.addEventListener('close', () => {
                this.reset();
            });
        }

        // Event-Listener für Mengeneingabe-Buttons
        document.querySelectorAll('.quantity-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const action = btn.dataset.action;
                if (action === 'decrease') {
                    this.decreaseQuantity();
                } else if (action === 'increase') {
                    this.increaseQuantity();
                }
            });
        });

        // Event-Listener für das neue sichtbare Eingabefeld
        if (activeInput) {
            activeInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const value = activeInput.value.trim();
                    const upperValue = value.toUpperCase();
                    if (upperValue === 'DANCE') {
                        QuickScan.showDancingEmojis();
                        showQuickScanToast('success', '🦓 Zebra-Party! 🦓');
                        activeInput.value = '';
                        return;
                    }
                    if (upperValue === 'VIBE') {
                        // VIBE Easter Egg - OPTIMIERT: Lazy Loading
                        const overlay = document.createElement('div');
                        overlay.className = 'zebra-overlay';
                        document.body.appendChild(overlay);
                        
                        const videoLeft = document.createElement('video');
                        videoLeft.className = 'dancing-zebra left';
                        videoLeft.loop = true;
                        videoLeft.autoplay = true;
                        videoLeft.preload = 'none'; // Wichtig: Nicht vorladen!
                        
                        const videoRight = document.createElement('video');
                        videoRight.className = 'dancing-zebra right';
                        videoRight.loop = true;
                        videoRight.autoplay = true;
                        videoRight.preload = 'none'; // Wichtig: Nicht vorladen!
                        
                        // Videos erst laden wenn sie benötigt werden
                        videoLeft.src = "/static/videos/vibe.mp4";
                        videoRight.src = "/static/videos/vibe.mp4";
                        
                        document.body.appendChild(videoLeft);
                        document.body.appendChild(videoRight);
                        
                        setTimeout(() => {
                            overlay.remove();
                            videoLeft.remove();
                            videoRight.remove();
                        }, 10000);
                        
                        activeInput.value = '';
                        return;
                    }
                    if (upperValue === 'AIIO') {
                        // AIIO Easter Egg (wie in handleScannerInput)
                        const overlay = document.createElement('div');
                        overlay.className = 'zebra-overlay';
                        document.body.appendChild(overlay);
                        const video = document.createElement('video');
                        video.src = "/static/videos/aiio.webm";
                        video.className = 'dancing-zebra';
                        video.loop = true;
                        video.autoplay = true;
                        video.style.position = 'fixed';
                        video.style.width = '640px';
                        video.style.height = '480px';
                        video.style.zIndex = 2147483647;
                        document.body.appendChild(video);
                        let x = Math.random() * (window.innerWidth - 640);
                        let y = Math.random() * (window.innerHeight - 480);
                        let dx = 5.0 * (Math.random() > 0.5 ? 1 : -1);
                        let dy = 5.0 * (Math.random() > 0.5 ? 1 : -1);
                        function animateDVDLogo() {
                            x += dx;
                            y += dy;
                            if (x <= 0 || x + 640 >= window.innerWidth) dx *= -1;
                            if (y <= 0 || y + 480 >= window.innerHeight) dy *= -1;
                            video.style.left = x + 'px';
                            video.style.top = y + 'px';
                            if (!video._stopAnimation) {
                                requestAnimationFrame(animateDVDLogo);
                            }
                        }
                        animateDVDLogo();
                        const modal = document.getElementById('quickScanModal');
                        let oldModalOverflow = null;
                        if (modal) {
                            modal.appendChild(video);
                            oldModalOverflow = modal.style.overflow;
                            modal.style.overflow = 'visible';
                        } else {
                            document.body.appendChild(video);
                        }
                        if (modal) {
                            modal.addEventListener('close', function removeAiioVideo() {
                                overlay.remove();
                                video._stopAnimation = true;
                                video.remove();
                                if (oldModalOverflow !== null) {
                                    modal.style.overflow = oldModalOverflow;
                                }
                                modal.removeEventListener('close', removeAiioVideo);
                            });
                        }
                        activeInput.value = '';
                        return;
                    }
                    // Normale Verarbeitung
                    if (value) {
                        if (this.activeInputType === 'item') {
                            this.handleItemScan(value);
                        } else if (this.activeInputType === 'worker') {
                            this.handleWorkerScan(value);
                        }
                        // Nach Scan/Eingabe Feld wieder ausblenden
                        document.getElementById('quickScanActiveInputContainer').classList.add('hidden');
                        this.activeInputType = null;
                    }
                }
            });
        }
    },

    handleKeyInput(e, input) {
        // Ignoriere input events, verarbeite nur keydown
        if (e.type !== 'keydown') return;
        
        const key = e.key;
        const currentTime = Date.now();
        const timeDiff = currentTime - this.lastKeyTime;
        const isWorkerInput = input.id === 'workerScanInput';
        
        // Ignoriere Steuerungstasten außer Backspace und Enter
        if (key.length > 1 && key !== 'Backspace' && key !== 'Enter') {
            return;
        }
        
        // Erhöhe die Zeitdifferenz auf 3000ms (3 Sekunden)
        if (timeDiff > 3000) { 
            this.keyBuffer = '';
        }
        
        if (key === 'Enter') {
            if (this.keyBuffer) {
                this.handleScannerInput(this.keyBuffer, input);
                this.keyBuffer = '';
            } else if (this.confirmationBarcode) {
                // Simuliere einen Scan des Bestätigungscodes bei Enter
                this.handleScannerInput(this.confirmationBarcode, input);
            } else if (input.value) {
                // Normale Enter-Verarbeitung für manuelle Eingaben
                const btnId = input.id === 'itemScanInput' ? 'confirmItemBtn' : 'confirmWorkerBtn';
                document.getElementById(btnId)?.click();
            }
            return;
        }
        
        if (key === 'Backspace') {
            e.preventDefault();
            this.keyBuffer = this.keyBuffer.slice(0, -1);
            this.updateDisplay(this.keyBuffer, isWorkerInput);
            return;
        }
        
        // Nur einzelne Zeichen zum Buffer hinzufügen
        if (key.length === 1) {
            this.keyBuffer += key;
            this.updateDisplay(this.keyBuffer, isWorkerInput);
            this.lastKeyTime = currentTime;
        }
    },

    updateDisplay(buffer, isWorker) {
        const inputId = isWorker ? 'processedWorkerInput' : 'processedItemInput';
        const btnId = isWorker ? 'confirmWorkerButton' : 'confirmItemBtn';
        const display = document.getElementById(inputId);
        const confirmBtn = document.getElementById(btnId);
        
        if (display) {
            if (buffer && buffer.length > 0) {
                display.textContent = buffer;
                display.classList.remove('opacity-50');
                if (confirmBtn) {
                    confirmBtn.classList.remove('hidden');
                }
            } else {
                display.textContent = 'Keine Eingabe';
                display.classList.add('opacity-50');
                if (confirmBtn) {
                    confirmBtn.classList.add('hidden');
                }
            }
        }
    },

    handleScannerInput(barcode, input) {
        // Easter Egg Checks - Case Insensitive
        const upperBarcode = barcode.toUpperCase();
        
        if (upperBarcode === 'DANCE') {
            this.showDancingEmojis();
            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        if (upperBarcode === 'VIBE') {
            if (window.location.pathname.startsWith('/mobile/quickscan')) { this.keyBuffer=''; this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput'); return; }
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);
            
            const videoLeft = document.createElement('video');
            videoLeft.src = "/static/videos/vibe.mp4";
            videoLeft.className = 'dancing-zebra left';
            videoLeft.loop = true;
            videoLeft.autoplay = true;
            
            const videoRight = document.createElement('video');
            videoRight.src = "/static/videos/vibe.mp4";
            videoRight.className = 'dancing-zebra right';
            videoRight.loop = true;
            videoRight.autoplay = true;
            
            document.body.appendChild(videoLeft);
            document.body.appendChild(videoRight);
            
            setTimeout(() => {
                overlay.remove();
                videoLeft.remove();
                videoRight.remove();
            }, 10000);
            
            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        if (upperBarcode === 'AIIO') {
            if (window.location.pathname.startsWith('/mobile/quickscan')) { this.keyBuffer=''; this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput'); return; }
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);

            // Video-Element erzeugen
            const video = document.createElement('video');
            video.src = "/static/videos/aiio.webm";
            video.className = 'dancing-zebra';
            video.loop = true;
            video.autoplay = true;
            video.style.position = 'fixed';
            video.style.width = '640px';
            video.style.height = '480px';
            video.style.zIndex = 2147483647;
            document.body.appendChild(video);

            // Startposition und Geschwindigkeit
            let x = Math.random() * (window.innerWidth - 640);
            let y = Math.random() * (window.innerHeight - 480);
            let dx = 5.0 * (Math.random() > 0.5 ? 1 : -1);
            let dy = 5.0 * (Math.random() > 0.5 ? 1 : -1);

            function animateDVDLogo() {
                x += dx;
                y += dy;
                // Kollision mit Rändern
                if (x <= 0 || x + 640 >= window.innerWidth) dx *= -1;
                if (y <= 0 || y + 480 >= window.innerHeight) dy *= -1;
                video.style.left = x + 'px';
                video.style.top = y + 'px';
                if (!video._stopAnimation) {
                    requestAnimationFrame(animateDVDLogo);
                }
            }
            animateDVDLogo();

            // Modal in den Hintergrund schicken
            const modal = document.getElementById('quickScanModal');
            let oldModalOverflow = null;
            if (modal) {
                // Video INS Modal einfügen
                modal.appendChild(video);
                // Modal-Overflow sichtbar machen, damit das Video nicht beschnitten wird
                oldModalOverflow = modal.style.overflow;
                modal.style.overflow = 'visible';
            } else {
                document.body.appendChild(video);
            }

            // Entferne das Video, wenn das Modal geschlossen wird
            if (modal) {
                modal.addEventListener('close', function removeAiioVideo() {
                    overlay.remove();
                    video._stopAnimation = true;
                    video.remove();
                    if (oldModalOverflow !== null) {
                        modal.style.overflow = oldModalOverflow;
                    }
                    modal.removeEventListener('close', removeAiioVideo);
                });
            }

            this.keyBuffer = '';
            this.updateDisplay(this.keyBuffer, input.id === 'workerScanInput');
            return;
        }

        // Normale Barcode-Verarbeitung
        if (this.confirmationBarcode && barcode.includes(this.confirmationBarcode)) {
            // Bestätigungscode-Logik
            if (this.currentStep === 1) {
                this.currentStep = 2;
                this.goToStep(2);
            } else if (this.currentStep === 2) {
                this.executeStoredProcess();
            }
        } else {
            if (this.currentStep === 1) {
                this.handleItemScan(barcode);
            } else if (this.currentStep === 2) {
                this.handleWorkerScan(barcode);
            }
        }
    },

    setCardState(type, state) {
        // type: 'item' oder 'worker', state: 'selected', 'success', 'default'
        const card = document.getElementById(type === 'item' ? 'itemCard' : 'workerCard');
        card.classList.remove('selected', 'success', 'default');
        if (state === 'selected') {
            card.classList.add('selected');
        } else if (state === 'success') {
            card.classList.add('success');
        }
        // Für 'default' keine Klasse hinzufügen
    },

    async handleItemScan(barcode) {
        try {
            // Zuerst versuchen, ein Werkzeug zu finden
            let response = await fetch(`/api/inventory/tools/${barcode}`);
            let data = await response.json();
            
            let item = null;
            let itemType = 'tool';
            
            if (data.success) {
                item = data.tool;
            } else {
                // Wenn kein Werkzeug gefunden, versuche Verbrauchsmaterial
                response = await fetch(`/api/inventory/consumables/${barcode}`);
                data = await response.json();
                
                if (data.success) {
                    item = data.consumable;
                    itemType = 'consumable';
                } else {
                    this.showError("Artikel nicht gefunden", 'item');
                    this.setCardState('item', 'selected');
                    updateQuickScanButton(); // Button-Status aktualisieren
                    return;
                }
            }
            
            this.scannedItem = item;
            
            // Bestandswert robust ermitteln
            let quantity = (typeof item.quantity === 'number') ? item.quantity :
                           (typeof item.current_stock === 'number') ? item.current_stock :
                           (typeof item.current_amount === 'number') ? item.current_amount : 0;
            let min_quantity = (typeof item.min_quantity === 'number') ? item.min_quantity : 0;
            
            // Status-Text generieren
            let statusText = '';
            if (itemType === 'consumable') {
                statusText = quantity > 0 ? 'Verfügbar' : 'Fehlt';
            } else {
                statusText = item.status || 'Unbekannt';
            }
            
            // Anzeige auf Karte aktualisieren
            const itemCardContent = document.getElementById('itemCardContent');
            if (itemCardContent) {
                let html = `<div class='font-bold mb-1'>${item.name || 'Unbek. Artikel'}</div>`;
                html += `<div class='badge badge-lg ${itemType === 'consumable' ? 'badge-info' : 'badge-neutral'} mb-1'>${itemType === 'consumable' ? 'Verbrauchsmaterial' : 'Werkzeug'}</div>`;
                html += `<div class='badge badge-lg mb-1'>${statusText}</div>`;
                if (itemType === 'consumable') {
                    html += `<div class='text-sm mt-1'>Bestand: <span class='font-mono'>${quantity}</span> / <span class='font-mono'>${min_quantity}</span> (min)</div>`;
                }
                html += `<div class='text-xs text-gray-400 mt-2'>(erneut klicken zum Ändern)</div>`;
                itemCardContent.innerHTML = html;
            }
            this.setCardState('item', 'success');
            this.setCardState('worker', this.activeInputType === 'worker' ? 'selected' : (this.scannedWorker ? 'success' : 'default'));
            
            // Button-Status sofort aktualisieren
            setTimeout(() => updateQuickScanButton(), 100);
            
            // Mengen-Modal für Verbrauchsgüter anzeigen
            if (itemType === 'consumable') {
                this.showQuantityModal();
            }
        } catch (error) {
            console.error("Fehler beim Abrufen des Artikels:", error);
            this.showError("Fehler beim Abrufen des Artikels", 'item');
            updateQuickScanButton(); // Button-Status aktualisieren
        }
    },

    async handleWorkerScan(barcode) {
        try {
            const response = await fetch(`/api/inventory/workers/${barcode}`);
            const result = await response.json();
            if (!result.success) {
                this.showError(result.message || 'Mitarbeiter nicht gefunden', 'worker');
                this.setCardState('worker', 'selected');
                updateQuickScanButton(); // Button-Status aktualisieren
                return;
            }
            const worker = result.worker;
            this.scannedWorker = worker;
            
            // Anzeige auf Karte aktualisieren
            const workerCardContent = document.getElementById('workerCardContent');
            if (workerCardContent) {
                let html = `<div class='font-bold mb-1'>${worker.firstname || ''} ${worker.lastname || ''}</div>`;
                html += `<div class='text-sm mb-1'>${worker.department || 'Keine Abteilung'}</div>`;
                html += `<div class='text-xs text-gray-400 mt-2'>(erneut klicken zum Ändern)</div>`;
                workerCardContent.innerHTML = html;
            }
            this.setCardState('worker', 'success');
            this.setCardState('item', this.activeInputType === 'item' ? 'selected' : (this.scannedItem ? 'success' : 'default'));
            
            // Button-Status sofort aktualisieren
            setTimeout(() => updateQuickScanButton(), 100);
        } catch (error) {
            console.error("Fehler beim Abrufen des Mitarbeiters:", error);
            this.showError("Fehler beim Abrufen des Mitarbeiters", 'worker');
            updateQuickScanButton(); // Button-Status aktualisieren
        }
    },

    async executeStoredProcess() {

        if (!this.currentProcess || !this.scannedItem || !this.scannedWorker) {
            console.error("Prozess nicht vollständig:", {
                process: this.currentProcess,
                item: this.scannedItem,
                worker: this.scannedWorker
            });
            this.showError("Prozess nicht vollständig");
            return;
        }

        try {
            const response = await fetch('/api/quickscan/process_lending', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    item_barcode: this.scannedItem.barcode,
                    worker_barcode: this.scannedWorker.barcode,
                    action: this.scannedItem.type === 'consumable' ? 'consume' : 'lend',
                    item_type: this.scannedItem.type,
                    quantity: this.scannedItem.type === 'consumable' ? (this.currentProcess.quantity || 1) : 1
                })
            });

            const data = await response.json();

            if (data.success) {
                showQuickScanToast('success', data.message || 'Vorgang erfolgreich!');
                
                // Schließe das Modal
                const modal = document.getElementById('quickScanModal');
                if (modal) {
                    modal.close();
                }
                
                // Aktualisiere die Verbrauchshistorie, wenn es sich um ein Verbrauchsmaterial handelt
                if (this.scannedItem.type === 'consumable') {
                    // Lade die Seite neu, um die aktualisierte Historie anzuzeigen
                    window.location.reload();
                }
                
                this.reset();
            } else {
                this.showError(data.message || 'Fehler bei der Verarbeitung');
            }
        } catch (error) {
            console.error("Fehler bei der Verarbeitung:", error);
            this.showError("Fehler bei der Verarbeitung");
        }
    },

    reset() {
        this.scannedItem = null;
        this.scannedWorker = null;
        this.activeInputType = null;
        this.currentProcess = {};
        
        // Karten zurücksetzen
        const itemCardContent = document.getElementById('itemCardContent');
        const workerCardContent = document.getElementById('workerCardContent');
        if (itemCardContent) {
            itemCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
        }
        if (workerCardContent) {
            workerCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
        }
        
        // Kartenfarben zurücksetzen
        this.setCardState('item', 'default');
        this.setCardState('worker', 'default');
        
        // Eingabefeld verstecken
        const inputContainer = document.getElementById('quickScanActiveInputContainer');
        if (inputContainer) {
            inputContainer.classList.add('hidden');
        }
        
        // Button-Status zurücksetzen
        setTimeout(() => {
            updateQuickScanButton();
        }, 100);
    },

    goToStep(step) {
        document.querySelectorAll('.scan-step').forEach(el => el.classList.add('hidden'));
        document.getElementById(`step${step}`).classList.remove('hidden');
        document.querySelectorAll('.steps .step').forEach((el, index) => {
            if (index + 1 <= step) {
                el.classList.add('step-primary');
            } else {
                el.classList.remove('step-primary');
            }
        });
        this.currentStep = step;
        this.focusCurrentInput(); // Fokus wieder aktivieren
    },
    
    focusCurrentInput() {
        const currentInput = this.currentStep === 1 ? 'itemScanInput' : 'workerScanInput';
        const input = document.getElementById(currentInput);
        if (input) {
            input.focus();
            input.select(); // Selektiert den vorhandenen Text
        }
    },

    confirmItem() {
        const input = document.getElementById('itemScanInput');
        if (this.keyBuffer) {
            this.handleScannerInput(this.keyBuffer, input);
            this.keyBuffer = '';
        }
    },

    confirmWorker() {
        const input = document.getElementById('workerScanInput');
        if (this.keyBuffer) {
            this.handleScannerInput(this.keyBuffer, input);
            this.keyBuffer = '';
        }
    },

    // Neue Funktionen für Mengenänderung
    decreaseQuantity() {
        const quantityDisplay = document.getElementById('quantityDisplay');
        const currentValue = parseInt(quantityDisplay.textContent);
        if (currentValue > 1) {
            quantityDisplay.textContent = currentValue - 1;
            this.currentProcess.quantity = currentValue - 1;
            // Fokus zurücksetzen
            this.focusCurrentInput();
        }
    },

    increaseQuantity() {
        const quantityDisplay = document.getElementById('quantityDisplay');
        const currentValue = parseInt(quantityDisplay.textContent);
        const maxQuantity = parseInt(quantityDisplay.dataset.max);
        if (currentValue < maxQuantity) {
            quantityDisplay.textContent = currentValue + 1;
            this.currentProcess.quantity = currentValue + 1;
            // Fokus zurücksetzen
            this.focusCurrentInput();
        }
    },

    // Funktion zum Rückgängig machen der letzten Eingabe
    undoLastInput(type) {
        this.keyBuffer = this.keyBuffer.slice(0, -1);
        this.updateDisplay(this.keyBuffer, type === 'worker');
    },

    processScannerInput: function(input, type) {
        if (!input) return;
        
        // Spezielle Barcodes für visuelle Effekte
        if (input === 'SCANDY') {
            this.showConfetti();
            return;
        }
        if (input === 'DANCE') {
            this.showDancingEmojis();
            return;
        }
        if (input === 'AIIO') {
            const overlay = document.createElement('div');
            overlay.className = 'zebra-overlay';
            document.body.appendChild(overlay);
            
            const videoLeft = document.createElement('video');
            videoLeft.src = "/static/videos/aiio.webm";
            videoLeft.className = 'dancing-zebra left';
            videoLeft.loop = true;
            videoLeft.autoplay = true;
            
            const videoRight = document.createElement('video');
            videoRight.src = "/static/videos/aiio.webm";
            videoRight.className = 'dancing-zebra right';
            videoRight.loop = true;
            videoRight.autoplay = true;
            
            document.body.appendChild(videoLeft);
            document.body.appendChild(videoRight);
            
            setTimeout(() => {
                overlay.remove();
                videoLeft.remove();
                videoRight.remove();
            }, 10000);
            return;
        }
        
        // Normale Verarbeitung
        if (type === 'item') {
            this.scannedItem = input;
            this.updateDisplay();
            this.currentStep = 'worker';
            document.getElementById('workerInput').focus();
        } else if (type === 'worker') {
            this.scannedWorker = input;
            this.updateDisplay();
            this.executeStoredProcess();
        }
    },

    showConfetti() {
        confetti({
            particleCount: 200,
            spread: 160,
            origin: { y: 0.6 },
            ticks: 200,
            gravity: 0.8,
            scalar: 1.2,
            zIndex: 99999
        });
        setTimeout(() => {
            confetti({
                particleCount: 100,
                angle: 60,
                spread: 100,
                origin: { x: 0 },
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                zIndex: 99999
            });
            confetti({
                particleCount: 100,
                angle: 120,
                spread: 100,
                origin: { x: 1 },
                ticks: 200,
                gravity: 0.8,
                scalar: 1.2,
                zIndex: 99999
            });
        }, 250);
        showQuickScanToast('success', '🎉 SCANDY! 🎉');
    },

    showDancingEmojis() {
        if (window.location.pathname.startsWith('/mobile/quickscan')) {
            // Easter-Eggs auf Mobilseite deaktivieren
            return;
        }
        // Vorhandene Zebras entfernen, falls welche da sind
        document.querySelectorAll('.dancing-zebra').forEach(el => el.remove());
        
        const overlay = document.createElement('div');
        overlay.className = 'zebra-overlay';
        document.body.appendChild(overlay);
        
        const zebraLeft = document.createElement('img');
        zebraLeft.src = '/static/images/dancing_zebra.gif'; // Pfad zum animierten GIF
        zebraLeft.className = 'dancing-zebra left';
        
        const zebraRight = document.createElement('img');
        zebraRight.src = '/static/images/dancing_zebra.gif';
        zebraRight.className = 'dancing-zebra right';
        
        document.body.appendChild(zebraLeft);
        document.body.appendChild(zebraRight);
        
        // Optional: Musik abspielen
        const audio = new Audio('/static/audio/zebra_party.mp3'); // Pfad zur Musikdatei
        audio.play().catch(error => console.warn("Autoplay wurde verhindert:", error));
        
        // Nach einiger Zeit wieder entfernen
        setTimeout(() => {
            zebraLeft.remove();
            zebraRight.remove();
            overlay.remove();
            audio.pause();
            audio.currentTime = 0;
        }, 10000); // 10 Sekunden
    },

    showError(message, type = null) {
        console.error("Fehler:", message);
        showQuickScanToast('error', message);
        if (type === 'item') {
            // Nur Item-Eingabe zurücksetzen
            this.scannedItem = null;
            const itemCardContent = document.getElementById('itemCardContent');
            if (itemCardContent) {
                itemCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
            }
            this.setCardState('item', 'selected');
            updateQuickScanButton();
        } else if (type === 'worker') {
            // Nur Worker-Eingabe zurücksetzen
            this.scannedWorker = null;
            const workerCardContent = document.getElementById('workerCardContent');
            if (workerCardContent) {
                workerCardContent.innerHTML = `<p class='text-sm opacity-50'>Klicken &amp; Barcode scannen oder eingeben</p>`;
            }
            this.setCardState('worker', 'selected');
            updateQuickScanButton();
        } else {
            // Fallback: alles zurücksetzen
            this.reset();
        }
    },

    showQuantityModal() {
        const modal = document.getElementById('quantityModal');
        if (modal) {
            modal.showModal();
        }
    },

    closeQuantityModal() {
        const modal = document.getElementById('quantityModal');
        if (modal) {
            modal.close();
        }
    },

    confirmQuantity() {
        const quantityInput = document.getElementById('quantityInput');
        if (!quantityInput) return;
        
        const quantity = parseInt(quantityInput.value);
        if (quantity > 0) {
            this.currentProcess.quantity = quantity;
            this.closeQuantityModal();
            // Nach Mengenbestätigung: Karte bleibt grün, kein weiterer Scan nötig
            this.setCardState('item', 'success');
            updateQuickScanButton();
        } else {
            showQuickScanToast('error', 'Bitte eine gültige Menge eingeben.');
        }
    },

    openModal() {
        const modal = document.getElementById('quickScanModal');
        if (modal) {
            modal.showModal();
            this.init();
        } else {
            console.error("Cannot open QuickScan modal - modal not found!");
        }
    },

    activateInput(type) {
        // Zeige das sichtbare Eingabefeld an und setze Typ
        this.activeInputType = type;
        const inputContainer = document.getElementById('quickScanActiveInputContainer');
        const input = document.getElementById('quickScanActiveInput');
        if (inputContainer && input) {
            input.value = '';
            inputContainer.classList.remove('hidden');
            input.focus();
            input.placeholder = type === 'item' ? 'Werkzeug/Verbrauchsgut scannen oder eingeben' : 'Mitarbeiter scannen oder eingeben';
        }
        // Kartenfarben setzen
        this.setCardState('item', type === 'item' ? 'selected' : (this.scannedItem ? 'success' : 'default'));
        this.setCardState('worker', type === 'worker' ? 'selected' : (this.scannedWorker ? 'success' : 'default'));
        
        // Button-Status nach Kartenwechsel aktualisieren
        setTimeout(() => {
            checkManualInput(); // Prüfe auch manuelle Eingaben
        }, 50);
    },

    // Button-Status aktualisieren
    updateConfirmButtonState() {
        // Diese Funktion wurde durch die globale updateQuickScanButton() Funktion ersetzt
        updateQuickScanButton();
    },

    // Bestätigen-Button
    async confirm() {
        
        // Prüfe zuerst, ob manuelle Eingabe vorhanden ist
        const input = document.getElementById('quickScanActiveInput');
        if (input && input.value.trim()) {
            await this.handleManualInput(input.value);
            return;
        }
        
        // Normale Logik für gescannte Items
        if (this.scannedItem && this.scannedWorker) {
            // Bestimme Aktion für Werkzeuge: 'lend' oder 'return'
            let action = 'lend';
            if (this.scannedItem.type !== 'consumable') {
                if (this.scannedItem.status === 'ausgeliehen') {
                    action = 'return';
                }
            } else {
                action = 'consume';
            }

            // Prüfe ob es sich um eine neue Werkzeug-Ausleihe handelt
            if (this.scannedItem.type !== 'consumable' && action === 'lend') {
                // Öffne Return Date Modal für neue Werkzeug-Ausleihen
                this.openReturnDateModal();
                return;
            }

            // Für alle anderen Fälle: direkt ausführen
            await this.executeAction(action);
        } else {
            showQuickScanToast('error', 'Bitte geben Sie einen Barcode ein oder scannen Sie Items');
        }
    },

    // Neue Funktion für manuelle Eingaben
    async handleManualInput(inputValue) {
        if (!inputValue || !this.activeInputType) {
            return;
        }
        
        try {
            if (this.activeInputType === 'item') {
                await this.handleItemScan(inputValue);
            } else if (this.activeInputType === 'worker') {
                await this.handleWorkerScan(inputValue);
            }
            
            // Eingabefeld leeren
            const input = document.getElementById('quickScanActiveInput');
            if (input) {
                input.value = '';
                checkManualInput(); // Button-Status aktualisieren
            }
        } catch (error) {
            console.error("Fehler bei manueller Eingabe:", error);
            showQuickScanToast('error', 'Fehler bei der Verarbeitung der Eingabe');
        }
    },

    updateButtonStates() {
        // Button-Status aktualisieren
        const buttons = document.querySelectorAll('[data-action]');
        buttons.forEach(button => {
            button.disabled = false;
        });
    },

    // Return Date Modal Funktionen
    openReturnDateModal() {
        // Standard-Datum auf 2 Wochen in der Zukunft setzen
        const today = new Date();
        const twoWeeksFromNow = new Date(today.getTime() + (14 * 24 * 60 * 60 * 1000));
        const formattedDate = twoWeeksFromNow.toISOString().split('T')[0];
        
        document.getElementById('returnDateInput').value = formattedDate;
        document.getElementById('returnDateModal').showModal();
    },

    closeReturnDateModal() {
        document.getElementById('returnDateModal').close();
    },

    async confirmReturnDate() {
        const returnDate = document.getElementById('returnDateInput').value;
        if (!returnDate) {
            showQuickScanToast('error', 'Bitte wählen Sie ein Rückgabedatum aus');
            return;
        }
        
        // Speichere das Rückgabedatum im currentProcess
        this.currentProcess.returnDate = returnDate;
        
        // Schließe das Modal
        this.closeReturnDateModal();
        
        // Führe die eigentliche Aktion aus
        await this.executeAction('lend');
    },

    // Neue Funktion für die eigentliche Aktionsausführung
    async executeAction(action) {
        if (!this.scannedItem || !this.scannedWorker) {
            showQuickScanToast('error', 'Bitte scannen Sie zuerst Werkzeug und Mitarbeiter');
            return;
        }

        try {
            // Daten für die API zusammenstellen
            const requestData = {
                item_barcode: this.scannedItem.barcode,
                worker_barcode: this.scannedWorker.barcode,
                action: action
            };

            // Return Date hinzufügen falls vorhanden
            if (this.currentProcess.returnDate) {
                requestData.expected_return_date = this.currentProcess.returnDate;
            }

            // Menge für Verbrauchsgüter hinzufügen
            if (this.scannedItem.type === 'consumable') {
                requestData.quantity = this.currentProcess.quantity || 1;
            }

            // API-Aufruf an den neuen Quick Scan Endpoint
            const response = await fetch('/quick_scan/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            
            if (data.error) {
                showQuickScanToast('error', data.error);
            } else {
                showQuickScanToast('success', data.message);
                this.reset();
                document.getElementById('quickScanModal').close();
            }
        } catch (error) {
            console.error('Error:', error);
            showQuickScanToast('error', 'Ein Fehler ist aufgetreten');
        }
    }
};

// QuickScan initialisieren wenn Modal geöffnet wird
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('quickScanModal');
    const trigger = document.getElementById('quickScanTrigger'); 

    if (modal) {
        // Listener für das 'close'-Event des Modals
        modal.addEventListener('close', () => {
            QuickScan.reset();
        });
    }

    // Event Listener für den Trigger Button hinzufügen
    if (trigger) {
        trigger.addEventListener('click', () => {
            // Prüfe ob der Benutzer authentifiziert ist
            const userRole = trigger.getAttribute('data-role');
            const isAuthenticated = userRole && userRole !== 'None' && userRole !== 'anonymous';
            const isTeilnehmer = userRole === 'teilnehmer';
            
            if (!isAuthenticated) {
                // Zeige Meldung für nicht eingeloggte Benutzer
                showQuickScanToast('warning', 'QuickScan ist nur für eingeloggte Benutzer verfügbar');
                return;
            }
            
            if (isTeilnehmer) {
                // Zeige Meldung für Teilnehmer
                showQuickScanToast('warning', 'QuickScan ist für Teilnehmer nicht verfügbar');
                return;
            }
            
            if (modal) {
                modal.showModal(); 
                QuickScan.init(); 
            } else {
                console.error("Cannot open QuickScan modal - modal not found!");
            }
        });
    }
});

// Aktualisiere den Buffer im UI
function updateBufferDisplay(buffer, isWorker = false) {
    if (typeof updateScanBuffer === 'function') {
        updateScanBuffer(buffer, isWorker);
    }
}

// Robuste Toast-Funktion für QuickScan
function showQuickScanToast(type, message) {
    // Warte auf window.showToast oder verwende Fallback
    const showToast = () => {
        if (typeof window.showToast === 'function') {
            try {
                window.showToast(type, message);
                return;
            } catch (e) {
                console.warn('window.showToast failed, using fallback:', e);
            }
        }
        
        // Fallback: Eigene Toast-Implementierung
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'fixed bottom-4 right-4 z-[9999] flex flex-col gap-2';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} rounded-lg shadow-lg p-4 pr-12 relative min-w-[300px] max-w-[400px]`;
        
        // Farben basierend auf Typ
        const colors = {
            success: { bg: '#10b981', color: '#ffffff', icon: '✓' },
            error: { bg: '#ef4444', color: '#ffffff', icon: '✕' },
            info: { bg: '#3b82f6', color: '#ffffff', icon: 'ℹ' },
            warning: { bg: '#f59e0b', color: '#ffffff', icon: '⚠' }
        };
        
        const color = colors[type] || colors.info;
        toast.style.backgroundColor = color.bg;
        toast.style.color = color.color;
        
        toast.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0 mr-3">
                    <span class="text-lg font-bold">${color.icon}</span>
                </div>
                <div class="flex-1">
                    <span class="text-sm font-medium">${message}</span>
                </div>
                <button class="close-btn absolute top-2 right-2 text-white hover:text-gray-200 transition-colors duration-200" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Nach 6 Sekunden ausblenden
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 6000);
    };
    
    // Versuche sofort, falls window.showToast bereits verfügbar ist
    if (typeof window.showToast === 'function') {
        showToast();
    } else {
        // Warte auf DOMContentLoaded oder timeout
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', showToast);
        } else {
            // Fallback: Warte kurz und versuche dann
            setTimeout(showToast, 100);
        }
    }
}

// Globale Funktion für Button-Status-Update
function updateQuickScanButton() {
    const btn = document.getElementById('quickScanConfirmBtn');
    if (!btn) {
        console.error("Button nicht gefunden!");
        return;
    }
    
    const hasItem = !!(QuickScan.scannedItem && QuickScan.scannedItem.barcode);
    const hasWorker = !!(QuickScan.scannedWorker && QuickScan.scannedWorker.barcode);
    const shouldEnable = hasItem && hasWorker;
    

    
    btn.disabled = !shouldEnable;
    
    if (shouldEnable) {
        btn.classList.remove('btn-disabled');
        btn.classList.add('btn-primary');
    } else {
        btn.classList.add('btn-disabled');
        btn.classList.remove('btn-primary');
    }
}

// Neue Funktion für manuelle Eingabe-Validierung
function checkManualInput() {
    const input = document.getElementById('quickScanActiveInput');
    if (!input) return;
    
    const inputValue = input.value.trim();
    const hasInput = inputValue.length > 0;
    

    
    // Wenn Eingabe vorhanden ist, Button aktivieren
    if (hasInput) {
        const btn = document.getElementById('quickScanConfirmBtn');
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('btn-disabled');
            btn.classList.add('btn-primary');

        }
    } else {
        // Wenn keine Eingabe, normale Logik verwenden
        updateQuickScanButton();
    }
}