// Reports course activity — chart-based analytics for report statements

import Chart from "chart.js/auto";

const VERBS = ["completed", "passed", "failed", "progressed", "scored"];
const VERB_COLORS = {
  completed: "#4caf50",
  passed: "#2196f3",
  failed: "#f44336",
  progressed: "#ff9800",
  scored: "#9c27b0",
};

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  let config = activity.state.config || {};
  let data = activity.state.data || [];
  let chart = null;

  activity.onEvent = (name, value) => {
    if (name === "data.result") {
      data = value;
      renderChart();
    } else if (name === "fields.change.config") {
      config = value;
    }
  };

  function render() {
    if (permission === "edit") {
      renderEditView();
    } else {
      renderPlayView();
    }
  }

  function renderEditView() {
    element.innerHTML = `
      <style>
        .reports-container { font-family: sans-serif; max-width: 800px; }
        .reports-form { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 1rem; }
        .reports-form label { font-size: 0.85rem; color: #555; }
        .reports-form input, .reports-form select { padding: 0.4rem; font-size: 0.9rem; border: 1px solid #ccc; border-radius: 4px; }
        .title-row { grid-column: 1 / -1; }
        .title-row input { width: 100%; box-sizing: border-box; }
        .save-btn { padding: 0.5rem 1.5rem; cursor: pointer; background: #1976d2; color: white; border: none; border-radius: 4px; font-size: 0.9rem; }
        .save-btn:hover { background: #1565c0; }
        .feedback { margin-top: 0.5rem; padding: 0.4rem; border-radius: 4px; font-size: 0.85rem; }
        .feedback.success { background: #d4edda; color: #155724; }
        .chart-preview { margin-top: 1rem; }
        .chart-preview canvas { max-height: 350px; }
      </style>
      <div class="reports-container">
        <h3>Configure Report Chart</h3>
        <div class="reports-form">
          <div class="title-row">
            <label>Title</label>
            <input type="text" id="rpt-title" value="${escapeAttr(config.title || "")}" placeholder="Chart title">
          </div>
          <div>
            <label>Activity name</label>
            <input type="text" id="rpt-activity-name" value="${escapeAttr(config.activity_name || "")}" placeholder="e.g. math">
          </div>
          <div>
            <label>Activity ID</label>
            <input type="text" id="rpt-activity-id" value="${escapeAttr(config.activity_id || "")}" placeholder="Optional">
          </div>
          <div>
            <label>User ID</label>
            <input type="text" id="rpt-user-id" value="${escapeAttr(config.user_id || "")}" placeholder="Optional">
          </div>
          <div>
            <label>Verb</label>
            <select id="rpt-verb">
              <option value="">All</option>
              ${VERBS.map((v) => `<option value="${v}"${config.verb === v ? " selected" : ""}>${v}</option>`).join("")}
            </select>
          </div>
          <div>
            <label>From date</label>
            <input type="datetime-local" id="rpt-after-date" value="${escapeAttr(config.after_date || "")}">
          </div>
          <div>
            <label>To date</label>
            <input type="datetime-local" id="rpt-before-date" value="${escapeAttr(config.before_date || "")}">
          </div>
          <div>
            <label>Chart type</label>
            <select id="rpt-chart-type">
              <option value="bar"${config.chart_type === "bar" || !config.chart_type ? " selected" : ""}>Bar</option>
              <option value="pie"${config.chart_type === "pie" ? " selected" : ""}>Pie</option>
              <option value="line"${config.chart_type === "line" ? " selected" : ""}>Line</option>
            </select>
          </div>
        </div>
        <button type="button" class="save-btn" id="rpt-save">Save</button>
        <div id="rpt-feedback"></div>
        <div class="chart-preview">
          <canvas id="rpt-chart"></canvas>
        </div>
      </div>
    `;

    element.querySelector("#rpt-save").addEventListener("click", async () => {
      const newConfig = readForm();
      config = newConfig;
      const feedbackEl = element.querySelector("#rpt-feedback");
      try {
        await activity.sendAction("config.save", newConfig);
        feedbackEl.innerHTML =
          '<div class="feedback success">Saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML =
          '<div class="feedback" style="background:#f8d7da;color:#721c24;">Error saving</div>';
      }
    });

    renderChart();
  }

  function renderPlayView() {
    const title = config.title || "Report";
    element.innerHTML = `
      <style>
        .reports-container { font-family: sans-serif; max-width: 800px; }
        .reports-title { margin: 0 0 0.5rem 0; }
        .chart-area canvas { max-height: 400px; }
        .refresh-btn { margin-top: 0.5rem; padding: 0.3rem 1rem; cursor: pointer; font-size: 0.85rem; border: 1px solid #ccc; border-radius: 4px; background: white; }
        .refresh-btn:hover { background: #f5f5f5; }
        .no-data { color: #666; font-style: italic; padding: 2rem; text-align: center; }
      </style>
      <div class="reports-container">
        <h3 class="reports-title">${escapeHtml(title)}</h3>
        <div class="chart-area">
          <canvas id="rpt-chart"></canvas>
        </div>
        <button type="button" class="refresh-btn" id="rpt-refresh">Refresh</button>
      </div>
    `;

    element.querySelector("#rpt-refresh").addEventListener("click", () => {
      activity.sendAction("data.refresh", {});
    });

    renderChart();
  }

  function readForm() {
    return {
      title: element.querySelector("#rpt-title").value.trim(),
      activity_name: element.querySelector("#rpt-activity-name").value.trim(),
      activity_id: element.querySelector("#rpt-activity-id").value.trim(),
      user_id: element.querySelector("#rpt-user-id").value.trim(),
      verb: element.querySelector("#rpt-verb").value,
      after_date: element.querySelector("#rpt-after-date").value,
      before_date: element.querySelector("#rpt-before-date").value,
      chart_type: element.querySelector("#rpt-chart-type").value,
    };
  }

  function renderChart() {
    const canvas = element.querySelector("#rpt-chart");
    if (!canvas) return;

    if (chart) {
      chart.destroy();
      chart = null;
    }

    if (!data || data.length === 0) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const chartType = config.chart_type || "bar";

    if (chartType === "line") {
      chart = buildLineChart(canvas, data);
    } else {
      chart = buildVerbChart(canvas, data, chartType);
    }
  }

  function buildVerbChart(canvas, rows, type) {
    const counts = {};
    for (const row of rows) {
      counts[row.verb] = (counts[row.verb] || 0) + 1;
    }
    const labels = Object.keys(counts);
    const values = labels.map((l) => counts[l]);
    const colors = labels.map((l) => VERB_COLORS[l] || "#999");

    return new Chart(canvas, {
      type,
      data: {
        labels,
        datasets: [
          {
            label: "Statements",
            data: values,
            backgroundColor: colors,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: !!config.title,
            text: config.title || "",
          },
        },
      },
    });
  }

  function buildLineChart(canvas, rows) {
    // Group by date (YYYY-MM-DD)
    const counts = {};
    for (const row of rows) {
      const day = row.created_at.slice(0, 10);
      counts[day] = (counts[day] || 0) + 1;
    }
    const labels = Object.keys(counts).sort();
    const values = labels.map((d) => counts[d]);

    return new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Statements per day",
            data: values,
            borderColor: "#1976d2",
            backgroundColor: "rgba(25,118,210,0.1)",
            fill: true,
            tension: 0.3,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: !!config.title,
            text: config.title || "",
          },
        },
        scales: {
          y: { beginAtZero: true },
        },
      },
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  render();
}
