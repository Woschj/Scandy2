// Mobile Quickscan mit Kamera-Vorschau und BarcodeDetector
(function() {
  let mediaStream = null;
  let useEnvironment = true;
  let torchOn = false;
  let selectedItem = null; // { barcode, type, name, status, quantity }
  let selectedWorker = null; // { barcode, firstname, lastname }
  let currentStep = null; // 'item' | 'worker'
  let detectionActive = false;
  let codeReader = null; // ZXing reader
  let zxingActive = false;
  let quaggaActive = false;
  let lastScan = { code: null, codeNorm: null, ts: 0 };
  let pauseUntilTs = 0; // kurze Pause nach einem Treffer
  let handling = false; // verhindert parallele Verarbeitung
  let lastHitTs = 0;
  let pureReader = null; // ZXing library reader (ohne Browser-Helper)
  let captureCanvas = null;
  let captureCtx = null;
  let detectionBuffer = new Map(); // normCode -> { count, lastTs }
  let html5qrcodeInstance = null;
  let isStartingCamera = false;
  const USE_HTML5_QR = true; // Standardmäßig aktivieren: robust auf Mobilgeräten
  const USE_QUAGGA = false;   // Temporär deaktivieren, erzeugt zu viele Geistertreffer
  const USE_ZXING = false;    // Vorläufig deaktivieren, um Video-Play-Warnungen zu vermeiden

  const els = {};

  function $(id) { return document.getElementById(id); }
  function dbg(...args) {
    try {
      console.debug('[Quickscan]', ...args);
      const panel = $('debugPanel');
      if (panel) {
        const line = args.map(a => {
          try { return typeof a === 'string' ? a : JSON.stringify(a); } catch(e) { return String(a); }
        }).join(' ');
        const ts = new Date().toLocaleTimeString();
        panel.textContent = `[${ts}] ${line}\n` + panel.textContent;
      }
    } catch (e) {}
  }

  function ensureVideoVisible() {
    try {
      const fb = document.getElementById('html5qrcode');
      if (fb) fb.classList.add('hidden');
      const cam = document.getElementById('cameraContainer');
      if (cam) { cam.classList.remove('hidden'); cam.style.display = 'block'; cam.style.opacity = '1'; }
      if (!els.video) return;
      els.video.classList.remove('hidden');
      els.video.style.display = 'block';
      els.video.style.visibility = 'visible';
      els.video.style.opacity = '1';
      els.video.setAttribute('playsinline', 'true');
      els.video.setAttribute('autoplay', 'true');
      // Debug Events
      const once = (ev) => {
        const h = () => { dbg('video event', ev, { rs: els.video.readyState, w: els.video.videoWidth, h: els.video.videoHeight }); els.video.removeEventListener(ev, h); };
        els.video.addEventListener(ev, h);
      };
      ['loadedmetadata','loadeddata','canplay','playing'].forEach(once);
    } catch(_) {}
  }

  function appendScanLog(entry) {
    try {
      const log = document.getElementById('scanLog');
      if (!log) return;
      const li = document.createElement('li');
      li.className = 'flex items-center justify-between rounded-lg border border-base-200 bg-base-100 px-3 py-1.5';
      li.innerHTML = `<span class="truncate">${entry.text}</span><span class="text-xs opacity-60">${new Date().toLocaleTimeString()}</span>`;
      log.prepend(li);
      // max 8 Einträge
      while (log.children.length > 8) log.removeChild(log.lastChild);
    } catch (e) {}
  }

  function setButtonState() {}

  function pauseDetect(ms = 1500) {
    pauseUntilTs = Date.now() + ms;
  }

  function isPaused() {
    return Date.now() < pauseUntilTs;
  }

  function normalizeCode(raw) {
    try {
      return String(raw || '')
        .trim()
        .replace(/\s+/g, '')
        .replace(/[-_]+/g, '')
        .toUpperCase();
    } catch (e) {
      return String(raw || '');
    }
  }

  function getReadersForStep() {
    // Worker: Code128 + Code39 (robuster für Ausweise), Item: volle Palette
    if (currentStep === 'worker') {
      return ['code_128_reader', 'code_39_reader'];
    }
    return [
      'code_128_reader',
      'ean_reader',
      'ean_8_reader',
      'code_39_reader',
      'upc_reader',
      'upc_e_reader',
      'i2of5_reader'
    ];
  }

  function shouldAcceptDetection(normCode) {
    const now = Date.now();
    const entry = detectionBuffer.get(normCode) || { count: 0, lastTs: 0 };
    if (now - entry.lastTs > 800) {
      entry.count = 0;
    }
    entry.count += 1;
    entry.lastTs = now;
    detectionBuffer.set(normCode, entry);
    // Mindestens 2 aufeinander folgende Frames, um Fehl-Erkennungen zu minimieren
    return entry.count >= 2;
  }

  function setStep(step) {
    currentStep = step; // 'item' | 'worker'
    // Erkennungspuffer/Hints zurücksetzen bei Schrittwechsel
    detectionBuffer = new Map();
    lastScan = { code: null, codeNorm: null, ts: 0 };
    pureReader = null; // erzwinge Neu-Initialisierung mit passenden Hints
    const hint = $('scanHint');
    if (hint) hint.textContent = 'Scannen…';
  }

  function resizeOverlay() {
    if (!els.overlay || !els.video) return;
    const w = els.video.clientWidth || 0;
    const h = els.video.clientHeight || 0;
    if (!w || !h) return;
    const dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    els.overlay.width = Math.floor(w * dpr);
    els.overlay.height = Math.floor(h * dpr);
    els.overlay.style.width = w + 'px';
    els.overlay.style.height = h + 'px';
    els.overlayCtx = els.overlay.getContext('2d');
    els.overlayCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function clearOverlay() {
    if (!els.overlayCtx || !els.overlay) return;
    els.overlayCtx.clearRect(0, 0, els.overlay.width, els.overlay.height);
  }

  function drawGuide() {
    if (!els.overlayCtx || !els.overlay) return;
    const ctx = els.overlayCtx;
    const w = els.overlay.clientWidth || parseInt(els.overlay.style.width, 10) || 0;
    const h = els.overlay.clientHeight || parseInt(els.overlay.style.height, 10) || 0;
    const size = Math.min(w, h) * 0.5; // 50% des kleineren Maßes
    const x = (w - size) / 2;
    const y = (h - size) / 2;
    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,255,0.85)';
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 8]);
    ctx.strokeRect(x, y, size, size);
    // Scanning-Linie animiert
    const t = (performance.now() % 1600) / 1600; // 0..1
    const scanY = y + t * size;
    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(59,130,246,0.85)'; // blue-500
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x + 4, scanY);
    ctx.lineTo(x + size - 4, scanY);
    ctx.stroke();
    ctx.restore();
  }

  function getVideoLayout() {
    // Berechne Mapping von Video-Quellkoordinaten -> gerendertes Video im Canvas (object-contain)
    if (!els.video || !els.overlay) return null;
    const viewW = els.overlay.clientWidth || parseInt(els.overlay.style.width, 10) || 0;
    const viewH = els.overlay.clientHeight || parseInt(els.overlay.style.height, 10) || 0;
    const srcW = els.video.videoWidth || 0;
    const srcH = els.video.videoHeight || 0;
    if (!viewW || !viewH || !srcW || !srcH) return null;
    const scale = Math.min(viewW / srcW, viewH / srcH);
    const drawW = srcW * scale;
    const drawH = srcH * scale;
    const offsetX = (viewW - drawW) / 2;
    const offsetY = (viewH - drawH) / 2;
    return { srcW, srcH, viewW, viewH, scale, offsetX, offsetY };
  }

  function drawBoxes(results) {
    if (!els.overlayCtx || !els.overlay) return;
    const ctx = els.overlayCtx;
    clearOverlay();
    ctx.save();
    ctx.strokeStyle = '#22c55e'; // green-500
    ctx.lineWidth = 3;
    const layout = getVideoLayout();
    (results || []).forEach(r => {
      const bb = r.boundingBox;
      if (bb && layout) {
        const x = layout.offsetX + bb.x * layout.scale;
        const y = layout.offsetY + bb.y * layout.scale;
        const w = bb.width * layout.scale;
        const h = bb.height * layout.scale;
        ctx.strokeRect(x, y, w, h);
      }
      // Fallback: Eckpunkte (manche Browser liefern cornerPoints statt boundingBox)
      if (r.cornerPoints && r.cornerPoints.length && layout) {
        ctx.beginPath();
        r.cornerPoints.forEach((p, i) => {
          const px = layout.offsetX + p.x * layout.scale;
          const py = layout.offsetY + p.y * layout.scale;
          if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        });
        ctx.closePath();
        ctx.stroke();
      }
    });
    ctx.restore();
  }

  function drawZXingResult(result) {
    if (!els.overlayCtx || !els.overlay || !result) return;
    const ctx = els.overlayCtx;
    const layout = getVideoLayout();
    clearOverlay();
    if (!layout) return;
    const pts = result.resultPoints || [];
    if (!pts.length) return;
    ctx.save();
    ctx.strokeStyle = '#22c55e';
    ctx.fillStyle = '#22c55e';
    ctx.lineWidth = 2.5;
    // Punkte verbinden
    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = layout.offsetX + p.x * layout.scale;
      const y = layout.offsetY + p.y * layout.scale;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    if (pts.length > 1) ctx.closePath();
    ctx.stroke();
    // Punkte markieren
    pts.forEach(p => {
      const x = layout.offsetX + p.x * layout.scale;
      const y = layout.offsetY + p.y * layout.scale;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.restore();
  }

  function setScanStatus(scanning) {
    if (!els.status) return;
    if (scanning) {
      els.status.textContent = 'Scanne…';
      els.status.className = 'absolute top-2 left-2 bg-black/60 text-white text-xs md:text-sm px-2 py-1 rounded';
    } else {
      els.status.textContent = 'Treffer!';
      els.status.className = 'absolute top-2 left-2 bg-green-600/80 text-white text-xs md:text-sm px-2 py-1 rounded';
    }
  }

  async function startCamera() {
    if (isStartingCamera) { dbg('startCamera ignored (already starting)'); return; }
    isStartingCamera = true;
    try {
      dbg('startCamera invoked', { step: currentStep });
      stopCamera();
      // Optional: html5-qrcode (deaktiviert)
      if (USE_HTML5_QR && window.Html5Qrcode) {
        try {
          els.video.classList.add('hidden');
          const fb = document.getElementById('html5qrcode');
          if (fb) fb.classList.remove('hidden');
          html5qrcodeInstance = new Html5Qrcode('html5qrcode');
          const formatsToSupport = [
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF
          ];
          await html5qrcodeInstance.start(
            { facingMode: useEnvironment ? 'environment' : 'user' },
            { fps: 20, qrbox: 280, formatsToSupport },
            (decodedText) => {
              const raw = String(decodedText || '').trim();
              const norm = normalizeCode(raw);
              if (isPaused() || handling) return;
              if (!shouldAcceptDetection(norm)) return;
              dbg('html5-qrcode result', { raw, norm });
              setScanStatus(false);
              handleBarcode(raw);
            }
          );
          detectionActive = true;
          try { toast('info', 'Scanner aktiv'); } catch(_) {}
          return; // kein weiteres Setup nötig
        } catch (e0) {
          dbg('html5-qrcode failed, fallback to browser', e0);
        }
      }
      // Optional: Quagga (deaktiviert)
      if (USE_QUAGGA && window.Quagga && currentStep !== 'worker') {
        try {
          const constraints = { facingMode: useEnvironment ? 'environment' : 'user' };
          await new Promise((resolve, reject) => {
            window.Quagga.init({
              inputStream: {
                type: 'LiveStream',
                target: document.getElementById('cameraContainer'),
                constraints: {
                  ...constraints,
                  width: 640,
                  height: 360,
                },
                // Begrenze den Scanbereich auf die Bildmitte, um Störungen am Rand zu vermeiden
                area: { top: '20%', right: '15%', left: '15%', bottom: '20%' }
              },
              locator: { patchSize: 'medium', halfSample: true },
              numOfWorkers: 0,
              decoder: {
                readers: getReadersForStep()
              },
              locate: true,
            }, (err) => {
              if (err) return reject(err);
              try { window.Quagga.start(); quaggaActive = true; } catch (e) {}
              resolve();
            });
          });
          window.Quagga.onDetected((data) => {
            if (!data || !data.codeResult || !data.codeResult.code) return;
            if (isPaused() || handling) return;
            const code = String(data.codeResult.code).trim();
            const norm = normalizeCode(code);
            const now = Date.now();
            dbg('Quagga detected:', { raw: code, norm });
            if (lastScan.codeNorm === norm && now - lastScan.ts < 3000) return;
            const format = (data.codeResult.format || '').toLowerCase();
            if (!shouldAcceptDetection(norm, format)) return;
            lastHitTs = now;
            setScanStatus(false);
            handleBarcode(code);
          });
          window.Quagga.onProcessed(() => {
            // Quagga rendert eigene Overlays; wir lassen unseren Guide klein
            lastHitTs || setScanStatus(true);
          });
          return; // Keine eigene Kamera initialisieren
        } catch (e) {
          console.warn('Quagga Start fehlgeschlagen, falle zurück auf BarcodeDetector/ZXing', e);
          try { window.Quagga.stop(); } catch (e2) {}
          quaggaActive = false;
        }
      }
      const constraints = {
        video: {
          facingMode: useEnvironment ? 'environment' : 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
          advanced: [
            { focusMode: 'continuous' },
            { zoom: 2 }
          ]
        },
        audio: false
      };
      // Browser-API
      mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      dbg('getUserMedia success', { facing: useEnvironment ? 'environment' : 'user' });
      // Sicherstellen, dass der Video-Container sichtbar ist und Fallback versteckt
      ensureVideoVisible();
      // Erzwinge sichtbare Größe (Safari-Layout-Fix)
      try {
        els.video.style.width = '100%';
        els.video.style.height = '100%';
        els.video.style.objectFit = 'contain';
      } catch(_) {}
      try { els.video.pause && els.video.pause(); } catch(_) {}
      els.video.srcObject = mediaStream;
      els.video.muted = true;
      els.video.setAttribute('playsinline', 'true');
      els.video.setAttribute('autoplay', 'true');
      // Warten bis Metadaten geladen sind, dann abspielen (wichtig für iOS)
      await new Promise((resolve) => {
        try {
          if (els.video.readyState >= 2) return resolve();
          const handler = () => { els.video.removeEventListener('loadedmetadata', handler); resolve(); };
          els.video.addEventListener('loadedmetadata', handler, { once: true });
        } catch(_) { resolve(); }
      });
      await els.video.play().catch(() => {});
      // Falls Safari Autoplay blockiert, starte nach User-Gesture nochmals
      if (els.video.paused) {
        dbg('video paused after play, waiting for user gesture');
      }
      // Falls dennoch kein Bild: zweiter Versuch nach kleinem Delay
      if (!els.video.videoWidth || !els.video.videoHeight) {
        await new Promise(r => setTimeout(r, 150));
        ensureVideoVisible();
        try { await els.video.play(); } catch(_) {}
      }
      resizeOverlay();
      // Versuche Torch (Blitz) zu setzen falls verfügbar
      await applyTorch(torchOn);
      startDetectLoop();
    } catch (e) {
      console.warn('Kamera konnte nicht gestartet werden:', e);
      try { toast('warning', 'Kamera konnte nicht gestartet werden. Versuche stabilen Scanner…'); } catch(_) {}
      // Als Fallback: html5-qrcode verwenden, wenn verfügbar
      try {
        if (window.Html5Qrcode) {
          // Video verbergen, Fallback-Container zeigen
          els.video.classList.add('hidden');
          const fb = document.getElementById('html5qrcode');
          if (fb) fb.classList.remove('hidden');
          const html5qrcode = new Html5Qrcode('html5qrcode');
          const formatsToSupport = [
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF
          ];
          await html5qrcode.start(
            { facingMode: useEnvironment ? 'environment' : 'user' },
            { fps: 15, qrbox: 250, formatsToSupport },
            (decodedText, decodedResult) => {
              const raw = String(decodedText || '').trim();
              const norm = normalizeCode(raw);
              if (!shouldAcceptDetection(norm)) return;
              dbg('html5-qrcode result', { raw, norm });
              handleBarcode(raw);
            },
            (errorMessage) => { /* ignore continuous errors */ }
          );
          // Markiere Detection-Loop als aktiv, damit UI-Guide weiterläuft
          detectionActive = true;
          try { toast('info', 'Stabiler Scanner aktiv'); } catch(_) {}
        }
      } catch (e2) {
        console.warn('Fallback html5-qrcode Start fehlgeschlagen:', e2);
        try { toast('error', 'Scanner konnte nicht gestartet werden'); } catch(_) {}
      }
    }
    finally {
      isStartingCamera = false;
    }
  }

  function stopCamera() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
    // Video sauber anhalten und Quelle lösen, um Race-Conditions beim erneuten play() zu vermeiden
    try { if (els.video) { els.video.pause && els.video.pause(); els.video.srcObject = null; } } catch(e) {}
    if (html5qrcodeInstance && typeof html5qrcodeInstance.stop === 'function') {
      try { html5qrcodeInstance.stop().catch(()=>{}); } catch(e) {}
      html5qrcodeInstance = null;
      const fb = document.getElementById('html5qrcode');
      if (fb) fb.classList.add('hidden');
      if (els.video) els.video.classList.remove('hidden');
    }
    detectionActive = false;
    if (quaggaActive && window.Quagga) {
      try { window.Quagga.stop(); } catch (e) {}
      quaggaActive = false;
    }
    if (codeReader && typeof codeReader.reset === 'function') {
      try { codeReader.reset(); } catch (e) {}
    }
    zxingActive = false;
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
    if (quaggaActive) return; // Quagga übernimmt die Erkennung und Overlays
    if (Date.now() < pauseUntilTs) { setScanStatus(true); return; }
    try {
      // 1) Quagga2 bevorzugt, wenn verfügbar und noch nicht gestartet
      if (USE_QUAGGA && window.Quagga && els.video && !window.__quagga_started__ && currentStep !== 'worker') {
        try {
          const constraints = {
            facingMode: useEnvironment ? 'environment' : 'user',
          };
          await new Promise((resolve, reject) => {
            window.Quagga.init({
              inputStream: {
                type: 'LiveStream',
                target: document.getElementById('cameraContainer') || els.video.parentElement,
                constraints: {
                  ...constraints,
                  width: 1280,
                  height: 720,
                },
                // area entfernt: zu restriktiv auf einigen Geräten
              },
              locator: { patchSize: 'medium', halfSample: true },
              numOfWorkers: 0,
              decoder: {
                readers: getReadersForStep()
              },
              locate: true,
            }, (err) => {
              if (err) return reject(err);
              try { window.Quagga.start(); window.__quagga_started__ = true; } catch (e) {}
              resolve();
            });
          });
          window.Quagga.onDetected((data) => {
            if (!data || !data.codeResult || !data.codeResult.code) return;
            if (isPaused() || handling) return;
            const code = String(data.codeResult.code).trim();
            const norm = normalizeCode(code);
            const now = Date.now();
            dbg('Quagga detected:', { raw: code, norm });
            if (lastScan.codeNorm === norm && now - lastScan.ts < 3000) return;
            if (!shouldAcceptDetection(norm)) return;
            lastHitTs = now;
            setScanStatus(false);
            // Quagga zeichnet sein eigenes Overlay im Container; unser Guide bleibt bestehen
            handleBarcode(code);
          });
          // Optional: onProcessed für visuelles Feedback
          window.Quagga.onProcessed(function(result){
            try {
              clearOverlay();
              drawGuide();
              if (result && result.boxes) {
                const layout = getVideoLayout();
                const ctx = els.overlayCtx;
                if (layout && ctx) {
                  ctx.save();
                  ctx.strokeStyle = 'rgba(255,255,255,0.35)';
                  result.boxes.forEach(box => {
                    ctx.beginPath();
                    box.forEach((p, i) => {
                      const x = layout.offsetX + p[0] * layout.scale;
                      const y = layout.offsetY + p[1] * layout.scale;
                      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                    });
                    ctx.closePath();
                    ctx.stroke();
                  });
                  if (result.box) {
                    ctx.strokeStyle = '#22c55e';
                    ctx.beginPath();
                    result.box.forEach((p, i) => {
                      const x = layout.offsetX + p[0] * layout.scale;
                      const y = layout.offsetY + p[1] * layout.scale;
                      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                    });
                    ctx.closePath();
                    ctx.stroke();
                  }
                  ctx.restore();
                }
              }
            } catch(e) {}
          });
        } catch (e) {
          console.warn('Quagga konnte nicht gestartet werden:', e);
        }
      }

      // 2) Parallel: Wir nutzen BarcodeDetector und ZXing (wenn verfügbar)
      if ('BarcodeDetector' in window) {
        const formats = ['code_128', 'code_39', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf'];
        const detector = new BarcodeDetector({ formats });
        const barcodes = await detector.detect(els.video);
        if (barcodes?.length) {
          dbg('BarcodeDetector hits:', barcodes.map(b => ({ raw: b.rawValue })));
          try { drawBoxes(barcodes); } catch (e) {}
          lastHitTs = Date.now();
          setScanStatus(false);
          const candidate = String(barcodes[0].rawValue || '').trim();
          const norm = normalizeCode(candidate);
          if (!shouldAcceptDetection(norm)) { dbg('BarcodeDetector wait confirm', { norm }); return; }
          handleBarcode(candidate);
          return;
        }
        // Kein Treffer: Status aktualisieren
        setScanStatus(true);
      }
      // Verwende bevorzugt Browser-API; ZXing-Pfade optional abschaltbar
      if (USE_ZXING && window.ZXingBrowser && els.video) {
        if (!codeReader && window.ZXingBrowser.BrowserMultiFormatReader) {
          try {
            const hints = (window.ZXingBrowser.DecodeHintType && window.ZXingBrowser.BarcodeFormat) ? new Map() : undefined;
            if (hints) {
              hints.set(window.ZXingBrowser.DecodeHintType.TRY_HARDER, true);
              const f = window.ZXingBrowser.BarcodeFormat;
              const allowed = (currentStep === 'worker')
                ? [f.CODE_128, f.CODE_39]
                : [f.CODE_128, f.EAN_13, f.EAN_8, f.CODE_39, f.ITF, f.UPC_A, f.UPC_E, f.QR_CODE];
              hints.set(window.ZXingBrowser.DecodeHintType.POSSIBLE_FORMATS, allowed);
            }
            codeReader = new window.ZXingBrowser.BrowserMultiFormatReader(hints, 200);
          } catch (e) {
            codeReader = new window.ZXingBrowser.BrowserMultiFormatReader();
          }
        }
        if (codeReader && !zxingActive) {
          zxingActive = true;
          if (typeof codeReader.decodeFromVideoElementContinuously === 'function') {
            codeReader.decodeFromVideoElementContinuously(els.video, (result, err) => {
              if (result && result.text) {
                try { drawZXingResult(result); } catch (e) {}
                lastHitTs = Date.now();
                dbg('ZXingBrowser result:', { raw: result.text, pts: !!(result.resultPoints && result.resultPoints.length) });
                setScanStatus(false);
                handleBarcode(String(result.text).trim());
              }
            });
          } else if (typeof codeReader.decodeFromVideoElement === 'function') {
            const poll = async () => {
              if (!zxingActive) return;
              try {
                const res = await codeReader.decodeFromVideoElement(els.video);
                if (res && res.text) {
                  try { drawZXingResult(res); } catch (e) {}
                  lastHitTs = Date.now();
                  dbg('ZXingBrowser poll result:', { raw: res.text });
                  setScanStatus(false);
                  handleBarcode(String(res.text).trim());
                }
              } catch (e) {}
              if (zxingActive) setTimeout(poll, 100);
            };
            poll();
          }
        }
      }
      // Reines ZXing (library) Fallback: optional
      if (USE_ZXING && !window.ZXingBrowser && window.ZXing && els.video && els.video.videoWidth) {
        if (!window.__zxing_pure__) {
          try {
            window.__zxing_pure__ = new window.ZXing.BrowserMultiFormatReader();
          } catch (e) { window.__zxing_pure__ = null; }
        }
        const pure = window.__zxing_pure__;
        if (pure && !zxingActive) {
          zxingActive = true;
          const poll = async () => {
            if (!zxingActive) return;
            try {
              const res = await pure.decodeFromVideoElement(els.video);
              if (res && res.text) {
                try { drawZXingResult(res); } catch (e) {}
                lastHitTs = Date.now();
                dbg('ZXing pure result:', { raw: res.text });
                setScanStatus(false);
                handleBarcode(String(res.text).trim());
              }
            } catch (e) {}
            if (zxingActive) setTimeout(poll, 120);
          };
          poll();
        }
      }
      // Fallback: wenn keinerlei ZXing verfügbar, loggen
      if (!window.ZXingBrowser && !window.ZXing) {
        // einmalig loggen wenn tatsächlich keinerlei ZXing verfügbar ist
        if (!window.__zxing_warned__) {
          window.__zxing_warned__ = true;
          console.warn('ZXing nicht verfügbar – nutze nur BarcodeDetector');
        }
      }
      // Letzter Fallback: Reines ZXing (library) über Canvas-Frame
      if (window.ZXing && els.video && els.video.videoWidth && els.video.videoHeight) {
        const text = await tryDecodeWithPureZXing();
        if (text) {
          lastHitTs = Date.now();
          setScanStatus(false);
          handleBarcode(String(text).trim());
          return;
        }
      }
    } catch (e) {
      // weiter versuchen
    }
  }

  async function tryDecodeWithPureZXing() {
    try {
      const ZX = window.ZXing;
      if (!ZX) return null;
      if (!captureCanvas) {
        captureCanvas = document.createElement('canvas');
        captureCtx = captureCanvas.getContext('2d', { willReadFrequently: true });
      }
      const vw = els.video.videoWidth;
      const vh = els.video.videoHeight;
      if (!vw || !vh) return null;
      // Skaliere für Performance, aber genügend Detail
      const targetW = Math.min(800, vw);
      const scale = targetW / vw;
      const targetH = Math.round(vh * scale);
      captureCanvas.width = targetW;
      captureCanvas.height = targetH;
      captureCtx.drawImage(els.video, 0, 0, targetW, targetH);
      const img = captureCtx.getImageData(0, 0, targetW, targetH);
      if (!pureReader) {
        pureReader = new ZX.MultiFormatReader();
        const hints = new Map();
        if (ZX.DecodeHintType && ZX.BarcodeFormat) {
          hints.set(ZX.DecodeHintType.TRY_HARDER, true);
          hints.set(ZX.DecodeHintType.POSSIBLE_FORMATS, [
            ZX.BarcodeFormat.CODE_128,
            ZX.BarcodeFormat.EAN_13,
            ZX.BarcodeFormat.EAN_8,
            ZX.BarcodeFormat.CODE_39,
            ZX.BarcodeFormat.ITF,
            ZX.BarcodeFormat.UPC_A,
            ZX.BarcodeFormat.UPC_E,
            ZX.BarcodeFormat.QR_CODE,
          ]);
        }
        if (pureReader.setHints && hints) pureReader.setHints(hints);
      }
      const luminance = new ZX.RGBLuminanceSource(img.data, targetW, targetH);
      const binaryBitmap = new ZX.BinaryBitmap(new ZX.HybridBinarizer(luminance));
      const result = pureReader.decode(binaryBitmap);
      const text = result.getText ? result.getText() : result.text;
      return text || null;
    } catch (err) {
      return null;
    }
  }

  function startDetectLoop() {
    detectionActive = true;
    const loop = async () => {
      if (!detectionActive) return;
      // UI vorbereiten
      resizeOverlay();
      await detectOnce();
      // Wenn kein aktueller Treffer: Guide zeichnen, sonst Treffer-Overlay bestehen lassen
      if (Date.now() - lastHitTs > 800) {
        setScanStatus(true);
        clearOverlay();
        drawGuide();
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  async function handleBarcode(code) {
    if (!code || !currentStep) return;
    // Debounce: Ignoriere Duplikate innerhalb 1.2s
    const now = Date.now();
    const norm = normalizeCode(code);
    dbg('handleBarcode start', { raw: code, norm, step: currentStep });
    if (lastScan.codeNorm === norm && now - lastScan.ts < 3000) return;
    lastScan = { code, codeNorm: norm, ts: now };
    if (handling) return; // bereits in Verarbeitung
    handling = true;
    // Neue Heuristik: immer beide Typen testen (Priorität je Inhalt)
    const hasLetters = /[A-Z]/.test(norm);
    const likelyEAN = /^\d{6,14}$/.test(norm);
    let ok = false;
    if (hasLetters && !likelyEAN) {
      // Alphanumerisch: zuerst Mitarbeiter, dann Artikel
      ok = await tryLookupWorker(code);
      if (!ok) ok = await tryLookupItem(code);
      if (ok && selectedItem && selectedWorker) await confirmAction();
    } else {
      // Numerisch: zuerst Artikel, dann Mitarbeiter
      ok = await tryLookupItem(code);
      if (!ok) ok = await tryLookupWorker(code);
      if (ok && selectedItem && selectedWorker) await confirmAction();
    }
    if (ok) {
      // Schritt-Hinweis anpassen: wenn Artikel gewählt, wechsle auf Mitarbeiter
      if (selectedItem && !selectedWorker) setStep('worker');
      pauseDetect(1200);
      handling = false;
      return;
    }
    toast('error', 'Nicht gefunden');
    handling = false;
  }

  async function tryLookupItem(barcode) {
    try {
      const found = await scanBarcodeViaAPI(barcode, ['tool','consumable']);
      if (found) {
        dbg('tryLookupItem success', found);
        const item = found.item;
        selectedItem = {
          barcode: item.barcode,
          type: item.type || (found.type === 'consumable' ? 'consumable' : 'tool'),
          name: item.name || 'Artikel',
          status: item.status,
          quantity: typeof item.quantity === 'number' ? item.quantity : (item.current_stock || item.current_amount || 0)
        };
        const itemSum = $('itemSummary');
        if (itemSum) itemSum.textContent = `${selectedItem.name}`;
        appendScanLog({ text: `Artikel: ${selectedItem.name} (${selectedItem.barcode})` });
        setScanStatus(false);
        return true;
      }
      dbg('tryLookupItem failed');
      return false;
    } catch (e) {
      dbg('tryLookupItem error', e);
      return false;
    }
  }

  async function tryLookupWorker(barcode) {
    try {
      const found = await scanBarcodeViaAPI(barcode, ['worker']);
      if (found) {
        dbg('tryLookupWorker success', found);
        const w = found.item || found.worker || {};
        selectedWorker = { barcode: w.barcode, firstname: w.firstname || '', lastname: w.lastname || '' };
        const workerSum = $('workerSummary');
        if (workerSum) workerSum.textContent = `${selectedWorker.firstname} ${selectedWorker.lastname}`.trim();
        appendScanLog({ text: `Mitarbeiter: ${selectedWorker.firstname || ''} ${selectedWorker.lastname || ''} (${selectedWorker.barcode})`.trim() });
        setScanStatus(false);
        return true;
      }
      dbg('tryLookupWorker failed');
      return false;
    } catch (e) {
      dbg('tryLookupWorker error', e);
      return false;
    }
  }

  function buildCodeVariants(code) {
    const c = String(code || '').trim();
    const variants = new Set([c]);
    // Entferne Whitespaces innerhalb
    const noSpace = c.replace(/\s+/g, '');
    variants.add(noSpace);
    variants.add(noSpace.toUpperCase());
    variants.add(noSpace.toLowerCase());
    // Ersetze häufige Trennzeichen-Varianten
    variants.add(noSpace.replace(/[-_]+/g, ''));
    return Array.from(variants).filter(Boolean);
  }

  async function scanBarcodeViaAPI(code, allowedTypes) {
    const variants = buildCodeVariants(code);
    dbg('scanBarcodeViaAPI', { code, variants, allowedTypes });
    for (const v of variants) {
      try {
        const res = await fetch('/mobile/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ barcode: v })
        });
        if (!res.ok) {
          const txt = await res.text().catch(() => '');
          dbg('API miss', { variant: v, status: res.status, body: txt });
          continue;
        }
        const data = await res.json();
        if (data && data.success && data.item && (!allowedTypes || allowedTypes.includes(data.item.type))) {
          dbg('API hit', data);
          return { type: data.item.type, item: data.item, lending: data.lending || null };
        }
      } catch (e) {
        dbg('API error', e);
        // ignore and try next variant
      }
    }
    dbg('API no hit for any variant');
    return null;
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
    const unifiedBtn = $('scanUnifiedBtn');
    if (unifiedBtn) unifiedBtn.addEventListener('click', async () => {
      // Einheitlicher Modus: wir starten die Kamera und prüfen immer beide Typen
      setStep('item');
      await startCamera();
    });
    const switchBtn = $('switchCameraBtn');
    if (switchBtn) switchBtn.addEventListener('click', async () => {
      useEnvironment = !useEnvironment;
      await startCamera();
    });
    const fallbackBtn = $('fallbackScannerBtn');
    if (fallbackBtn) fallbackBtn.addEventListener('click', async () => {
      try {
        if (mediaStream) stopCamera();
        if (window.Html5Qrcode) {
          const html5qrcode = new Html5Qrcode('html5qrcode');
          els.video.classList.add('hidden');
          const fb = document.getElementById('html5qrcode');
          if (fb) fb.classList.remove('hidden');
          const formatsToSupport = [
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.ITF
          ];
          await html5qrcode.start({ facingMode: useEnvironment ? 'environment' : 'user' }, { fps: 15, qrbox: 250, formatsToSupport }, (decodedText) => {
            const raw = String(decodedText || '').trim();
            const norm = normalizeCode(raw);
            if (!shouldAcceptDetection(norm)) return;
            dbg('html5-qrcode manual start', { raw, norm });
            handleBarcode(raw);
          });
          detectionActive = true;
          try { toast('info', 'Stabiler Scanner aktiv'); } catch(_) {}
        } else {
          toast('info', 'Stabiler Scanner nicht verfügbar');
        }
      } catch (e) {
        dbg('fallback start error', e);
        toast('error', 'Stabiler Scanner konnte nicht gestartet werden');
      }
    });
    const cameraTap = $('cameraContainer');
    if (cameraTap) cameraTap.addEventListener('click', async () => {
      if (!detectionActive) {
        await startCamera();
      }
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
    els.overlay = $('scanOverlay');
    els.status = $('scanStatus');
    if (!('mediaDevices' in navigator) || !navigator.mediaDevices.getUserMedia) {
      toast('warning', 'Kamera wird von diesem Browser nicht unterstützt');
      return;
    }
    bindEvents();
    setStep('item');
    resizeOverlay();
    window.addEventListener('resize', resizeOverlay);
    // WICHTIG: Kamera erst nach User-Tap starten (iOS Safari-Anforderung)
  });
})();

