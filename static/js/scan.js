(function () {
  "use strict";

  const app = document.getElementById("scan-app");
  if (!app) {
    return;
  }

  const lookupBase = app.dataset.lookupBase;
  const saveUrl = app.dataset.saveUrl;
  const defaultCover = "/static/upload/default_cover.png";

  const scanInput = document.getElementById("scan-input");
  const focusButton = document.getElementById("focus-button");
  const scanStatus = document.getElementById("scan-status");
  const scanLog = document.getElementById("scan-log");

  const preview = document.getElementById("preview");
  const previewCover = document.getElementById("preview-cover");
  const previewMeta = document.getElementById("preview-meta");
  const saveForm = document.getElementById("save-form");
  const previewTitle = document.getElementById("preview-titel");
  const previewAuthors = document.getElementById("preview-authors");
  const previewGenres = document.getElementById("preview-genres");
  const previewDescription = document.getElementById("preview-description");
  const previewAantal = document.getElementById("preview-aantal");
  const previewLocatie = document.getElementById("preview-locatie");
  const previewIsbn = document.getElementById("preview-isbn");
  const previewPaginas = document.getElementById("preview-paginas");
  const previewCoverUrl = document.getElementById("preview-cover-url");
  const saveButton = document.getElementById("save-button");
  const cancelButton = document.getElementById("cancel-button");

  const existing = document.getElementById("existing");
  const existingTitle = document.getElementById("existing-title");
  const existingMeta = document.getElementById("existing-meta");
  const existingForm = document.getElementById("existing-form");
  const existingAantal = document.getElementById("existing-aantal");
  const existingSave = document.getElementById("existing-save");
  const existingCancel = document.getElementById("existing-cancel");
  const existingIsbn = document.getElementById("existing-isbn");

  let lastCode = "";
  let lastTime = 0;
  let busy = false;
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
      // Geluid is een extraatje; zonder audio blijft scannen werken.
    }
  }

  function successSound() {
    beep(880, 0.12);
  }

  function errorSound() {
    beep(220, 0.25);
  }

  function setStatus(tekst, soort) {
    scanStatus.className = `mt-2 small text-${soort || "muted"}`;
    scanStatus.textContent = tekst;
  }

  function addLog(tekst, soort) {
    const item = document.createElement("li");
    item.className = `text-${soort || "muted"}`;
    item.textContent = `${new Date().toLocaleTimeString()} — ${tekst}`;
    scanLog.prepend(item);
    while (scanLog.children.length > 5) {
      scanLog.lastElementChild.remove();
    }
  }

  function hidePanels() {
    preview.classList.add("d-none");
    existing.classList.add("d-none");
  }

  function setMeta(data) {
    const delen = [];
    if (data.uitgever) {
      delen.push(data.uitgever);
    }
    if (data.jaar) {
      delen.push(data.jaar);
    }
    if (data.paginas) {
      delen.push(`${data.paginas} pagina's`);
    }
    if (data.bron === "google_books") {
      delen.push("Google Books");
    } else if (data.bron === "open_library") {
      delen.push("Open Library");
    }
    previewMeta.textContent = delen.join(" · ");
  }

  function showPreview(data) {
    hidePanels();
    previewIsbn.value = data.isbn || "";
    previewCoverUrl.value = data.cover_url || "";
    previewPaginas.value = data.paginas || "";
    previewCover.src = data.cover_url || defaultCover;
    previewCover.onerror = () => {
      previewCover.src = defaultCover;
    };
    previewTitle.value = data.titel || "";
    previewAuthors.value = (data.auteurs || []).join(", ");
    previewGenres.value = (data.genres || []).join(", ");
    previewDescription.value = data.beschrijving || "";
    previewAantal.value = "1";
    previewLocatie.value = "";
    setMeta(data);
    preview.classList.remove("d-none");
    if (!data.titel) {
      previewTitle.focus();
    }
  }

  function showExisting(data) {
    hidePanels();
    existingIsbn.value = data.isbn || "";
    existingTitle.textContent = data.titel || "";
    const delen = [];
    if (typeof data.aantal === "number") {
      delen.push(`${data.aantal} exemplaren totaal`);
    }
    if (typeof data.beschikbaar === "number") {
      delen.push(`${data.beschikbaar} beschikbaar`);
    }
    if (data.auteurs && data.auteurs.length) {
      delen.push(data.auteurs.join(", "));
    }
    existingMeta.textContent = delen.join(" · ");
    existingAantal.value = "1";
    existing.classList.remove("d-none");
    existingAantal.focus();
    existingAantal.select();
  }

  async function lookup(rawCode) {
    const code = (rawCode || "").replace(/[^0-9Xx]/g, "");
    if (!code || busy) {
      return;
    }

    const nu = Date.now();
    if (code === lastCode && nu - lastTime < 2000) {
      return;
    }
    lastCode = code;
    lastTime = nu;
    busy = true;
    hidePanels();
    setStatus(`Zoeken naar ${code}...`, "muted");

    try {
      const url = lookupBase.replace("__ISBN__", encodeURIComponent(code));
      const response = await fetch(url, { headers: { Accept: "application/json" } });

      if (response.status === 401 || response.redirected) {
        errorSound();
        setStatus("Sessie verlopen. Log opnieuw in.", "danger");
        return;
      }

      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        errorSound();
        setStatus("Onverwacht antwoord van de server.", "danger");
        return;
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        errorSound();
        const melding = data.error || "Boek niet gevonden.";
        setStatus(melding, "warning");
        addLog(melding, "warning");
        showPreview({
          isbn: data.isbn || code,
          titel: "",
          auteurs: [],
          genres: [],
          beschrijving: "",
          paginas: null,
          cover_url: null,
        });
        return;
      }

      if (data.bestaat) {
        successSound();
        setStatus(`Bestaat al: ${data.titel}`, "success");
        addLog(`Bestaat al: ${data.titel}`, "success");
        showExisting(data);
      } else {
        successSound();
        setStatus(`Gevonden: ${data.titel}`, "success");
        addLog(`Nieuw: ${data.titel}`, "success");
        showPreview(data);
      }
    } catch (error) {
      errorSound();
      setStatus("Netwerkfout bij het zoeken. Probeer opnieuw.", "danger");
      addLog("Netwerkfout bij zoeken", "danger");
    } finally {
      busy = false;
      scanInput.value = "";
      if (preview.classList.contains("d-none") && existing.classList.contains("d-none")) {
        scanInput.focus();
      }
    }
  }

  async function opslaan(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (response.redirected) {
      return {
        response: { ok: false },
        data: { error: "Sessie verlopen. Log opnieuw in." },
      };
    }

    const data = await response.json().catch(() => ({}));
    return { response, data };
  }

  saveForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) {
      return;
    }

    const titel = previewTitle.value.trim();
    if (!titel) {
      errorSound();
      setStatus("Titel is verplicht.", "danger");
      previewTitle.focus();
      return;
    }

    busy = true;
    saveButton.disabled = true;
    setStatus("Opslaan...", "muted");

    const payload = {
      isbn: previewIsbn.value,
      titel: titel,
      auteurs: previewAuthors.value,
      genres: previewGenres.value,
      beschrijving: previewDescription.value.trim(),
      aantal: previewAantal.value,
      locatie: previewLocatie.value,
      paginas: previewPaginas.value,
      cover_url: previewCoverUrl.value,
    };

    try {
      const { response, data } = await opslaan(saveUrl, payload);
      if (!response.ok) {
        errorSound();
        setStatus(data.error || "Opslaan mislukt.", "danger");
        return;
      }
      successSound();
      const melding = data.bericht || "Boek opgeslagen.";
      setStatus(melding, "success");
      addLog(melding, "success");
      hidePanels();
      scanInput.value = "";
      scanInput.focus();
    } catch (error) {
      errorSound();
      setStatus("Netwerkfout bij opslaan.", "danger");
    } finally {
      busy = false;
      saveButton.disabled = false;
    }
  });

  existingForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) {
      return;
    }

    busy = true;
    existingSave.disabled = true;
    setStatus("Exemplaren toevoegen...", "muted");

    try {
      const { response, data } = await opslaan(saveUrl, {
        isbn: existingIsbn.value,
        aantal: existingAantal.value,
      });
      if (!response.ok) {
        errorSound();
        setStatus(data.error || "Toevoegen mislukt.", "danger");
        return;
      }
      successSound();
      const melding = data.bericht || "Exemplaren toegevoegd.";
      setStatus(melding, "success");
      addLog(melding, "success");
      hidePanels();
      scanInput.value = "";
      scanInput.focus();
    } catch (error) {
      errorSound();
      setStatus("Netwerkfout bij toevoegen.", "danger");
    } finally {
      busy = false;
      existingSave.disabled = false;
    }
  });

  scanInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      lookup(scanInput.value);
    }
  });

  focusButton.addEventListener("click", () => {
    scanInput.focus();
    scanInput.select();
  });

  cancelButton.addEventListener("click", () => {
    hidePanels();
    scanInput.focus();
  });

  existingCancel.addEventListener("click", () => {
    hidePanels();
    scanInput.focus();
  });

  window.addEventListener("focus", () => {
    if (preview.classList.contains("d-none") && existing.classList.contains("d-none")) {
      scanInput.focus();
    }
  });

  scanInput.focus();
})();
