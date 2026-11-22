"""Antarmuka web sederhana untuk Wikiwisata Serving (tanpa dependensi eksternal)."""

from __future__ import annotations

import html


def render_ui_html(default_config: str = "B4") -> str:
    """Bangun halaman HTML UI yang menampilkan jawaban, sitasi, tanggal data, dan status abstain."""
    configs = ["B0", "B1", "B2", "B3", "B4", "B5", "B6"]
    options = "\n".join(
        f'<option value="{cfg}"{" selected" if cfg == default_config else ""}>{cfg}</option>'
        for cfg in configs
    )

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Wikiwisata — Asisten Rencana Perjalanan</title>
  <style>
    :root {{
      --bg: #f6f8fa;
      --card: #ffffff;
      --text: #1f2328;
      --muted: #59636e;
      --border: #d0d7de;
      --primary: #0969da;
      --ok-bg: #dafbe1;
      --ok-fg: #116329;
      --warn-bg: #fff8c5;
      --warn-fg: #9a6700;
      --err-bg: #ffebe9;
      --err-fg: #cf222e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    .container {{ max-width: 880px; margin: 32px auto; padding: 0 16px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    h1 {{ margin: 0 0 4px 0; font-size: 1.4rem; }}
    .subtitle {{ color: var(--muted); font-size: 0.9rem; margin: 0 0 16px 0; }}
    label {{ display: block; font-weight: 600; font-size: 0.85rem; margin-bottom: 4px; }}
    textarea, input, select {{
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font: inherit;
      margin-bottom: 12px;
    }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .actions {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    button {{
      padding: 9px 16px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }}
    button.primary {{ background: var(--primary); color: #fff; border-color: var(--primary); }}
    button.abstain-btn {{ background: var(--warn-bg); color: var(--warn-fg); border-color: #d4a72c; }}
    button.abstain-btn.active {{ background: var(--err-bg); color: var(--err-fg); border-color: #cf222e; }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
    }}
    .badge.answered {{ background: var(--ok-bg); color: var(--ok-fg); }}
    .badge.abstain {{ background: var(--err-bg); color: var(--err-fg); }}
    .badge.supported {{ background: var(--ok-bg); color: var(--ok-fg); }}
    .badge.unknown {{ background: var(--warn-bg); color: var(--warn-fg); }}
    .badge.contradicted {{ background: var(--err-bg); color: var(--err-fg); }}
    .meta {{ color: var(--muted); font-size: 0.82rem; font-family: ui-monospace, monospace; }}
    ul {{ padding-left: 18px; margin: 8px 0; }}
    li {{ margin-bottom: 6px; }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Wikiwisata</h1>
      <p class="subtitle">Asisten rencana perjalanan yang menjawab dengan bukti, sitasi, dan tanggal data.</p>
      <form id="query-form">
        <label for="question">Pertanyaan Perjalanan</label>
        <textarea id="question" rows="3" placeholder="Contoh: Jam buka Keraton Yogyakarta saat ini?" required></textarea>
        <div class="row">
          <div>
            <label for="travel_date">Tanggal Perjalanan</label>
            <input id="travel_date" type="date" value="2026-12-01" required />
          </div>
          <div>
            <label for="config_id">Konfigurasi</label>
            <select id="config_id">
              {options}
            </select>
          </div>
        </div>
        <div class="actions">
          <button type="submit" class="primary" id="submit-btn">Tanyakan</button>
          <button type="button" class="abstain-btn" id="abstain-indicator" disabled>Status: Tidak Ada Bukti (Abstain)</button>
        </div>
      </form>
    </div>

    <div id="result-card" class="card hidden">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <strong>Hasil Jawaban</strong>
        <span id="verdict-badge" class="badge"></span>
      </div>
      <p id="answer-text"></p>
      <div id="abstain-box" class="hidden" style="padding:10px; background:var(--warn-bg); border-radius:6px; margin:10px 0;">
        <strong>Alasan Tidak Ada Bukti / Abstain:</strong> <span id="abstain-reason"></span>
      </div>

      <h3>Klaim Atomik</h3>
      <ul id="claims-list"></ul>

      <h3>Sitasi &amp; Tanggal Data</h3>
      <ul id="citations-list"></ul>

      <hr style="border:none; border-top:1px solid var(--border); margin:12px 0;" />
      <div class="meta" id="trace-meta"></div>
    </div>
  </div>

  <script>
    const form = document.getElementById("query-form");
    const submitBtn = document.getElementById("submit-btn");
    const abstainBtn = document.getElementById("abstain-indicator");
    const resultCard = document.getElementById("result-card");

    form.addEventListener("submit", async (e) => {{
      e.preventDefault();
      submitBtn.disabled = true;
      submitBtn.textContent = "Memproses...";
      try {{
        const res = await fetch("/predict", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            question: document.getElementById("question").value,
            travel_date: document.getElementById("travel_date").value,
            config_id: document.getElementById("config_id").value,
            source: "ui"
          }})
        }});
        const data = await res.json();
        renderResult(data);
      }} catch (err) {{
        alert("Gagal memanggil API: " + err);
      }} finally {{
        submitBtn.disabled = false;
        submitBtn.textContent = "Tanyakan";
      }}
    }});

    function renderResult(data) {{
      resultCard.classList.remove("hidden");
      const verdict = data.verdict || "abstain";
      const badge = document.getElementById("verdict-badge");
      badge.textContent = verdict.toUpperCase();
      badge.className = "badge " + verdict;

      if (verdict === "abstain") {{
        abstainBtn.classList.add("active");
        abstainBtn.textContent = "Tidak Ada Bukti (Abstain Aktif)";
        document.getElementById("abstain-box").classList.remove("hidden");
        document.getElementById("abstain-reason").textContent = data.abstain_reason || "-";
      }} else {{
        abstainBtn.classList.remove("active");
        abstainBtn.textContent = "Status: Terjawab dengan Bukti";
        document.getElementById("abstain-box").classList.add("hidden");
      }}

      document.getElementById("answer-text").textContent = data.answer || "";

      const claimsList = document.getElementById("claims-list");
      claimsList.innerHTML = "";
      (data.claims || []).forEach((c) => {{
        const li = document.createElement("li");
        li.innerHTML = `<span class="badge ${{c.status}}">${{c.status}}</span> ${{escapeHtml(c.text)}} <span class="meta">[${{(c.evidence_ids || []).join(", ")}}]</span>`;
        claimsList.appendChild(li);
      }});
      if (!data.claims || data.claims.length === 0) {{
        claimsList.innerHTML = "<li class='meta'>Tidak ada klaim atomik.</li>";
      }}

      const citationsList = document.getElementById("citations-list");
      citationsList.innerHTML = "";
      (data.citations || []).forEach((cit) => {{
        const li = document.createElement("li");
        const dateLabel = cit.lastedit ? ` | lastedit: ${{cit.lastedit}}` : "";
        li.textContent = `${{cit.title}} — ${{cit.section}} (doc: ${{cit.doc_id}}, rev: ${{cit.rev_id}}, passage: ${{cit.passage_id}}${{dateLabel}})`;
        citationsList.appendChild(li);
      }});
      if (!data.citations || data.citations.length === 0) {{
        citationsList.innerHTML = "<li class='meta'>Tidak ada sitasi dokumen.</li>";
      }}

      const meta = data.meta || {{}};
      document.getElementById("trace-meta").textContent =
        `request_id=${{meta.request_id || "-"}} | config=${{meta.config_id || "-"}} | latency=${{meta.latency_ms ?? "-"}} ms | fallback=${{Boolean(meta.fallback)}}`;
    }}

    function escapeHtml(str) {{
      return String(str).replace(/[&<>"']/g, (m) => ({{
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }}[m]));
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    """Jalankan server UI + API Wikiwisata."""
    from wikiwisata.serving.api import main as api_main

    api_main()


if __name__ == "__main__":
    main()
