/**
 * Rich interactive tables + insight card for Marie classic UI.
 */
(function (global) {
    "use strict";

    function escapeHtml(text) {
        return String(text ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatNumber(value) {
        const num = Number(value);
        if (Number.isNaN(num)) {
            return String(value ?? "");
        }
        if (Number.isInteger(num)) {
            return num.toLocaleString();
        }
        return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    function columnMetaMap(item) {
        const map = {};
        (item.columns_meta || []).forEach((col) => {
            map[col.key] = col;
        });
        return map;
    }

    function formatCellValue(key, raw, meta) {
        const kind = (meta && meta.kind) || "text";
        const text = raw == null ? "" : String(raw);
        if (!text) {
            return "";
        }
        if (kind === "doi") {
            const doi = text.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "");
            const href = doi.startsWith("http") ? doi : `https://doi.org/${doi}`;
            return `<span class="marie-cell-link"><a href="${escapeHtml(href)}" target="_blank" rel="noopener">${escapeHtml(doi)}</a></span>`;
        }
        if (kind === "badge") {
            const cls = key.toLowerCase() === "refcode" ? "marie-cell-badge refcode" : "marie-cell-badge";
            return `<span class="${cls}">${escapeHtml(text)}</span>`;
        }
        if (kind === "numeric") {
            return `<span class="marie-cell-num">${escapeHtml(formatNumber(text))}</span>`;
        }
        if (kind === "longtext") {
            return `<span class="marie-cell-mono" title="${escapeHtml(text)}">${escapeHtml(text)}</span>`;
        }
        return escapeHtml(text);
    }

    function renderInsightCard(narrative, parentElem) {
        if (!narrative || !String(narrative).trim()) {
            return null;
        }
        const card = document.createElement("div");
        card.className = "marie-insight-card";
        card.innerHTML = `
            <h5>Interpretation</h5>
            <div class="insight-body"></div>
        `;
        const body = card.querySelector(".insight-body");
        if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
            marked.setOptions({ breaks: true, gfm: true });
            body.innerHTML = DOMPurify.sanitize(marked.parse(String(narrative)));
        } else {
            body.textContent = String(narrative);
        }
        parentElem.appendChild(card);
        return card;
    }

    function exportCsv(tableId, filename) {
        const table = document.getElementById(tableId);
        if (!table) {
            return;
        }
        const rows = [];
        table.querySelectorAll("tr").forEach((tr) => {
            const cells = [];
            tr.querySelectorAll("th, td").forEach((td) => {
                cells.push(`"${String(td.textContent || "").replace(/"/g, '""')}"`);
            });
            if (cells.length) {
                rows.push(cells.join(","));
            }
        });
        const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename || "marie-results.csv";
        link.click();
        URL.revokeObjectURL(link.href);
    }

    function renderBarChart(containerId, item) {
        const chart = item.chart;
        const rows = item.bindings || item.data || [];
        if (!chart || chart.type !== "bar" || typeof Plotly === "undefined" || !rows.length) {
            return;
        }
        const sorted = rows
            .slice()
            .sort((a, b) => Number(b[chart.y_key] || 0) - Number(a[chart.y_key] || 0))
            .slice(0, chart.top_n || 10);
        const x = sorted.map((r) => String(r[chart.x_key] || "").slice(0, 24));
        const y = sorted.map((r) => Number(r[chart.y_key] || 0));
        Plotly.newPlot(
            containerId,
            [{ type: "bar", x, y, marker: { color: "#3b82f6" } }],
            {
                margin: { t: 24, r: 16, b: 80, l: 56 },
                xaxis: { title: chart.x_key, tickangle: -35 },
                yaxis: { title: chart.y_label || chart.y_key },
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
            },
            { displayModeBar: false, responsive: true }
        );
    }

    function renderRichDataTable(item, parentElem, id) {
        const vars = item.vars || item.columns || [];
        const bindings = item.bindings || item.data || [];
        const metaMap = columnMetaMap(item);
        const tableId = `${id}-table`;
        const chartId = `${id}-chart`;

        const card = document.createElement("div");
        card.className = "marie-rich-table-card";
        card.id = id;

        const title = item.title || "Results";
        const rowCount = item.row_count != null ? item.row_count : bindings.length;

        card.innerHTML = `
            <div class="marie-rich-table-header">
                <div>
                    <h6>${escapeHtml(title)}</h6>
                    <span class="marie-row-badge">${Number(rowCount).toLocaleString()} rows</span>
                </div>
                <div class="marie-rich-table-toolbar">
                    <button type="button" class="marie-btn-ghost marie-export-csv">Export CSV</button>
                    <button type="button" class="marie-btn-ghost marie-toggle-iri">Hide IRIs</button>
                </div>
            </div>
            ${item.chart ? `<div class="marie-chart-wrap" id="${chartId}"></div>` : ""}
            <div class="marie-rich-table-body">
                <div class="table-responsive">
                    <table id="${tableId}" class="table table-sm table-hover table-striped" style="width:100%"></table>
                </div>
            </div>
        `;
        parentElem.appendChild(card);

        const thead = vars.map((key) => {
            const meta = metaMap[key] || {};
            const label = meta.label || key;
            const description = meta.description || "";
            const kgHint = meta.key && meta.key !== label ? meta.key : key;
            const title = description
                ? `${description} (KG field: ${kgHint})`
                : `KG field: ${kgHint}`;
            return `<th title="${escapeHtml(title)}">
                <span class="marie-th-label">${escapeHtml(label)}</span>
                <span class="marie-th-kg">${escapeHtml(kgHint)}</span>
            </th>`;
        }).join("");
        const tbody = bindings.map((row, idx) => {
            const cells = vars.map((key) => {
                const formatted = formatCellValue(key, row[key], metaMap[key]);
                return `<td data-order="${escapeHtml(row[key] ?? "")}">${formatted}</td>`;
            }).join("");
            return `<tr><td>${idx + 1}</td>${cells}</tr>`;
        }).join("");

        const table = document.getElementById(tableId);
        table.innerHTML = `<thead><tr><th>#</th>${thead}</tr></thead><tbody>${tbody}</tbody>`;

        card.querySelector(".marie-export-csv").addEventListener("click", () => {
            exportCsv(tableId, `${id}.csv`);
        });

        if (item.chart) {
            setTimeout(() => renderBarChart(chartId, item), 0);
        }

        setTimeout(() => {
            if (typeof DataTable === "undefined") {
                return;
            }
            const dt = new DataTable(`#${tableId}`, {
                retrieve: true,
                scrollX: true,
                pageLength: 10,
                lengthMenu: [10, 25, 50, 100],
                order: [],
                dom: '<"row mb-2"<"col-sm-6"l><"col-sm-6"f>>rtip',
            });

            const toggleBtn = card.querySelector(".marie-toggle-iri");
            function toggleIri() {
                const rowNum = dt.rows().count();
                if (rowNum === 0) {
                    return;
                }
                const showing = toggleBtn.textContent === "Hide IRIs";
                const rowData = dt.row(0).data();
                const iriCols = rowData.reduce((arr, val, idx) => {
                    if (typeof val === "string" && TWA_ABOX_IRI_PREFIXES.some((p) => val.startsWith(p))) {
                        arr.push(idx);
                    }
                    return arr;
                }, []);
                iriCols.forEach((colIdx) => {
                    dt.column(colIdx).visible(!showing);
                });
                toggleBtn.textContent = showing ? "Show IRIs" : "Hide IRIs";
            }
            toggleIri();
            toggleBtn.addEventListener("click", toggleIri);
        }, 0);

        return card;
    }

    global.MarieRichTable = {
        renderInsightCard,
        renderRichDataTable,
    };
})(window);
