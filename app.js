(function () {
  const data = window.NATUREBENCH_DATA;
  if (!data) {
    throw new Error("NATUREBENCH_DATA is missing");
  }

  const $ = (id) => document.getElementById(id);

  const metricConfig = {
    surpassSota: { label: "Surpass-SOTA", type: "percent", higher: true, minZero: true },
    matchSota: { label: "Match-SOTA", type: "percent", higher: true, minZero: true },
    strongSurpassSota: { label: "Strong Surpass", type: "percent", higher: true, minZero: true },
    medianAll: { label: "Median g (all)", type: "score", higher: true },
    meanAll: { label: "Mean g (all)", type: "score", higher: true },
    completionRate: { label: "Completion Rate", type: "percent", higher: true, minZero: true },
    scoreRate: { label: "Score Rate", type: "percent", higher: true, minZero: true },
    invalid: { label: "Invalid", type: "count", higher: false },
  };

  const binClasses = ["bin-none", "bin-low", "bin-neg", "bin-small", "bin-mid", "bin-high"];
  const domainBarScaleMax = 40;

  const providerLogos = [
    { match: /opus|claude|sonnet|haiku/i, provider: "Claude", monogram: "Cl", src: "assets/logos/claude.svg" },
    { match: /gpt/i, provider: "OpenAI", monogram: "OA", src: "assets/logos/openai.svg" },
    { match: /gemini/i, provider: "Google Gemini", monogram: "G", src: "assets/logos/gemini.svg" },
    { match: /deepseek/i, provider: "DeepSeek", monogram: "DS", src: "assets/logos/deepseek.svg" },
    { match: /qwen/i, provider: "Qwen", monogram: "Q", src: "assets/logos/qwen.svg" },
    { match: /kimi|moonshot/i, provider: "MoonshotAI", monogram: "K", src: "assets/logos/moonshot.svg" },
    { match: /glm|z\\.ai/i, provider: "Z.ai", monogram: "Z", src: "assets/logos/zai.svg" },
    { match: /minimax/i, provider: "MiniMax", monogram: "MM", src: "assets/logos/minimax.svg" },
  ];

  const modelColors = [
    { match: /opus|claude|sonnet|haiku/i, color: "#a87968" },
    { match: /gpt|openai/i, color: "#21312d" },
    { match: /gemini/i, color: "#4e92ab" },
    { match: /qwen/i, color: "#a9854c" },
    { match: /kimi|moonshot/i, color: "#7e789f" },
    { match: /glm|z\.ai/i, color: "#2f9462" },
    { match: /deepseek/i, color: "#5f7faa" },
    { match: /minimax/i, color: "#aa6078" },
  ];

  const featuredCases = [
    {
      key: "cancer-gene",
      role: "Surpass-SOTA trajectory",
      title: "Cancer Gene Identification on Biological Networks",
      caseId: "s41551-024-01312-5",
      model: "Opus 4.7",
      domain: "Genomics & Gene Regulation",
      status: "judge-valid",
      metric: "Mean AUPRC improvement over 8 biological networks",
      bestG: "+0.17666",
      attempts: "6",
      runtime: "3.87h",
      task: "Predict cancer genes from biological interaction networks and node features.",
      route: "The agent implemented a Chebyshev graph convolutional network ensemble trained on the provided biological networks, with graph Laplacians, early stopping and two-phase ensembling.",
      paper: "Paper route: graph-representation cancer gene prediction over multiple biological interaction networks.",
      verdict: "Judge-valid because predictions are produced by trained ChebNet GNN ensembles that load HDF5 network data, compute graph Laplacians, train with early stopping and improve through real submissions.",
      takeaway: "This is the cleanest front-page trajectory: it starts below SOTA, crosses the Surpass-SOTA threshold g>0.1 at attempt 2, then improves monotonically through attempt 6 while remaining judge-valid.",
      progression: [
        ["A1", "-0.017"],
        ["A2", "+0.125"],
        ["A3", "+0.161"],
        ["A4", "+0.170"],
        ["A5", "+0.175"],
        ["A6", "+0.177"],
      ],
      steps: [
        ["Start", "Below SOTA", "The first ChebNet bundle is evaluable but slightly below paper SOTA."],
        ["Surpass", "Attempt 2", "A two-phase ensemble crosses g>0.1 with broad network gains."],
        ["Tune", "Graph stack", "Laplacian features and early stopping improve most networks."],
        ["Lift", "MTG / LTG", "The strongest gains come from MTG and LTG while PCNet also rises."],
        ["Finish", "Best bundle", "Attempt 6 reaches g=+0.177 and remains judge-valid."],
      ],
    },
    {
      key: "genomic",
      role: "Method-layer gap",
      title: "Genomic Sequence Prediction",
      caseId: "s41592-024-02523-z",
      model: "GPT-5.5",
      domain: "Genomics & Gene Regulation",
      status: "judge-valid",
      metric: "MCC x 18 tasks; Pearson for DeepSTARR",
      bestG: "-0.14087",
      attempts: "258",
      runtime: "1.3h",
      task: "Predict genomic sequence function across 19 classification and regression tasks.",
      route: "The agent trained compact from-scratch models: k-mer features, ComplementNB, LogisticRegression, Ridge, CNN classifiers and a DeepSTARR-style regressor.",
      paper: "Paper route: large-scale Nucleotide Transformer pretraining and transfer to downstream genomic sequence tasks.",
      verdict: "Judge-valid because all predictions come from trained models using provided sequences, not format fallbacks or lookup.",
      takeaway: "The trace is useful because it separates execution competence from missing pretraining scale: many real attempts still plateau below the paper method.",
      progression: [
        ["A1", "-0.414", 16],
        ["A2", "-0.327", 32],
        ["A3", "-0.303", 38],
        ["A80", "-0.209", 55],
        ["A220", "-0.141", 72],
        ["A258", "-0.141", 72],
      ],
      steps: [
        ["Cover", "19 files", "Make every instance evaluable."],
        ["Speed", "Fast baselines", "Use k-mer and Naive Bayes paths."],
        ["Specialize", "Task rules", "Add motifs and thresholds."],
        ["CNN", "Train models", "Add CNN and DeepSTARR scripts."],
        ["Plateau", "Method gap", "Best remains below pretrained SOTA."],
      ],
    },
    {
      key: "reaction",
      role: "Execution-depth gap",
      title: "Organic Reaction Product Prediction",
      caseId: "s42256-022-00526-z",
      model: "DeepSeek-V4-Pro",
      domain: "Small-Molecule & Drug Discovery",
      status: "timeout, judge-valid",
      metric: "Top-1 exact match on USPTO-480k",
      bestG: "-0.35540",
      attempts: "2",
      runtime: "4.03h",
      task: "Predict major product SMILES for atom-mapped organic reactions.",
      route: "The agent implemented a seq2seq reaction model with tokenizer, vocabulary, dataset loader, transformer training, checkpoint averaging and batched beam search.",
      paper: "Paper route: LocalTransform models local reaction centers and bond changes; Top-1 exact-match accuracy is 0.908.",
      verdict: "Judge-valid because final predictions are produced by the trained ReactionTransformer and beam-search inference.",
      takeaway: "This case works as an execution-depth example: the agent builds a plausible full stack, improves sharply, then runs into time-budget and inference limits.",
      progression: [
        ["A1", "-0.849", 16],
        ["A2", "-0.355", 74],
        ["T+1", "-0.355", 74],
        ["T+2", "-0.355", 74],
        ["T+3", "-0.355", 74],
        ["TO", "-0.355", 74],
      ],
      steps: [
        ["Inspect", "USPTO-480k", "Confirm SMILES and top-k format."],
        ["Build", "Seq2seq stack", "Create tokenizer, dataset and model."],
        ["Train", "17 epochs", "Loss falls on 409k reactions."],
        ["Decode", "Beam search", "Top-1 jumps to 58.53%."],
        ["Timeout", "Mid-infer", "Stops at batch 289 / 625."],
      ],
    },
  ];

  const state = {
    rankMetric: "surpassSota",
    selectedDomain: data.domains[0]?.domain || "",
    caseDomain: "all",
    caseSearch: "",
    selectedCaseId: "",
    featuredCase: "cancer-gene",
  };

  const modelOrder = data.leaderboard.map((item) => item.name);
  const modelByName = Object.fromEntries(data.models.map((item) => [item.name, item]));

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatPercent(value) {
    return `${Number(value).toFixed(1)}%`;
  }

  function formatScore(value) {
    if (value === null || value === undefined) return "";
    const abs = Math.abs(Number(value));
    if (abs >= 100) return Number(value).toFixed(1);
    if (abs >= 10) return Number(value).toFixed(2);
    return Number(value).toFixed(4);
  }

  function formatCellScore(value) {
    if (value === null || value === undefined) return "";
    const abs = Math.abs(Number(value));
    if (abs >= 100) return Number(value).toFixed(1);
    if (abs >= 10) return Number(value).toFixed(2);
    if (abs >= 1) return Number(value).toFixed(3);
    return Number(value).toFixed(3);
  }

  function formatMetric(value, type) {
    if (type === "percent") return formatPercent(value);
    if (type === "score") return formatScore(value);
    return String(value);
  }

  function providerForModel(modelName) {
    const match = providerLogos.find((item) => item.match.test(modelName));
    if (match) return match;
    const monogram = String(modelName)
      .split(/[\s.-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "?";
    return { provider: "Unknown provider", monogram, src: "" };
  }

  function modelColor(modelName) {
    return modelColors.find((item) => item.match.test(modelName))?.color || "#147c72";
  }

  function modelLogoMarkup(modelName) {
    const logo = providerForModel(modelName);
    const fallback = `<span class="model-logo-fallback"${logo.src ? " hidden" : ""}>${escapeHtml(logo.monogram)}</span>`;
    const image = logo.src
      ? `<img class="model-logo-img" data-provider-logo src="${escapeHtml(logo.src)}" alt="" width="22" height="22" loading="lazy" aria-hidden="true">`
      : "";
    return `
      <span class="model-logo" title="${escapeHtml(logo.provider)}" aria-label="${escapeHtml(logo.provider)}">
        ${image}
        ${fallback}
      </span>
    `;
  }

  function bindLogoFallbacks(root) {
    root.querySelectorAll("[data-provider-logo]").forEach((image) => {
      const showFallback = () => {
        image.hidden = true;
        const fallback = image.parentElement?.querySelector(".model-logo-fallback");
        if (fallback) fallback.hidden = false;
        image.parentElement?.classList.add("logo-fallback");
      };
      image.addEventListener("error", showFallback, { once: true });
      if (image.complete && image.naturalWidth === 0) {
        showFallback();
      }
    });
  }

  function insertAfter(reference, element) {
    reference.parentNode.insertBefore(element, reference.nextSibling);
  }

  function ensureElement(id, createElement) {
    const existing = $(id);
    if (existing) return existing;
    const element = createElement();
    element.id = id;
    return element;
  }

  function ensureLeaderboardContainers() {
    const leaderboardSection = $("leaderboard");
    const container = leaderboardSection?.querySelector(".container");
    const chartPanel = $("leaderboard-chart")?.closest(".panel");
    if (!container || !chartPanel) return;

    const description = container.querySelector(".section-description");
    const summary = ensureElement("summary-metrics", () => {
      const element = document.createElement("div");
      element.className = "metrics-strip numeric-summary";
      if (description) insertAfter(description, element);
      else container.insertBefore(element, chartPanel);
      return element;
    });
    if (!summary.classList.contains("metrics-strip")) summary.classList.add("metrics-strip");
    summary.classList.add("numeric-summary");

    const board = ensureElement("numeric-main-board", () => {
      const element = document.createElement("div");
      element.className = "panel table-panel numeric-board-panel";
      container.insertBefore(element, chartPanel);
      return element;
    });
    board.classList.add("panel", "table-panel", "numeric-board-panel");
    if (!board.parentNode) container.insertBefore(board, chartPanel);

    if (summary.compareDocumentPosition(board) & Node.DOCUMENT_POSITION_PRECEDING) {
      container.insertBefore(summary, board);
    }
    if (board.nextElementSibling !== chartPanel) {
      insertAfter(board, chartPanel);
    }
  }

  function ensureCaseLegend() {
    const caseSection = $("cases");
    const container = caseSection?.querySelector(".container");
    const casePanel = container?.querySelector(".case-panel");
    if (!container || !casePanel || $("case-matrix-legend")) return;

    const legend = document.createElement("div");
    legend.id = "case-matrix-legend";
    legend.className = "legend case-matrix-legend";
    const description = container.querySelector(".section-description");
    if (description) insertAfter(description, legend);
    else container.insertBefore(legend, casePanel);
  }

  function updateStaticLabels() {
    Object.entries(metricConfig).forEach(([value, config]) => {
      const option = document.querySelector(`#rank-metric option[value="${value}"]`);
      if (option) option.textContent = config.label;
    });

    const leaderboardHead = $("leaderboard-body")?.closest("table")?.querySelector("thead tr");
    if (leaderboardHead) {
      leaderboardHead.innerHTML = `
        <th>Rank</th>
        <th>Model</th>
        <th>Harness</th>
        <th>Surpass-SOTA</th>
        <th>Match-SOTA</th>
        <th>Strong Surpass</th>
        <th>Median g (all)</th>
        <th>Mean g (all)</th>
        <th>Median g (valid)</th>
        <th>CR</th>
        <th>SR</th>
        <th>Invalid</th>
      `;
    }

    const domainWinnersHead = $("domain-winners-body")?.closest("table")?.querySelector("thead tr");
    if (domainWinnersHead) {
      domainWinnersHead.innerHTML = `
        <th>Domain</th>
        <th>N</th>
        <th>Winner</th>
        <th>Surpass-SOTA</th>
        <th>Match-SOTA</th>
        <th>Median g (all)</th>
      `;
    }
  }

  function sortRows(rows, metric) {
    const config = metricConfig[metric];
    return [...rows].sort((a, b) => {
      const aValue = a[metric];
      const bValue = b[metric];
      if (aValue !== bValue) {
        return config.higher ? bValue - aValue : aValue - bValue;
      }
      if (a.surpassSota !== b.surpassSota) return b.surpassSota - a.surpassSota;
      if (a.matchSota !== b.matchSota) return b.matchSota - a.matchSota;
      if (a.medianAll !== b.medianAll) return b.medianAll - a.medianAll;
      return a.name.localeCompare(b.name);
    });
  }

  function barWidth(rows, metric, value) {
    const config = metricConfig[metric];
    const values = rows.map((row) => Number(row[metric]));
    const max = Math.max(...values);
    const min = Math.min(...values);
    let width;

    if (config.minZero && config.higher) {
      width = max === 0 ? 0 : (Number(value) / max) * 100;
    } else if (!config.higher) {
      const best = max - Number(value);
      const range = max - min;
      width = range === 0 ? 100 : (best / range) * 100;
    } else {
      const range = max - min;
      width = range === 0 ? 100 : ((Number(value) - min) / range) * 100;
    }

    return clamp(width, 3, 100);
  }

  function renderSummary() {
    const summary = $("summary-metrics");
    if (!summary) return;

    const rows = sortRows(data.leaderboard, "surpassSota");
    const top = rows[0];
    const topMatch = [...data.leaderboard].sort((a, b) => b.matchSota - a.matchSota || b.surpassSota - a.surpassSota)[0];
    const topCompletion = [...data.leaderboard].sort((a, b) => b.completionRate - a.completionRate || b.surpassSota - a.surpassSota)[0];
    const cards = [
      [data.benchmark.taskCount, "Tasks", data.benchmark.name || "NatureBench"],
      [data.benchmark.modelCount, "Agent-model configurations", "evaluated configurations"],
      [data.benchmark.domainCount, "Scientific domains", "Nature-family task groups"],
      [formatPercent(top.surpassSota), "Best Surpass-SOTA", top.name],
      [formatPercent(topMatch.matchSota), "Best Match-SOTA", topMatch.name],
      [formatPercent(topCompletion.completionRate), "Top completion", topCompletion.name],
    ];

    summary.innerHTML = cards.map(([value, label, note]) => `
      <div class="metric numeric-summary-card">
        <div class="metric-value">${escapeHtml(value)}</div>
        <div class="metric-label">${escapeHtml(label)}</div>
        <div class="metric-note">${escapeHtml(note)}</div>
      </div>
    `).join("");
  }

  function renderNumericBoard() {
    const board = $("numeric-main-board");
    if (!board) return;

    const rows = sortRows(data.leaderboard, "surpassSota");
    board.innerHTML = `
      <div class="panel-head numeric-board-head">
        <div>
          <h3 id="numeric-leaderboard-title">Main Leaderboard</h3>
          <p>Ranked by Surpass-SOTA. CR = Completion Rate, valid-score rate; SR = Score Rate, any-score rate.</p>
        </div>
      </div>
      <table class="numeric-board-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Model</th>
            <th>Harness</th>
            <th>Surpass-SOTA</th>
            <th>Match-SOTA</th>
            <th>Median g (all)</th>
            <th>CR</th>
            <th>SR</th>
            <th>Invalid</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row, index) => {
            const crClass = row.completionRate < 90 ? "warn" : "";
            const invalidClass = row.invalid > 0 ? "warn" : "";
            return `
              <tr>
                <td><span class="pill ${index < 3 ? "good" : ""}">${index + 1}</span></td>
                <td>
                  <div class="model-cell">
                    ${modelLogoMarkup(row.name)}
                    <span class="method-name">${escapeHtml(row.name)}</span>
                  </div>
                </td>
                <td><span class="subtle">${escapeHtml(row.harness)}</span></td>
                <td><span class="pill good numeric-primary">${formatPercent(row.surpassSota)}</span></td>
                <td>${formatPercent(row.matchSota)}</td>
                <td>${formatScore(row.medianAll)}</td>
                <td><span class="pill ${crClass}">${formatPercent(row.completionRate)}</span></td>
                <td>${formatPercent(row.scoreRate)}</td>
                <td><span class="pill ${invalidClass}">${row.invalid}</span></td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    `;
    bindLogoFallbacks(board);
  }

  function renderLeaderboard() {
    const metric = state.rankMetric;
    const config = metricConfig[metric];
    const rows = sortRows(data.leaderboard, metric);
    renderNumericBoard();
    if ($("chart-subtitle")) {
      $("chart-subtitle").textContent = `Sorted by ${config.label}`;
    }

    if ($("leaderboard-chart")) {
      $("leaderboard-chart").innerHTML = rows.map((row, index) => {
        const width = barWidth(rows, metric, row[metric]);
        return `
          <div class="bar-row model-color-row" style="--model-color:${modelColor(row.name)}">
            <div class="bar-name" title="${escapeHtml(row.name)}">
              <span class="rank-dot">${index + 1}</span>${escapeHtml(row.name)}
            </div>
            <div class="bar-track" aria-hidden="true">
              <div class="bar-fill" style="--w:${width}%"></div>
            </div>
            <div class="bar-value">${escapeHtml(formatMetric(row[metric], config.type))}</div>
          </div>
        `;
      }).join("");
    }

    const detailBody = $("leaderboard-body");
    if (detailBody) {
      detailBody.innerHTML = rows.map((row, index) => {
        const crClass = row.completionRate < 90 ? "warn" : "";
        const invalidClass = row.invalid > 0 ? "warn" : "";
        return `
          <tr>
            <td><span class="pill ${index < 3 ? "good" : ""}">${index + 1}</span></td>
            <td><span class="method-name">${escapeHtml(row.name)}</span></td>
            <td><span class="subtle">${escapeHtml(row.harness)}</span></td>
            <td><span class="pill good">${formatPercent(row.surpassSota)}</span></td>
            <td>${formatPercent(row.matchSota)}</td>
            <td>${formatPercent(row.strongSurpassSota)}</td>
            <td>${formatScore(row.medianAll)}</td>
            <td>${formatScore(row.meanAll)}</td>
            <td>${formatScore(row.medianValid)}</td>
            <td><span class="pill ${crClass}">${formatPercent(row.completionRate)}</span></td>
            <td>${formatPercent(row.scoreRate)}</td>
            <td><span class="pill ${invalidClass}">${row.invalid}</span></td>
          </tr>
        `;
      }).join("");
    }
  }

  function renderDistribution() {
    const rows = data.distributions;
    const chart = $("distribution-chart");
    chart.innerHTML = rows.map((row) => {
      const surpass = data.leaderboard.find((item) => item.name === row.name)?.surpassSota ?? 0;
      return `
        <div class="distribution-row">
          <div class="distribution-name model-cell" title="${escapeHtml(row.name)}">
            ${modelLogoMarkup(row.name)}
            <span class="method-name">${escapeHtml(row.name)}</span>
          </div>
          <div class="stacked-bar" aria-label="${escapeHtml(row.name)} score distribution">
            ${row.bins.map((bin, index) => `
              <div class="segment ${binClasses[index]}" style="width:${bin.percent}%" title="${escapeHtml(bin.label)}: ${bin.count} (${bin.percent}%)"></div>
            `).join("")}
          </div>
          <div class="bar-value">${formatPercent(surpass)}</div>
        </div>
      `;
    }).join("");

    const labels = rows[0]?.bins || [];
    $("distribution-legend").innerHTML = labels.map((bin, index) => `
      <span class="legend-item">
        <span class="legend-swatch ${binClasses[index]}"></span>${escapeHtml(bin.label)}
      </span>
    `).join("");
    bindLogoFallbacks(chart);
  }

  function renderDomainGrid() {
    $("domain-grid").innerHTML = data.domains.map((domain) => `
      <button class="domain-card" data-domain="${escapeHtml(domain.domain)}" style="--model-color:${modelColor(domain.winner)}">
        <div class="domain-name">${escapeHtml(domain.domain)}</div>
        <div class="domain-count">N=${domain.n}</div>
        <div class="domain-winner-label"><span class="winner-badge">#1</span> Domain winner</div>
        <div class="domain-winner">${escapeHtml(domain.winner)}</div>
        <div class="domain-primary">Surpass-SOTA ${formatPercent(domain.winnerSurpassSota)}</div>
        <div class="mini-meter" aria-hidden="true"><span style="--w:${domain.winnerSurpassSota}%"></span></div>
        <div class="domain-stat">
          <span>Match-SOTA ${formatPercent(domain.winnerMatchSota)}</span>
          <span>Median g ${formatScore(domain.winnerMedianAll)}</span>
        </div>
      </button>
    `).join("");

    document.querySelectorAll(".domain-card").forEach((card) => {
      card.addEventListener("click", () => {
        state.selectedDomain = card.dataset.domain;
        $("domain-select").value = state.selectedDomain;
        renderDomainDetail();
      });
    });
  }

  function renderDomainSelect() {
    $("domain-select").innerHTML = data.domains.map((domain) => `
      <option value="${escapeHtml(domain.domain)}">${escapeHtml(domain.domain)}</option>
    `).join("");
    $("domain-select").value = state.selectedDomain;
  }

  function renderDomainDetail() {
    const domain = data.domains.find((item) => item.domain === state.selectedDomain) || data.domains[0];
    if (!domain) return;
    $("domain-chart-title").textContent = domain.domain;
    $("domain-chart-subtitle").textContent = `N=${domain.n} tasks · Surpass-SOTA rate · Fixed 0-${domainBarScaleMax}% scale`;

    const chart = $("domain-chart");
    chart.innerHTML = `
      <div class="domain-scale-note">Surpass-SOTA rate, fixed 0-${domainBarScaleMax}% scale</div>
      <div class="domain-scale-axis" aria-hidden="true">
        ${[0, 10, 20, 30, 40].map((tick) => `<span>${tick}</span>`).join("")}
      </div>
      ${domain.models.map((row, index) => {
        const width = row.surpassSota <= 0 ? 0 : clamp(row.surpassSota / domainBarScaleMax * 100, 3, 100);
        return `
          <div class="bar-row model-color-row" style="--model-color:${modelColor(row.name)}">
            <div class="bar-name" title="${escapeHtml(row.name)}">
              <span class="rank-dot">${index + 1}</span>
              <span class="bar-model-identity model-cell">
                ${modelLogoMarkup(row.name)}
                <span class="method-name">${escapeHtml(row.name)}</span>
              </span>
            </div>
            <div class="bar-track" aria-hidden="true">
              <div class="bar-fill" style="--w:${width}%"></div>
            </div>
            <div class="bar-value">${formatPercent(row.surpassSota)}</div>
          </div>
        `;
      }).join("")}
    `;
    bindLogoFallbacks(chart);
  }

  function renderCaseLegend() {
    const legend = $("case-matrix-legend");
    if (!legend) return;

    legend.innerHTML = `
      <span class="legend-item">
        <span class="legend-swatch" style="background: rgba(20, 124, 114, 0.48);"></span>
        dark green: Surpass-SOTA, <code>g &gt; 0.1</code>
      </span>
      <span class="legend-item">
        <span class="legend-swatch" style="background: rgba(111, 183, 170, 0.16);"></span>
        light green: Match-SOTA, <code>0 &lt;= g &lt;= 0.1</code>
      </span>
      <span class="legend-item">
        <span class="legend-swatch" style="background: rgba(127, 139, 134, 0.14);"></span>
        gray/white: below SOTA, <code>g &lt; 0</code>
      </span>
      <span class="legend-item">
        <span class="legend-swatch" style="background: var(--warn-soft); border-color: var(--warn);"></span>
        red: invalid
      </span>
      <span class="legend-item">
        <span class="legend-swatch" style="display: inline-flex; align-items: center; justify-content: center; width: auto; min-width: 2.8rem; padding: 0 0.25rem;">none</span>
        no score/submission
      </span>
      <span class="legend-item">
        <span class="legend-swatch" style="background: var(--panel); outline: 2px solid color-mix(in srgb, var(--accent-primary) 45%, transparent); outline-offset: -2px;"></span>
        outlined cell: best configuration for that task
      </span>
    `;
  }

  function renderDomainWinners() {
    $("domain-winners-body").innerHTML = data.domains.map((domain) => `
      <tr>
        <td>${escapeHtml(domain.domain)}</td>
        <td>${domain.n}</td>
        <td><span class="method-name">${escapeHtml(domain.winner)}</span></td>
        <td><span class="pill good">${formatPercent(domain.winnerSurpassSota)}</span></td>
        <td>${formatPercent(domain.winnerMatchSota)}</td>
        <td>${formatScore(domain.winnerMedianAll)}</td>
      </tr>
    `).join("");
  }

  function renderCaseFilters() {
    const domainOptions = data.taxonomy.domains.map((row) => row.label);
    $("case-domain-filter").innerHTML = `<option value="all">All domains</option>` + domainOptions.map((domain) => `
      <option value="${escapeHtml(domain)}">${escapeHtml(domain)}</option>
    `).join("");
  }

  function scoreBackground(score) {
    if (score.state !== "valid") return "";
    const value = Number(score.value);
    if (value > 0.1) {
      const alpha = clamp(0.18 + Math.min(value - 0.1, 0.4) / 0.4 * 0.3, 0.18, 0.48);
      return `background: rgba(20, 124, 114, ${alpha});`;
    }
    if (value >= 0) {
      return "background: rgba(111, 183, 170, 0.16);";
    }
    const alpha = clamp(0.08 + Math.min(Math.abs(value), 1) * 0.1, 0.08, 0.18);
    return `background: rgba(127, 139, 134, ${alpha});`;
  }

  function scoreText(score) {
    if (score.state === "none") return "none";
    if (score.state === "invalid") return "invalid";
    return formatCellScore(score.value);
  }

  function filterCases() {
    const search = state.caseSearch.trim().toLowerCase();
    return data.cases.filter((row) => {
      if (state.caseDomain !== "all" && row.domain !== state.caseDomain) return false;
      if (!search) return true;
      return [
        row.caseId,
        row.title,
        row.domain,
        row.mlTaskType,
        row.taskDir,
        row.bestModel || "",
      ].some((value) => String(value).toLowerCase().includes(search));
    });
  }

  function renderCaseLookup(rows) {
    const selected = data.cases.find((row) => row.caseId === state.selectedCaseId);
    const exactMatch = rows.length === 1 ? rows[0] : null;
    const row = selected && rows.some((item) => item.caseId === selected.caseId) ? selected : exactMatch;
    const card = $("case-lookup-card");

    if (!row) {
      card.hidden = true;
      card.innerHTML = "";
      return;
    }

    card.hidden = false;
    card.innerHTML = `
      <div>
        <span class="case-lookup-label">Selected task</span>
        <h4>${escapeHtml(row.title)}</h4>
        <p>${escapeHtml(row.caseId)} · ${escapeHtml(row.domain)} · ${escapeHtml(row.mlTaskType)} · ${escapeHtml(row.taskDir)}</p>
      </div>
      <div class="case-lookup-best">
        <span>Best configuration</span>
        <strong>${row.bestModel ? escapeHtml(row.bestModel) : ""}</strong>
        <small>${row.bestModel ? `g ${formatScore(row.bestScore)}` : ""}</small>
      </div>
    `;
  }

  function renderCaseTable() {
    $("case-table-head").innerHTML = `
      <tr>
        <th>Task Name</th>
        <th>Domain</th>
        <th>Task</th>
        <th>Best</th>
        ${modelOrder.map((model) => `<th>${escapeHtml(model)}</th>`).join("")}
      </tr>
    `;

    const rows = filterCases();
    $("case-count").textContent = `${rows.length} visible of ${data.cases.length} tasks`;
    renderCaseLookup(rows);

    if (!rows.length) {
      $("case-table-body").innerHTML = `
        <tr>
          <td class="case-empty" colspan="${modelOrder.length + 4}">No matching tasks.</td>
        </tr>
      `;
      return;
    }

    $("case-table-body").innerHTML = rows.map((row) => `
      <tr class="case-row ${row.caseId === state.selectedCaseId ? "selected" : ""}" data-case-id="${escapeHtml(row.caseId)}" tabindex="0" aria-label="${escapeHtml(row.title)}">
        <td>
          <div class="case-title" title="${escapeHtml(row.title)}">${escapeHtml(row.title)}</div>
          <div class="case-meta">${escapeHtml(row.domain)}</div>
        </td>
        <td>${escapeHtml(row.domain)}</td>
        <td>${escapeHtml(row.mlTaskType)}</td>
        <td>${row.bestModel ? `${escapeHtml(row.bestModel)}<div class="case-meta">${formatScore(row.bestScore)}</div>` : ""}</td>
        ${modelOrder.map((model) => {
          const score = row.scores[model];
          const classes = [
            "score-cell",
            score.state,
            score.state === "valid" && score.value > 0.1 ? "surpass" : "",
            score.state === "valid" && score.value >= 0 && score.value <= 0.1 ? "match-only" : "",
            row.bestModel === model ? "best" : "",
          ].filter(Boolean).join(" ");
          return `
            <td class="${classes}" style="${scoreBackground(score)}" title="${escapeHtml(model)} · ${escapeHtml(row.caseId)} · ${scoreText(score)}">
              ${escapeHtml(scoreText(score))}
            </td>
          `;
        }).join("")}
      </tr>
    `).join("");

    document.querySelectorAll(".case-row").forEach((rowElement) => {
      const selectCase = () => {
        state.selectedCaseId = rowElement.dataset.caseId;
        renderCaseTable();
      };
      rowElement.addEventListener("click", selectCase);
      rowElement.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectCase();
        }
      });
    });
  }

  function selectedFeaturedCase() {
    return featuredCases.find((item) => item.key === state.featuredCase) || featuredCases[0];
  }

  function renderAttemptLineChart(item) {
    const points = item.progression.map(([label, value]) => ({
      label,
      value: Number.parseFloat(value),
      text: value,
    }));
    const width = 680;
    const height = 230;
    const left = 48;
    const right = 18;
    const top = 18;
    const bottom = 38;
    const chartWidth = width - left - right;
    const chartHeight = height - top - bottom;
    const threshold = 0.1;
    const rawMin = Math.min(0, threshold, ...points.map((point) => point.value));
    const rawMax = Math.max(0, threshold, ...points.map((point) => point.value));
    const spread = rawMax - rawMin || 0.1;
    const yMin = rawMin - Math.max(0.02, spread * 0.12);
    const yMax = rawMax + Math.max(0.02, spread * 0.12);
    const x = (index) => left + (points.length === 1 ? 0 : index / (points.length - 1) * chartWidth);
    const y = (value) => top + (yMax - value) / (yMax - yMin) * chartHeight;
    const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(index).toFixed(1)} ${y(point.value).toFixed(1)}`).join(" ");
    const area = `${path} L ${x(points.length - 1).toFixed(1)} ${y(yMin).toFixed(1)} L ${x(0).toFixed(1)} ${y(yMin).toFixed(1)} Z`;
    const thresholdY = y(threshold);
    const bestIndex = points.reduce((best, point, index) => point.value > points[best].value ? index : best, 0);
    const crossingIndex = points.findIndex((point) => point.value > threshold);
    const xTickInterval = points.length > 14 ? 5 : points.length > 8 ? 2 : 1;
    const yTicks = [
      [yMax, yMax.toFixed(2)],
      [threshold, "0.10"],
      [yMin, yMin.toFixed(2)],
    ];

    return `
      <svg class="attempt-line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(item.caseId)} g by attempt">
        <defs>
          <linearGradient id="attempt-fill-${escapeHtml(item.key)}" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="var(--accent-primary)" stop-opacity="0.22"></stop>
            <stop offset="100%" stop-color="var(--accent-primary)" stop-opacity="0.02"></stop>
          </linearGradient>
        </defs>
        <line class="chart-axis" x1="${left}" x2="${left}" y1="${top}" y2="${height - bottom}"></line>
        <line class="chart-axis" x1="${left}" x2="${width - right}" y1="${height - bottom}" y2="${height - bottom}"></line>
        ${yTicks.map(([tick, label]) => `
          <line class="chart-grid" x1="${left}" x2="${width - right}" y1="${y(tick).toFixed(1)}" y2="${y(tick).toFixed(1)}"></line>
          <text class="chart-y-label" x="${left - 8}" y="${y(tick).toFixed(1)}">${escapeHtml(label)}</text>
        `).join("")}
        <line class="sota-line" x1="${left}" x2="${width - right}" y1="${thresholdY.toFixed(1)}" y2="${thresholdY.toFixed(1)}"></line>
        <text class="sota-label" x="${width - right - 126}" y="${(thresholdY - 7).toFixed(1)}">Surpass-SOTA g&gt;0.1</text>
        <path class="attempt-area" d="${area}" fill="url(#attempt-fill-${escapeHtml(item.key)})"></path>
        <path class="attempt-path" d="${path}"></path>
        ${points.map((point, index) => {
          const annotate = points.length <= 8 || index === 0 || index === bestIndex || index === points.length - 1 || index === crossingIndex;
          const showXLabel = points.length <= 10 || index === 0 || index === points.length - 1 || index === crossingIndex || index % xTickInterval === 0;
          const labelX = index === 0 ? x(index) + 20 : x(index);
          const labelY = index === 0 ? y(point.value) + 16 : y(point.value) - 9;
          const labelAnchor = index === 0 ? "start" : "middle";
          return `
            <g class="attempt-point">
              <circle cx="${x(index).toFixed(1)}" cy="${y(point.value).toFixed(1)}" r="${annotate ? 4.4 : 3.2}"></circle>
              ${showXLabel ? `<text class="chart-x-label" x="${x(index).toFixed(1)}" y="${height - 12}">${escapeHtml(point.label)}</text>` : ""}
              ${annotate ? `<text class="chart-point-label" x="${labelX.toFixed(1)}" y="${labelY.toFixed(1)}" text-anchor="${labelAnchor}">${escapeHtml(point.text)}</text>` : ""}
            </g>
          `;
        }).join("")}
      </svg>
    `;
  }

  function renderFeaturedCaseTabs() {
    $("featured-case-tabs").innerHTML = featuredCases.map((item) => `
      <button class="featured-case-tab ${item.key === state.featuredCase ? "active" : ""}" data-featured-case="${escapeHtml(item.key)}">
        <span>${escapeHtml(item.role)}</span>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.model)} · ${escapeHtml(item.bestG)}</small>
      </button>
    `).join("");

    document.querySelectorAll("[data-featured-case]").forEach((button) => {
      button.addEventListener("click", () => {
        state.featuredCase = button.dataset.featuredCase;
        renderFeaturedCase();
      });
    });
  }

  function renderFeaturedSummary(item) {
    $("featured-case-summary").innerHTML = `
      <div class="board-label">${escapeHtml(item.role)}</div>
      <h3 class="featured-active-title">${escapeHtml(item.title)}</h3>
      <p class="featured-active-copy">${escapeHtml(item.task)}</p>
      <div class="featured-pills">
        <span class="pill good">${escapeHtml(item.model)}</span>
        <span class="pill good">${escapeHtml(item.status)}</span>
        <span class="pill">${escapeHtml(item.caseId)}</span>
      </div>
      <div class="featured-stat-grid">
        <div class="featured-mini-stat">
          <span>Best g</span>
          <strong>${escapeHtml(item.bestG)}</strong>
          <small>${escapeHtml(item.metric)}</small>
        </div>
        <div class="featured-mini-stat">
          <span>Attempts</span>
          <strong>${escapeHtml(item.attempts)}</strong>
          <small>runtime ${escapeHtml(item.runtime)}</small>
        </div>
      </div>
      <a class="featured-trace-link" href="trace-prototype.html?case=${encodeURIComponent(item.key)}">
        View full trace
      </a>
    `;
  }

  function renderFeaturedDetail() {
    const item = selectedFeaturedCase();
    $("featured-detail-body").innerHTML = `
      <div class="line-chart-card">
        <div class="line-chart-head">
          <div>
            <h4>g by attempt</h4>
            <p>Horizontal axis is attempt; the dashed line marks Surpass-SOTA at g&gt;0.1.</p>
          </div>
          <span>${escapeHtml(item.caseId)}</span>
        </div>
        ${renderAttemptLineChart(item)}
      </div>
    `;
  }

  function renderFeaturedCase() {
    const item = selectedFeaturedCase();
    renderFeaturedCaseTabs();
    renderFeaturedSummary(item);
    renderFeaturedDetail();
  }

  function renderFeaturedCompare() {
    const compare = $("featured-case-compare");
    if (!compare) return;

    compare.innerHTML = featuredCases.map((item) => `
      <div class="featured-compare-cell">
        <span>${escapeHtml(item.role)}</span>
        <strong>${escapeHtml(item.bestG)} · ${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.takeaway)}</p>
      </div>
    `).join("");
  }

  function renderFeaturedCases() {
    renderFeaturedCase();
    renderFeaturedCompare();
  }

  function bindEvents() {
    const rankMetric = $("rank-metric");
    if (rankMetric) {
      rankMetric.addEventListener("change", (event) => {
        state.rankMetric = event.target.value;
        renderLeaderboard();
      });
    }

    $("domain-select").addEventListener("change", (event) => {
      state.selectedDomain = event.target.value;
      renderDomainDetail();
    });

    $("case-search").addEventListener("input", (event) => {
      state.caseSearch = event.target.value;
      renderCaseTable();
    });

    $("case-domain-filter").addEventListener("change", (event) => {
      state.caseDomain = event.target.value;
      renderCaseTable();
    });

    $("theme-toggle").addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem("naturebench-theme", next);
      } catch {
        // Ignore storage failures for file:// previews.
      }
    });

    const menuToggle = $("menu-toggle");
    const navRight = $("nav-right");
    menuToggle.addEventListener("click", () => {
      const open = navRight.classList.toggle("open");
      menuToggle.setAttribute("aria-expanded", String(open));
    });

    navRight.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navRight.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  function initTheme() {
    try {
      const saved = localStorage.getItem("naturebench-theme");
      if (saved === "dark" || saved === "light") {
        document.documentElement.setAttribute("data-theme", saved);
      }
    } catch {
      // Ignore storage failures for file:// previews.
    }
  }

  function init() {
    initTheme();
    ensureLeaderboardContainers();
    ensureCaseLegend();
    updateStaticLabels();
    renderSummary();
    renderLeaderboard();
    renderFeaturedCases();
    renderDistribution();
    renderDomainGrid();
    renderDomainSelect();
    renderDomainDetail();
    renderDomainWinners();
    renderCaseFilters();
    renderCaseLegend();
    renderCaseTable();
    bindEvents();
  }

  init();
})();
