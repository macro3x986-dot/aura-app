(() => {
  const state = { mode: null, output: "", filename: "aura_protected.py" };

  const $ = (s) => document.querySelector(s);
  const codeInput = $("#codeInput");
  const fileInput = $("#fileInput");
  const protectBtn = $("#protectBtn");
  const statusText = $("#statusText");
  const outputPanel = $("#outputPanel");
  const outputCode = $("#outputCode");
  const copyBtn = $("#copyBtn");
  const downloadBtn = $("#downloadBtn");
  const progressBar = $("#progressBar");
  const toast = $("#toast");

  function showToast(msg, kind = "success") {
    toast.textContent = msg;
    toast.className = `toast show ${kind}`;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => toast.classList.remove("show"), 3200);
  }

  function setProgress(p) {
    progressBar.style.width = `${p}%`;
  }

  function setStatus(txt) {
    statusText.textContent = txt;
  }

  // Mode cards
  document.querySelectorAll(".mode-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".mode-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      state.mode = card.dataset.mode;
      protectBtn.disabled = false;
      protectBtn.textContent =
        state.mode === "mode01" ? "Protect with Signature" : "Obfuscate Code";
      setStatus(`Selected: ${card.querySelector("h3").textContent}`);
    });
  });

  protectBtn.disabled = true;
  protectBtn.addEventListener("click", () => { protectBtn.disabled = true; });

  // File upload
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.endsWith(".py")) {
      showToast("Only .py files supported", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      codeInput.value = reader.result;
      setStatus(`Loaded: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
      if (state.mode) protectBtn.disabled = false;
    };
    reader.readAsText(file, "utf-8");
  });

  // Protect
  protectBtn.addEventListener("click", async () => {
    if (!state.mode) return showToast("Select a mode first", "error");
    const code = codeInput.value;
    if (!code.trim()) return showToast("Paste or upload code first", "error");

    protectBtn.disabled = true;
    setProgress(25);
    setStatus("Processing...");
    protectBtn.textContent = "Working...";

    try {
      const res = await fetch("/protect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, mode: state.mode }),
      });
      setProgress(70);
      const data = await res.json();

      if (!data.ok) {
        setProgress(0);
        showToast(data.error || "Protection failed", "error");
        setStatus("Error");
        protectBtn.disabled = false;
        protectBtn.textContent = "Try Again";
        return;
      }

      state.output = data.output;
      state.filename = data.filename || "aura_protected.py";
      outputCode.textContent = data.output;
      outputPanel.classList.remove("hidden");
      outputPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      setProgress(100);
      setStatus("Done");
      showToast("Success! File ready", "success");
      protectBtn.disabled = false;
      protectBtn.textContent = "Protect Again";
      setTimeout(() => setProgress(0), 1200);
    } catch (err) {
      setProgress(0);
      setStatus("Network error");
      showToast("Server error: " + err.message, "error");
      protectBtn.disabled = false;
      protectBtn.textContent = "Retry";
    }
  });

  // Copy
  copyBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(state.output);
      showToast("Copied to clipboard", "success");
    } catch {
      showToast("Copy failed", "error");
    }
  });

  // Download
  downloadBtn.addEventListener("click", async () => {
    if (!state.output) return;
    try {
      const res = await fetch("/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: state.output, filename: state.filename }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = state.filename;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded", "success");
    } catch (err) {
      showToast("Download failed: " + err.message, "error");
    }
  });
})();