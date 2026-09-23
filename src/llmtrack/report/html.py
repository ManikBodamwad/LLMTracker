"""
HTML report generation using Jinja2 templates.
Produces a self-contained, interactive, responsive dark-mode HTML report.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Union

from jinja2 import Template

if TYPE_CHECKING:
    from llmtrack.tracker import CallEvent

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>llmtrack Cost Report</title>
<style>
  :root {
    --bg-primary: #0f1117;
    --bg-surface: #1a1d24;
    --bg-card: #222631;
    --border-color: #2e3442;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --accent-green: #10b981;
    --accent-emerald: #34d399;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-cyan: #06b6d4;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-main);
    padding: 32px 24px;
    line-height: 1.5;
  }
  .container { max-width: 1200px; margin: 0 auto; }
  .header {
    background: linear-gradient(145deg, #1c202a, #161820);
    border-radius: 14px;
    padding: 28px;
    margin-bottom: 24px;
    border: 1px solid var(--border-color);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
  }
  .title-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
  .header h1 { font-size: 26px; font-weight: 700; color: var(--accent-emerald); display: flex; align-items: center; gap: 8px; }
  .period-badge {
    background: rgba(16, 185, 129, 0.12);
    color: var(--accent-emerald);
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 600;
  }
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 24px;
  }
  .stat-card {
    background: var(--bg-card);
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid var(--border-color);
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .stat-card:hover { transform: translateY(-2px); border-color: #3b82f6; }
  .stat-card .label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
  .stat-card .value { font-size: 26px; font-weight: 700; color: #ffffff; }
  .stat-card .value.cost-val { color: var(--accent-amber); }
  .table-card {
    background: var(--bg-surface);
    border-radius: 14px;
    border: 1px solid var(--border-color);
    overflow: hidden;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
  }
  .table-responsive { width: 100%; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; text-align: left; }
  th {
    background: var(--bg-card);
    padding: 14px 18px;
    font-size: 12px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border-color);
  }
  th:hover { color: var(--text-main); }
  td { padding: 14px 18px; border-bottom: 1px solid #252a36; font-size: 14px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255, 255, 255, 0.02); }
  .feature-tag { font-weight: 600; color: #ffffff; display: inline-flex; align-items: center; gap: 6px; }
  .cost { font-weight: 700; color: var(--accent-amber); font-family: monospace; }
  .bar-container { width: 120px; background: #2a303c; height: 8px; border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
  .bar-fill.high { background: linear-gradient(90deg, #f87171, #ef4444); }
  .bar-fill.med { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
  .bar-fill.low { background: linear-gradient(90deg, #34d399, #10b981); }
  .dim { color: var(--text-muted); font-family: monospace; }
  .footer { margin-top: 20px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-muted); }
  .footer a { color: var(--accent-emerald); text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title-row">
      <h1>⚡ llmtrack Cost Report</h1>
      <span class="period-badge">Last {{ days }} Days</span>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">Total Cost</div>
        <div class="value cost-val">${{ "%.4f"|format(total_cost) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Total API Calls</div>
        <div class="value">{{ "{:,}".format(total_calls) }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Features Tracked</div>
        <div class="value">{{ features|length }}</div>
      </div>
      <div class="stat-card">
        <div class="label">Average / Call</div>
        <div class="value">${{ "%.6f"|format(avg_cost_per_call) }}</div>
      </div>
    </div>
  </div>

  <div class="table-card">
    <div class="table-responsive">
      <table id="costTable">
        <thead>
          <tr>
            <th onclick="sortTable(0)">Feature</th>
            <th onclick="sortTable(1, true)">Cost (USD)</th>
            <th onclick="sortTable(2, true)">% of Total</th>
            <th>Breakdown</th>
            <th onclick="sortTable(4, true)">Calls</th>
            <th onclick="sortTable(5, true)">Avg / Call</th>
            <th onclick="sortTable(6, true)">Input Tokens</th>
            <th onclick="sortTable(7, true)">Output Tokens</th>
          </tr>
        </thead>
        <tbody>
          {% for feature in features %}
          <tr>
            <td class="feature-tag">{{ feature.name }}</td>
            <td class="cost">${{ "%.4f"|format(feature.cost_usd) }}</td>
            <td style="font-weight:600;">{{ "%.1f"|format(feature.pct) }}%</td>
            <td>
              <div class="bar-container">
                <div class="bar-fill {{ feature.color_class }}" style="width: {{ [feature.pct, 3.0]|max }}%;"></div>
              </div>
            </td>
            <td>{{ "{:,}".format(feature.calls) }}</td>
            <td class="dim">${{ "%.6f"|format(feature.avg_cost_per_call) }}</td>
            <td class="dim">{{ "{:,}".format(feature.input_tokens) }}</td>
            <td class="dim">{{ "{:,}".format(feature.output_tokens) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    <span>Generated by <a href="https://github.com/ManikBodamwad/LLMTracker" target="_blank">llmtrack</a></span>
    <span>{{ generated_at }}</span>
  </div>
</div>

<script>
function sortTable(colIndex, isNumeric) {
  const table = document.getElementById("costTable");
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const isAsc = table.dataset.sortCol == colIndex && table.dataset.sortDir === "asc";

  rows.sort((a, b) => {
    let valA = a.children[colIndex].innerText.replace(/[$,%]/g, "").trim();
    let valB = b.children[colIndex].innerText.replace(/[$,%]/g, "").trim();
    if (isNumeric) {
      valA = parseFloat(valA) || 0;
      valB = parseFloat(valB) || 0;
      return isAsc ? valA - valB : valB - valA;
    }
    return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
  });

  table.dataset.sortCol = colIndex;
  table.dataset.sortDir = isAsc ? "desc" : "asc";
  rows.forEach(row => tbody.appendChild(row));
}
</script>
</body>
</html>
"""


def generate_html_report(
    events: List[CallEvent],
    filepath: Union[str, Path],
    days: int = 7,
) -> None:
    """
    Generate an HTML report file for the given events.

    Args:
        events: List of CallEvent objects.
        filepath: Destination path for HTML file.
        days: Period in days covered by the report.
    """
    from llmtrack.tracker import _aggregate

    summary = _aggregate(events, days=days)
    total_cost = summary["total_cost_usd"]
    total_calls = summary["total_calls"]
    avg_cost = total_cost / total_calls if total_calls > 0 else 0.0

    sorted_features_raw = sorted(
        summary["features"].items(),
        key=lambda x: x[1]["cost_usd"],
        reverse=True,
    )

    features = []
    num_features = len(sorted_features_raw)
    for idx, (name, data) in enumerate(sorted_features_raw):
        pct = (data["cost_usd"] / total_cost * 100) if total_cost > 0 else 0.0

        # Color coding: highest cost is red, lowest is green, middle is yellow
        if idx == 0 and num_features > 1 and pct > 40:
            color_class = "high"
        elif idx == num_features - 1 and num_features > 1:
            color_class = "low"
        else:
            color_class = "med"

        features.append(
            {
                "name": name,
                "cost_usd": data["cost_usd"],
                "pct": pct,
                "color_class": color_class,
                "calls": data["calls"],
                "avg_cost_per_call": data["avg_cost_per_call"],
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
            }
        )

    template = Template(HTML_TEMPLATE)
    html = template.render(
        days=days,
        total_cost=total_cost,
        total_calls=total_calls,
        avg_cost_per_call=avg_cost,
        features=features,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    path = Path(filepath)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
