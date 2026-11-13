(function () {
  "use strict";

  const app = document.getElementById("inventaris-app");
  if (!app) {
    return;
  }

  const lookupBase = app.dataset.lookupBase;
  const aanwezigBase = app.dataset.aanwezigBase;

  const input = document.getElementById("inventaris-input");
  const focusButton = document.getElementById("inventaris-focus");
  const status = document.getElementById("inventaris-status");
  const log = document.getElementById("inventaris-log");
  const count = document.getElementById("inventaris-count");

  const detail = document.getElementById("inventaris-detail");
  const detailTitle = document.getElementById("detail-title");
  const detailMeta = document.getElementById("detail-meta");
  const detailBarcode = document.getElementById("detail-barcode");
  const detailStatus = document.getElementById("detail-status");
  const detailLocatie = document.getElementById("detail-locatie");
  const detailGezien = document.getElementById("detail-gezien");

  const gezien = new Set();
  let laatsteCode = "";
  let laatsteTijd = 0;
  let bezig = false;
  let audioContext = null;

  function beep(frequentie, duur) {
    try {
      audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.frequency.value = frequentie;
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      gain.gain.setValueAtTime(0.08, audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioContext.currentTime + duur);
      oscillator.start();
      oscillator.stop(audioContext.currentTime + duur);
    } catch (error) {
      // Geluid is optioneel.
    }
  }

  function setStatus(tekst, soort) {
    status.className = `mt-3 small text-${soort || "muted"}`;
    status.textContent = tekst;
  }

  function addLog(tekst, soort) {
    const item = document.createElement("li");
    item.className = `text-${soort || "muted"}`;
    item.textContent = `${new Date().toLocaleTimeString()} — ${tekst}`;
    log.prepend(item);
    while (log.children.length > 10) {
      log.lastElementChild.remove();
    }
  }

  function toonDetail(data) {
    detailTitle.textContent = data.titel || "";
    const meta = [];
    if (data.isbn) {
      meta.push(`ISBN ${data.isbn}`);
    }
    if (data.status) {
      meta.push(data.status);
    }
    detailMeta.textContent = meta.join(" · ");
    detailBarcode.textContent = data.barcode || "";
    detailStatus.textContent = data.status || "";
    detailLocatie.textContent = data.locatie || "Onbekend";
    detailGezien.textContent = data.laatst_gezien
      ? new Date(data.laatst_gezien).toLocaleString()
      : "—";
    detail.classList.remove("d-none");
  }

  async function scan(rawCode) {
    const code = (rawCode || "").replace(/[^0-9A-Za-z-]/g, "").toUpperCase();
    if (!code || bezig) {
      return;
    }

    const nu = Date.now();
    if (code === laatsteCode && nu - laatsteTijd < 2000) {
      return;
    }
    laatsteCode = code;
    laatsteTijd = nu;
    bezig = true;
    setStatus(`Zoeken naar ${code}...`, "muted");

    try {
      const lookupUrl = lookupBase.replace("__BARCODE__", encodeURIComponent(code));
      const lookup = await fetch(lookupUrl, { headers: { Accept: "application/json" } });

      if (lookup.status === 401 || lookup.redirected) {
        beep(220, 0.25);
        setStatus("Sessie verlopen. Log opnieuw in.", "danger");
        return;
      }

      const data = await lookup.json().catch(() => ({}));
      if (!lookup.ok) {
        beep(220, 0.25);
        setStatus(data.error || "Exemplaar niet gevonden.", "warning");
        addLog(data.error || `Onbekend: ${code}`, "warning");
        return;
      }

      const aanwezigUrl = aanwezigBase.replace("__BARCODE__", encodeURIComponent(code));
      const aanwezig = await fetch(aanwezigUrl, {
        method: "POST",
        headers: { Accept: "application/json" },
      });

      if (!aanwezig.ok) {
        beep(220, 0.25);
        setStatus("Kon niet als aanwezig markeren.", "danger");
        return;
      }

      const resultaat = await aanwezig.json().catch(() => ({}));
      const samengevoegd = { ...data, ...resultaat };
      toonDetail(samengevoegd);

      gezien.add(code);
      count.textContent = String(gezien.size);

      beep(880, 0.12);
      setStatus(`${samengevoegd.titel} — aanwezig geregistreerd.`, "success");
      addLog(`${code} — ${samengevoegd.titel}`, "success");
    } catch (error) {
      beep(220, 0.25);
      setStatus("Netwerkfout bij het scannen.", "danger");
      addLog("Netwerkfout", "danger");
    } finally {
      bezig = false;
      input.value = "";
      input.focus();
    }
  }

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      scan(input.value);
    }
  });

  focusButton.addEventListener("click", () => {
    input.focus();
    input.select();
  });

  window.addEventListener("focus", () => {
    input.focus();
  });

  input.focus();
})();
