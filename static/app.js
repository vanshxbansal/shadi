async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.message || "Request failed");
  }
  return data;
}

function initDashboard() {
  const runBtn = document.getElementById("run-scrape-btn");
  if (!runBtn) return;

  api("/api/settings")
    .then((cfg) => {
      if (!cfg.mobile && !cfg.phpsessid) {
        document.getElementById("progress-section").classList.remove("hidden");
        document.getElementById("progress-message").textContent =
          "No login saved on the server. Open Settings, enter your mobile number, and click Save Settings.";
      }
    })
    .catch(() => {});

  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("results-section").classList.add("hidden");
    document.getElementById("log-panel").innerHTML = "";
    document.getElementById("progress-bar").style.width = "0%";
    document.getElementById("progress-message").textContent = "Starting scrape...";

    try {
      const cfg = await api("/api/settings");
      if (!cfg.mobile && !cfg.phpsessid) {
        throw new Error("Set mobile number or PHPSESSID in Settings first, then click Save Settings.");
      }
      const { job_id } = await api("/api/scrape", { method: "POST" });
      pollJob(job_id);
    } catch (err) {
      document.getElementById("progress-message").textContent = err.message;
      runBtn.disabled = false;
    }
  });
}

async function pollJob(jobId) {
  const runBtn = document.getElementById("run-scrape-btn");
  const interval = setInterval(async () => {
    try {
      const { job } = await api(`/api/jobs/${jobId}`);
      updateProgress(job);

      if (job.status === "done") {
        clearInterval(interval);
        showResults(job.result);
        runBtn.disabled = false;
      } else if (job.status === "error") {
        clearInterval(interval);
        document.getElementById("progress-message").textContent = job.error || job.message;
        runBtn.disabled = false;
      }
    } catch (err) {
      clearInterval(interval);
      document.getElementById("progress-message").textContent = err.message;
      runBtn.disabled = false;
    }
  }, 1200);
}

function updateProgress(job) {
  document.getElementById("progress-bar").style.width = `${job.progress || 0}%`;
  document.getElementById("progress-message").textContent = job.message || job.status;

  const logPanel = document.getElementById("log-panel");
  if (job.logs && job.logs.length) {
    logPanel.innerHTML = job.logs.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
    logPanel.scrollTop = logPanel.scrollHeight;
  }
}

function showResults(result) {
  if (!result || !result.summary) return;
  const summary = result.summary;

  document.getElementById("results-section").classList.remove("hidden");
  document.getElementById("stat-total").textContent = summary.total_scraped;
  document.getElementById("stat-baseline").textContent = summary.baseline_count;
  document.getElementById("stat-new").textContent = summary.new_count;
  document.getElementById("stat-pages").textContent = summary.pages_fetched;

  document.getElementById("download-new").href = `/api/exports/${summary.new_only_export}`;
  document.getElementById("download-full").href = `/api/exports/${summary.full_export}`;

  const tbody = document.querySelector("#preview-table tbody");
  tbody.innerHTML = "";
  (result.new_preview || []).forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.registration_no || "")}</td>
      <td>${escapeHtml(row.name || "")}</td>
      <td>${escapeHtml(row.gender || "")}</td>
      <td>${escapeHtml(row.date_of_birth || "")}</td>
      <td>${escapeHtml(row.phone_number || "")}</td>
      <td>${escapeHtml(row.location || "")}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initSettings() {
  const form = document.getElementById("settings-form");
  const testBtn = document.getElementById("test-login-btn");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      mobile: document.getElementById("mobile").value.trim(),
      phpsessid: document.getElementById("phpsessid").value.trim(),
      baseline_file: document.getElementById("baseline_file").value.trim(),
    };
    try {
      await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
      document.getElementById("settings-status").textContent = "Settings saved.";
    } catch (err) {
      document.getElementById("settings-status").textContent = err.message;
    }
  });

  testBtn.addEventListener("click", async () => {
    const payload = {
      mobile: document.getElementById("mobile").value.trim(),
      phpsessid: document.getElementById("phpsessid").value.trim(),
      baseline_file: document.getElementById("baseline_file").value.trim(),
    };
    document.getElementById("settings-status").textContent = "Testing login...";
    try {
      await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
      const result = await api("/api/test-login", { method: "POST" });
      document.getElementById("test-result").classList.remove("hidden");
      document.getElementById("test-output").textContent = JSON.stringify(result, null, 2);
      document.getElementById("settings-status").textContent = result.message;
    } catch (err) {
      document.getElementById("settings-status").textContent = err.message;
    }
  });
}

function initHistory() {
  document.querySelectorAll(".set-baseline-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const file = btn.dataset.file;
      try {
        await api("/api/settings", {
          method: "POST",
          body: JSON.stringify({ baseline_file: file }),
        });
        alert(`Baseline set to ${file}`);
        window.location.reload();
      } catch (err) {
        alert(err.message);
      }
    });
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
