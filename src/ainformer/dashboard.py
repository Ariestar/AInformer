from __future__ import annotations

from textwrap import dedent


def dashboard_html() -> str:
    return dedent(
        r"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>AInformer Dashboard</title>
          <style>
            :root {
              color-scheme: light;
              --bg: #f4efe6;
              --bg-accent: #efe0c6;
              --panel: rgba(255, 251, 245, 0.86);
              --panel-strong: #fffaf2;
              --text: #251a0f;
              --muted: #715d4a;
              --border: rgba(95, 71, 46, 0.18);
              --shadow: 0 22px 60px rgba(74, 51, 28, 0.12);
              --accent: #d96f32;
              --accent-deep: #9a3f14;
              --ok: #1f7a55;
              --error: #a43f32;
              --chip: #f0e1d0;
            }

            * {
              box-sizing: border-box;
            }

            body {
              margin: 0;
              min-height: 100vh;
              font-family: "Aptos", "Segoe UI Variable", "Segoe UI", sans-serif;
              color: var(--text);
              background:
                radial-gradient(circle at top left, rgba(217, 111, 50, 0.22), transparent 34%),
                radial-gradient(circle at top right, rgba(155, 88, 45, 0.16), transparent 28%),
                linear-gradient(180deg, #f8f2e8 0%, var(--bg) 52%, #efe6d9 100%);
            }

            .shell {
              width: min(1320px, calc(100vw - 32px));
              margin: 0 auto;
              padding: 28px 0 40px;
            }

            .hero {
              padding: 24px;
              border: 1px solid var(--border);
              border-radius: 28px;
              background: linear-gradient(135deg, rgba(255, 248, 239, 0.92), rgba(243, 226, 198, 0.82));
              box-shadow: var(--shadow);
              backdrop-filter: blur(18px);
            }

            .hero h1 {
              margin: 0 0 10px;
              font-family: Georgia, "Times New Roman", serif;
              font-size: clamp(2rem, 4vw, 3.4rem);
              line-height: 0.95;
              letter-spacing: -0.03em;
            }

            .hero p {
              margin: 0;
              max-width: 64ch;
              color: var(--muted);
              font-size: 1rem;
              line-height: 1.6;
            }

            .toolbar {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
              gap: 14px;
              margin-top: 20px;
            }

            .control,
            .stat,
            .panel {
              border: 1px solid var(--border);
              border-radius: 22px;
              background: var(--panel);
              box-shadow: var(--shadow);
              backdrop-filter: blur(12px);
            }

            .control,
            .stat {
              padding: 16px 18px;
            }

            .control label,
            .control legend {
              display: block;
              margin-bottom: 8px;
              color: var(--muted);
              font-size: 0.82rem;
              font-weight: 600;
              text-transform: uppercase;
              letter-spacing: 0.08em;
            }

            .control input[type="number"],
            .control input[type="search"] {
              width: 100%;
              padding: 12px 14px;
              border: 1px solid rgba(95, 71, 46, 0.16);
              border-radius: 14px;
              background: rgba(255, 255, 255, 0.85);
              color: var(--text);
              font: inherit;
            }

            .control-row {
              display: flex;
              align-items: center;
              gap: 10px;
              min-height: 48px;
            }

            .button {
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: 100%;
              min-height: 48px;
              padding: 12px 18px;
              border: 0;
              border-radius: 16px;
              background: linear-gradient(135deg, var(--accent), var(--accent-deep));
              color: #fff8f0;
              font: inherit;
              font-weight: 700;
              cursor: pointer;
              transition: transform 160ms ease, box-shadow 160ms ease;
              box-shadow: 0 16px 28px rgba(154, 63, 20, 0.25);
            }

            .button:hover {
              transform: translateY(-1px);
            }

            .stats {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
              gap: 14px;
              margin-top: 16px;
            }

            .stat .label {
              color: var(--muted);
              font-size: 0.82rem;
              text-transform: uppercase;
              letter-spacing: 0.08em;
            }

            .stat .value {
              margin-top: 10px;
              font-size: clamp(1.4rem, 3vw, 2.3rem);
              font-weight: 800;
              line-height: 1;
            }

            .status-line {
              margin-top: 18px;
              color: var(--muted);
              font-size: 0.95rem;
            }

            .layout {
              display: grid;
              grid-template-columns: 320px minmax(0, 1fr);
              gap: 18px;
              margin-top: 20px;
              align-items: start;
            }

            .panel {
              padding: 18px;
            }

            .panel h2 {
              margin: 0 0 14px;
              font-size: 1rem;
              letter-spacing: 0.01em;
            }

            .source-list,
            .error-list,
            .record-list {
              display: grid;
              gap: 12px;
            }

            .source-card,
            .record-card,
            .error-card {
              padding: 14px;
              border-radius: 18px;
              border: 1px solid var(--border);
              background: var(--panel-strong);
            }

            .source-card.is-empty {
              opacity: 0.62;
            }

            .source-card h3,
            .record-card h3,
            .error-card h3 {
              margin: 0;
              font-size: 0.98rem;
            }

            .record-card h3 a {
              color: inherit;
              text-decoration: none;
            }

            .record-card h3 a:hover {
              color: var(--accent-deep);
            }

            .meta {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              margin-top: 10px;
            }

            .chip {
              display: inline-flex;
              align-items: center;
              min-height: 28px;
              padding: 0 10px;
              border-radius: 999px;
              background: var(--chip);
              color: var(--muted);
              font-size: 0.82rem;
              font-weight: 600;
            }

            .source-name {
              margin-top: 8px;
              color: var(--muted);
              font-size: 0.9rem;
            }

            .excerpt {
              margin: 12px 0 0;
              color: var(--muted);
              font-size: 0.95rem;
              line-height: 1.7;
              white-space: pre-line;
              display: -webkit-box;
              -webkit-line-clamp: 7;
              -webkit-box-orient: vertical;
              overflow: hidden;
            }

            .group {
              padding: 18px;
              border-radius: 24px;
              background: linear-gradient(180deg, rgba(255, 249, 241, 0.96), rgba(246, 236, 218, 0.86));
              border: 1px solid var(--border);
            }

            .group + .group {
              margin-top: 16px;
            }

            .group-header {
              display: flex;
              align-items: baseline;
              justify-content: space-between;
              gap: 12px;
              margin-bottom: 12px;
            }

            .group-header h2 {
              margin: 0;
              font-size: 1.15rem;
            }

            .group-header .count {
              color: var(--muted);
              font-size: 0.9rem;
            }

            .empty {
              padding: 26px;
              border: 1px dashed rgba(95, 71, 46, 0.28);
              border-radius: 20px;
              color: var(--muted);
              text-align: center;
              background: rgba(255, 250, 242, 0.72);
            }

            .danger {
              color: var(--error);
            }

            .success {
              color: var(--ok);
            }

            @media (max-width: 980px) {
              .layout {
                grid-template-columns: 1fr;
              }
            }
          </style>
        </head>
        <body>
          <main class="shell">
            <section class="hero">
              <h1>AInformer Feedboard</h1>
              <p>
                Browse all configured sources from one page. The dashboard reads the configured
                source list, fetches current records, and groups them by source so you can verify
                coverage quickly.
              </p>
              <div class="toolbar">
                <div class="control">
                  <label for="limit">Records Per Source</label>
                  <input id="limit" type="number" min="1" max="100" value="8" />
                </div>
                <div class="control">
                  <label for="search">Filter Records</label>
                  <input id="search" type="search" placeholder="Search title, source, author, tag" />
                </div>
                <fieldset class="control">
                  <legend>Content Mode</legend>
                  <div class="control-row">
                    <input id="include-full-text" type="checkbox" />
                    <label for="include-full-text" style="margin: 0; text-transform: none; letter-spacing: 0;">Include full text</label>
                  </div>
                </fieldset>
                <div class="control">
                  <label>&nbsp;</label>
                  <button id="refresh" class="button" type="button">Refresh All Sources</button>
                </div>
              </div>
              <div class="stats">
                <article class="stat">
                  <div class="label">Sources</div>
                  <div class="value" id="stat-sources">0</div>
                </article>
                <article class="stat">
                  <div class="label">Records</div>
                  <div class="value" id="stat-records">0</div>
                </article>
                <article class="stat">
                  <div class="label">Deduped</div>
                  <div class="value" id="stat-deduped">0</div>
                </article>
                <article class="stat">
                  <div class="label">Errors</div>
                  <div class="value" id="stat-errors">0</div>
                </article>
              </div>
              <div id="status-line" class="status-line">Ready.</div>
            </section>

            <section class="layout">
              <aside class="panel">
                <h2>Configured Sources</h2>
                <div id="source-list" class="source-list"></div>
              </aside>
              <section class="panel">
                <h2>Fetched Records</h2>
                <div id="errors-root"></div>
                <div id="records-root"></div>
              </section>
            </section>
          </main>

          <script>
            const state = {
              sources: [],
              result: { records: [], errors: [], total_records: 0, deduped_records: 0 },
              loading: false,
              lastLoadedAt: null,
            };

            const nodes = {
              limit: document.getElementById("limit"),
              search: document.getElementById("search"),
              includeFullText: document.getElementById("include-full-text"),
              refresh: document.getElementById("refresh"),
              status: document.getElementById("status-line"),
              sourceList: document.getElementById("source-list"),
              errorsRoot: document.getElementById("errors-root"),
              recordsRoot: document.getElementById("records-root"),
              statSources: document.getElementById("stat-sources"),
              statRecords: document.getElementById("stat-records"),
              statDeduped: document.getElementById("stat-deduped"),
              statErrors: document.getElementById("stat-errors"),
            };

            function escapeHtml(value) {
              return String(value)
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#39;");
            }

            function formatDate(value) {
              if (!value) {
                return "Unknown date";
              }
              const date = new Date(value);
              if (Number.isNaN(date.valueOf())) {
                return value;
              }
              return new Intl.DateTimeFormat(undefined, {
                year: "numeric",
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
              }).format(date);
            }

            function normalizeWhitespace(value) {
              return String(value || "")
                .replace(/\r/g, "")
                .replace(/[ \t]+\n/g, "\n")
                .replace(/\n[ \t]+/g, "\n")
                .replace(/[ \t]{2,}/g, " ")
                .replace(/\n{3,}/g, "\n\n")
                .trim();
            }

            function looksLikeHtml(value) {
              return /<\/?[a-z][\s\S]*>/i.test(String(value || ""));
            }

            function htmlToText(value) {
              const normalizedHtml = String(value || "")
                .replace(/<br\s*\/?\s*>/gi, "\n")
                .replace(/<\/(p|div|article|section|li|ul|ol|h1|h2|h3|h4|h5|h6|blockquote)>/gi, "\n\n");
              const container = document.createElement("div");
              container.innerHTML = normalizedHtml;
              return normalizeWhitespace(container.textContent || "");
            }

            function readableText(value) {
              if (!value) {
                return "";
              }
              return looksLikeHtml(value) ? htmlToText(value) : normalizeWhitespace(value);
            }

            function previewText(record) {
              const candidates = [
                record.content_text,
                record.excerpt,
                record.content_html,
              ];
              for (const candidate of candidates) {
                const text = readableText(candidate);
                if (text) {
                  return text;
                }
              }
              return "";
            }

            function matchesSearch(record, sourceName, query) {
              if (!query) {
                return true;
              }
              const haystack = [
                record.title,
                sourceName,
                previewText(record),
                ...(record.authors || []),
                ...(record.tags || []),
              ]
                .join(" ")
                .toLowerCase();
              return haystack.includes(query);
            }

            function renderSourceList(groupedRecords) {
              const errorsBySource = new Map(state.result.errors.map((error) => [error.source_id, error]));
              const markup = state.sources.map((source) => {
                const records = groupedRecords.get(source.id) || [];
                const error = errorsBySource.get(source.id);
                const emptyClass = records.length === 0 ? " is-empty" : "";
                const statusChip = error
                  ? `<span class="chip danger">${escapeHtml(error.code)}</span>`
                  : `<span class="chip success">${records.length} records</span>`;
                return `
                  <article class="source-card${emptyClass}">
                    <h3>${escapeHtml(source.name)}</h3>
                    <div class="source-name">${escapeHtml(source.id)}</div>
                    <div class="meta">
                      <span class="chip">${escapeHtml(source.selected_method)}</span>
                      ${statusChip}
                    </div>
                  </article>
                `;
              }).join("");

              nodes.sourceList.innerHTML = markup || '<div class="empty">No sources configured.</div>';
            }

            function renderErrors() {
              if (!state.result.errors.length) {
                nodes.errorsRoot.innerHTML = "";
                return;
              }

              const markup = state.result.errors.map((error) => `
                <article class="error-card">
                  <h3>${escapeHtml(error.source_id)}</h3>
                  <p class="excerpt danger">${escapeHtml(error.message)}</p>
                </article>
              `).join("");

              nodes.errorsRoot.innerHTML = `
                <section class="group">
                  <div class="group-header">
                    <h2>Fetch Errors</h2>
                    <div class="count">${state.result.errors.length}</div>
                  </div>
                  <div class="error-list">${markup}</div>
                </section>
              `;
            }

            function renderRecords() {
              const sourceMap = new Map(state.sources.map((source) => [source.id, source]));
              const groupedRecords = new Map();

              for (const record of state.result.records) {
                const sourceRecords = groupedRecords.get(record.source_id) || [];
                sourceRecords.push(record);
                groupedRecords.set(record.source_id, sourceRecords);
              }

              renderSourceList(groupedRecords);
              renderErrors();

              const query = nodes.search.value.trim().toLowerCase();
              const groups = state.sources.map((source) => {
                const records = (groupedRecords.get(source.id) || []).filter((record) =>
                  matchesSearch(record, source.name, query)
                );
                return { source, records };
              }).filter((group) => group.records.length > 0 || !query);

              const markup = groups.map(({ source, records }) => {
                const body = records.length
                  ? records.map((record) => {
                      const contentPreview = previewText(record);
                      const authors = (record.authors || []).slice(0, 4);
                      const tags = (record.tags || []).slice(0, 6);
                      return `
                        <article class="record-card">
                          <h3><a href="${escapeHtml(record.url)}" target="_blank" rel="noreferrer">${escapeHtml(record.title)}</a></h3>
                          <div class="meta">
                            <span class="chip">${escapeHtml(formatDate(record.published_at))}</span>
                            <span class="chip">${escapeHtml(record.acquisition_method)}</span>
                            ${record.content_complete ? '<span class="chip">full text</span>' : ""}
                            ${authors.map((author) => `<span class="chip">${escapeHtml(author)}</span>`).join("")}
                            ${tags.map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}
                          </div>
                          ${contentPreview ? `<p class="excerpt">${escapeHtml(contentPreview)}</p>` : ""}
                        </article>
                      `;
                    }).join("")
                  : '<div class="empty">No records matched the current filter.</div>';

                return `
                  <section class="group">
                    <div class="group-header">
                      <h2>${escapeHtml(source.name)}</h2>
                      <div class="count">${records.length} shown</div>
                    </div>
                    <div class="record-list">${body}</div>
                  </section>
                `;
              }).join("");

              nodes.recordsRoot.innerHTML = markup || '<div class="empty">No records matched the current filter.</div>';
            }

            function updateStats() {
              nodes.statSources.textContent = String(state.sources.length);
              nodes.statRecords.textContent = String(state.result.total_records || 0);
              nodes.statDeduped.textContent = String(state.result.deduped_records || 0);
              nodes.statErrors.textContent = String(state.result.errors.length || 0);
            }

            function setStatus(message, tone = "") {
              nodes.status.className = "status-line" + (tone ? ` ${tone}` : "");
              nodes.status.textContent = message;
            }

            async function loadDashboard() {
              if (state.loading) {
                return;
              }

              state.loading = true;
              nodes.refresh.disabled = true;
              setStatus("Loading configured sources...");

              try {
                const sourcesResponse = await fetch("/v1/sources");
                if (!sourcesResponse.ok) {
                  throw new Error(`Unable to list sources: ${sourcesResponse.status}`);
                }
                state.sources = await sourcesResponse.json();

                setStatus(`Fetching ${state.sources.length} sources...`);
                const payload = {
                  source_ids: state.sources.map((source) => source.id),
                  limit: Number(nodes.limit.value || 8),
                  include_full_text: nodes.includeFullText.checked,
                };

                const fetchResponse = await fetch("/v1/fetch", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload),
                });
                const result = await fetchResponse.json();
                state.result = result;
                state.lastLoadedAt = new Date();

                updateStats();
                renderRecords();

                const loadedAt = new Intl.DateTimeFormat(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(state.lastLoadedAt);

                const statusText = fetchResponse.ok
                  ? `Loaded ${state.result.total_records} records across ${state.sources.length} sources at ${loadedAt}.`
                  : `Loaded with ${state.result.errors.length} errors at ${loadedAt}.`;
                setStatus(statusText, fetchResponse.ok ? "success" : "danger");
              } catch (error) {
                state.result = { records: [], errors: [], total_records: 0, deduped_records: 0 };
                updateStats();
                renderRecords();
                setStatus(error instanceof Error ? error.message : "Unknown dashboard error.", "danger");
              } finally {
                state.loading = false;
                nodes.refresh.disabled = false;
              }
            }

            nodes.refresh.addEventListener("click", loadDashboard);
            nodes.search.addEventListener("input", renderRecords);
            nodes.limit.addEventListener("change", loadDashboard);
            nodes.includeFullText.addEventListener("change", loadDashboard);

            loadDashboard();
          </script>
        </body>
        </html>
        """
    )
