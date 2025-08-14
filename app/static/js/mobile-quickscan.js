// Mobile Quickscan mit Kamera-Vorschau und BarcodeDetector
(function() {
  let mediaStream = null;
  let useEnvironment = true;
  let torchOn = false;
  let selectedItem = null; // { barcode, type, name, status, quantity }
  let selectedWorker = null; // { barcode, firstname, lastname }
  let currentStep = null; // 'item' | 'worker'
  let detectionActive = false;

  const els = {};

  function $(id) { return document.getElementById(id); }

  function setButtonState() {}

  function setStep(step) {
    currentStep = step; // 'item' | 'worker'
    // UI-Karten hervorheben
    const itemBtn = $('scanItemBtn');
    const workerBtn = $('scanWorkerBtn');
    itemBtn.classList.remove('border-primary');
    workerBtn.classList.remove('border-primary');
    if (step === 'item') itemBtn.classList.add('border-primary');
    if (step === 'worker') workerBtn.classList.add('border-primary');
    const hint = $('scanHint');
    if (hint) hint.textContent = step === 'item' ? 'Scanne Artikel-Barcode…' : 'Scanne Mitarbeiter-Barcode…';
  }

  async function startCamera() {
    try {
      stopCamera();
      const constraints = {
        video: {
          facingMode: useEnvironment ? 'environment' : 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      els.video.srcObject = mediaStream;
      els.video.play().catch(() => {});
      // Versuche Torch (Blitz) zu setzen falls verfügbar
      await applyTorch(torchOn);
      startDetectLoop();
    } catch (e) {
      console.warn('Kamera konnte nicht gestartet werden:', e);
    }
  }

  function stopCamera() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
    detectionActive = false;
  }

  async function applyTorch(on) {
    try {
      if (!mediaStream) return;
      const track = mediaStream.getVideoTracks()[0];
      const capabilities = track.getCapabilities?.();
      if (capabilities && capabilities.torch) {
        await track.applyConstraints({ advanced: [{ torch: !!on }] });
        torchOn = !!on;
        return true;
      }
    } catch (e) {
      console.debug('Torch nicht verfügbar:', e);
    }
    return false;
  }

  async function detectOnce() {
    try {
      if ('BarcodeDetector' in window) {
        const detector = new BarcodeDetector({ formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'codabar'] });
        const barcodes = await detector.detect(els.video);
        if (barcodes?.length) {
          handleBarcode(barcodes[0].rawValue.trim());
          return;
        }
      } else if (window.ZXingBrowser && els.video) {
        // ZXing Fallback: einmaliges Grab und Dekodieren des aktuellen Frames
        const codeReader = window.ZXingBrowser.BrowserMultiFormatReader ? new window.ZXingBrowser.BrowserMultiFormatReader() : null;
        if (codeReader) {
          try {
            const result = await codeReader.decodeFromVideoElement(els.video);
            if (result && result.text) {
              handleBarcode(String(result.text).trim());
              codeReader.reset();
              return;
            }
            codeReader.reset();
          } catch (err) {
            // still loop
          }
        }
      }
    } catch (e) {
      // weiter versuchen
    }
  }

  function startDetectLoop() {
    detectionActive = true;
    const loop = async () => {
      if (!detectionActive) return;
      await detectOnce();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  async function handleBarcode(code) {
    if (!code || !currentStep) return;
    if (currentStep === 'item') {
      await lookupItem(code);
      if (selectedItem) setStep('worker');
    } else if (currentStep === 'worker') {
      await lookupWorker(code);
      if (selectedItem && selectedWorker) {
        await confirmAction();
      }
    }
  }

  async function lookupItem(barcode) {
    try {
      // Erst Tool, sonst Consumable
      let res = await fetch(`/api/inventory/tools/${encodeURIComponent(barcode)}`);
      let data = await res.json();
      if (!data.success) {
        res = await fetch(`/api/inventory/consumables/${encodeURIComponent(barcode)}`);
        data = await res.json();
      }
      if (data.success) {
        const item = data.tool || data.consumable;
        selectedItem = {
          barcode: item.barcode,
          type: data.tool ? 'tool' : 'consumable',
          name: item.name || 'Artikel',
          status: item.status,
          quantity: typeof item.quantity === 'number' ? item.quantity : (item.current_stock || item.current_amount || 0)
        };
        const itemSum = $('itemSummary');
        if (itemSum) itemSum.textContent = `${selectedItem.name}`;
        const itemBtn = $('scanItemBtn');
        if (itemBtn) itemBtn.classList.add('btn-primary');
        // Felder erst beim bestätigungsbereiten Zustand anzeigen (in setButtonState)
      } else {
        toast('error', 'Artikel nicht gefunden');
      }
    } catch (e) {
      toast('error', 'Fehler bei Artikelsuche');
    }
  }

  async function lookupWorker(barcode) {
    try {
      const res = await fetch(`/api/inventory/workers/${encodeURIComponent(barcode)}`);
      const data = await res.json();
      if (data.success) {
        const w = data.worker;
        selectedWorker = { barcode: w.barcode, firstname: w.firstname || '', lastname: w.lastname || '' };
        const workerSum = $('workerSummary');
        if (workerSum) workerSum.textContent = `${selectedWorker.firstname} ${selectedWorker.lastname}`.trim();
        const workerBtn = $('scanWorkerBtn');
        if (workerBtn) workerBtn.classList.add('btn-primary');
      } else {
        toast('error', 'Mitarbeiter nicht gefunden');
      }
    } catch (e) {
      toast('error', 'Fehler bei Mitarbeitersuche');
    }
  }

  async function confirmAction() {
    if (!selectedItem || !selectedWorker) return;
    const payload = {
      item_barcode: selectedItem.barcode,
      worker_barcode: selectedWorker.barcode,
      action: selectedItem.type === 'consumable' ? 'use' : (selectedItem.status === 'ausgeliehen' ? 'return' : 'lend')
    };
    try {
      const res = await fetch('/quick_scan/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && !data.error) {
        toast('success', data.message || 'Vorgang erfolgreich');
        resetState(true);
      } else {
        toast('error', data.error || 'Fehler bei der Verarbeitung');
      }
    } catch (e) {
      toast('error', 'Netzwerkfehler');
    }
  }

  function resetState(keepCamera = false) {
    selectedItem = null;
    selectedWorker = null;
    $('itemSummary').textContent = 'Tippen zum Scannen';
    $('workerSummary').textContent = 'Tippen zum Scannen';
    const itemBtn2 = $('scanItemBtn');
    const workerBtn2 = $('scanWorkerBtn');
    if (itemBtn2) itemBtn2.classList.remove('btn-primary');
    if (workerBtn2) workerBtn2.classList.remove('btn-primary');
    const qtyRow = $('quantityRow');
    if (qtyRow) qtyRow.classList.add('hidden');
    const retRow = $('returnDateRow');
    if (retRow) retRow.classList.add('hidden');
    const qtyInput = $('qtyInput');
    if (qtyInput) qtyInput.value = '1';
    setStep('item');
    setButtonState();
    if (!keepCamera) stopCamera();
  }

  function toast(type, message) {
    if (typeof window.showToast === 'function') {
      window.showToast(type, message);
    } else {
      console.log(type.toUpperCase() + ': ' + message);
    }
  }

  function bindEvents() {
    const itemBtn = $('scanItemBtn');
    if (itemBtn) itemBtn.addEventListener('click', async () => {
      setStep('item');
      await startCamera(); // iOS: getUserMedia im User-Gesture-Kontext
    });
    const workerBtn = $('scanWorkerBtn');
    if (workerBtn) workerBtn.addEventListener('click', async () => {
      setStep('worker');
      await startCamera(); // iOS: getUserMedia im User-Gesture-Kontext
    });
    const switchBtn = $('switchCameraBtn');
    if (switchBtn) switchBtn.addEventListener('click', async () => {
      useEnvironment = !useEnvironment;
      await startCamera();
    });
    const torchBtn = $('toggleTorchBtn');
    if (torchBtn) torchBtn.addEventListener('click', async () => {
      const ok = await applyTorch(!torchOn);
      if (!ok) toast('info', 'Blitz nicht verfügbar');
    });
    const dec = $('qtyDec');
    if (dec) {
      dec.addEventListener('click', (e) => {
        e.preventDefault();
        const el = $('qtyInput');
        if (!el) return;
        const v = Math.max(1, (parseInt(el.value || '1', 10) || 1) - 1);
        el.value = String(v);
      });
    }
    const inc = $('qtyInc');
    if (inc) {
      inc.addEventListener('click', (e) => {
        e.preventDefault();
        const el = $('qtyInput');
        if (!el) return;
        const v = Math.max(1, (parseInt(el.value || '1', 10) || 1) + 1);
        el.value = String(v);
      });
    }
    const confirmBtn = $('confirmMobileQuickscan');
    if (confirmBtn) confirmBtn.addEventListener('click', confirmAction);
    const resetBtn = document.getElementById('resetMobileQuickscan');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => resetState(true));
    }
  }

  document.addEventListener('DOMContentLoaded', async () => {
    els.video = $('cameraPreview');
    if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
      toast('warning', 'Kamera wird von diesem Browser nicht unterstützt');
      return;
    }
    bindEvents();
    setStep('item');
    // WICHTIG: Kamera erst nach User-Tap starten (iOS Safari-Anforderung)
  });
})();

