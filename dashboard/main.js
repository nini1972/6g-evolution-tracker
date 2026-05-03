// Chart Global Defaults
if (window.Chart) {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.font.family = 'Inter';
}

// DOM Elements
const articlesGrid = document.getElementById('articles-grid');
const lastUpdateBadge = document.getElementById('last-update');
const sourceFilter = document.getElementById('source-filter');

// ---------------------------------------------------------------------------
// Security helpers
// ---------------------------------------------------------------------------

/**
 * Escape HTML special characters to prevent XSS when injecting user-supplied
 * content into innerHTML.
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Validate a URL is safe (http or https only) before using it as a link target.
 * Returns the URL if safe, '#' otherwise.
 * @param {string} url
 * @returns {string}
 */
function safeUrl(url) {
    try {
        const parsed = new URL(url);
        if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
            return url;
        }
    } catch (_) {
        // fall through
    }
    return '#';
}

// Fetch data from the generated JSON
let allArticles = [];

async function loadData() {
    try {
        console.log('🚀 Loading 6G Intelligence Data...');
        const response = await fetch('./latest_digest.json');
        if (!response.ok) throw new Error('latest_digest.json not found');

        const data = await response.json();
        allArticles = data.articles || [];

        // Load momentum data from its own file (momentum_data.json is a separate file)
        let momentumData = Array.isArray(data.momentum_data) ? data.momentum_data : [];
        try {
            const momResponse = await fetch('./momentum_data.json');
            if (momResponse.ok) {
                const momFromFile = await momResponse.json();
                if (Array.isArray(momFromFile)) {
                    momentumData = momFromFile;
                    console.log('✅ Momentum Data Loaded');
                }
            }
        } catch (mErr) {
            console.warn('⚠️ Momentum data could not be loaded:', mErr);
        }

        // Load historical memory (new Phase 3 feature)
        let historicalMemory = null;
        try {
            // Try local folder first, then parent folder
            let histResponse = await fetch('./historical_intelligence.json');
            if (!histResponse.ok) {
                histResponse = await fetch('../historical_intelligence.json');
            }

            if (histResponse.ok) {
                historicalMemory = await histResponse.json();
                console.log('✅ Historical Memory Loaded');
            }
        } catch (hErr) {
            console.warn('⚠️ Historical memory could not be loaded:', hErr);
        }

        // Load source-target matrix from its own file
        let flowMatrix = {};
        try {
            const matrixResponse = await fetch('./source_target_matrix.json');
            if (matrixResponse.ok) {
                const matrixFromFile = await matrixResponse.json();
                if (matrixFromFile && typeof matrixFromFile === 'object') {
                    flowMatrix = matrixFromFile;
                    console.log('✅ Source-Target Matrix Loaded');
                }
            }
        } catch (mxErr) {
            console.warn('⚠️ Source-target matrix could not be loaded:', mxErr);
        }

        // Render Panels with individual safety catches
        try { renderExecutiveBriefing(data.executive_briefing); } catch (e) { console.error('Briefing error:', e); }
        try { renderMomentumPanel(momentumData, historicalMemory); } catch (e) { console.error('Momentum error:', e); }
        try { renderMomentumCharts(momentumData); } catch (e) { console.error('Momentum charts error:', e); }
        try { renderFlowMatrix(flowMatrix); } catch (e) { console.error('Flow Matrix error:', e); }
        try { renderStandardizationPanel(data.standardization); } catch (e) { console.error('Standardization error:', e); }

        if (data.date) {
            lastUpdateBadge.textContent = `Last Update: ${data.date}`;
        }

        // Article-dependent components
        try { populateSourceFilter(allArticles); } catch (e) { console.error('Filter error:', e); }
        try { renderArticles(allArticles); } catch (e) { console.error('Articles render error:', e); }
        try { checkQuietMonth(allArticles); } catch (e) { console.error('Quiet month check error:', e); }
        try { renderConceptsPanel(allArticles); } catch (e) { console.error('Concepts error:', e); }
        try { renderEvidencePanel(allArticles); } catch (e) { console.error('Evidence error:', e); }
        try { renderTopicFrequencyChart(allArticles); } catch (e) { console.error('Topic chart error:', e); }

    } catch (err) {
        console.error('❌ Critical Error loading 6G data:', err);
        const errorHtml = `
            <div class="loading-state">
                <p style="color: #ff4b4b; font-weight: bold;">Error loading intelligence signals.</p>
                <p style="font-size: 0.8rem; opacity: 0.7;">Check if latest_digest.json is generated and accessible.</p>
            </div>
        `;
        if (articlesGrid) articlesGrid.innerHTML = errorHtml;

        // Also update other loading sectors to avoid infinite spinners
        const sectors = ['standardization-content', 'concepts-content', 'evidence-content', 'momentum-content'];
        sectors.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = errorHtml;
        });
        // Clear topics-chart spinner separately (it has a different structure)
        const topicsChart = document.getElementById('topics-chart');
        if (topicsChart) {
            const topicsLoader = topicsChart.querySelector('.loading-state');
            if (topicsLoader) topicsLoader.remove();
        }
    }
}

function renderExecutiveBriefing(briefing) {
    const container = document.getElementById('briefing-panel');
    const content = document.getElementById('briefing-content');
    if (!container || !content || !briefing) return;

    container.style.display = 'block';
    content.innerHTML = briefing; // Assuming markdown-to-html or plain HTML
}

function renderArticles(articles) {
    if (articles.length === 0) {
        articlesGrid.innerHTML = '<div class="loading-state"><p>No articles found matching your criteria.</p></div>';
        return;
    }

    articlesGrid.innerHTML = articles.map(article => {
        let impact = '?';
        let impactLabel = 'Impact';
        const regionFlag = article.ai_insights ? getRegionFlag(article.ai_insights.source_region) : "🌍";

        if (article.ai_insights && article.ai_insights.impact_score) {
            impact = article.ai_insights.impact_score;
        } else if (article.score) {
            // Fallback to keyword relevance score if AI failed
            impact = article.score;
            impactLabel = 'Relevance';
        }

        const summary = article.ai_insights ? article.ai_insights.summary : article.summary;
        const safeLink = safeUrl(article.link);

        return `
            <div class="article-card" onclick="window.open('${escapeHtml(safeLink)}', '_blank')">
                <div class="source-tag">${escapeHtml(article.source)}</div>
                <h3>${escapeHtml(article.title)}</h3>
                <p class="article-summary">${escapeHtml(summary)}</p>
                <div class="article-footer">
                    <div class="impact-badge">${impactLabel}: ${escapeHtml(String(impact))}/10</div>
                    <div class="date-text">${escapeHtml(article.date)}</div>
                </div>
            </div>
        `;
    }).join('');
}
function renderMomentumPanel(momentumData, historicalMemory) {
    const container = document.getElementById('momentum-content');
    if (!container) return;

    if (!momentumData || momentumData.length === 0) {
        container.innerHTML = `<p>No current momentum data available.</p>`;
        return;
    }

    // Clear any loading state before rendering cards
    container.innerHTML = '';

    // 1. Render Cards (Existing logic)
    renderMomentumCards(momentumData, container);

    // 2. Render Trend Chart (New Phase 3 feature) — canvas is optional
    const chartCanvas = document.getElementById('momentum-chart');
    if (chartCanvas && historicalMemory && historicalMemory.standardization_snapshots) {
        renderMomentumTrendChart(chartCanvas, historicalMemory.standardization_snapshots);
    }
}

function renderMomentumCards(momentumData, container) {
    momentumData.sort((a, b) => {
        if (a.region !== b.region) return a.region.localeCompare(b.region);
        return a.time_window.localeCompare(b.time_window);
    });

    const cards = momentumData.map(entry => {
        const flag = getRegionFlag(entry.region);
        return `
            <div class="momentum-card">
                <div class="momentum-header">
                    <span class="region-flag">${flag}</span>
                    <span class="region-name">${entry.region}</span>
                </div>
                <div class="momentum-score">Score: <strong>${entry.momentum_score.toFixed(1)}</strong></div>
                <div class="momentum-quarter">${entry.time_window}</div>
                <div class="momentum-breakdown">
                    <div>Res: ${entry.research_intensity}</div>
                    <div>Std: ${entry.standardization_influence}</div>
                </div>
            </div>
        `;
    }).join('');
    container.innerHTML = cards;
}

function renderMomentumTrendChart(canvas, snapshots) {
    if (!window.Chart) return;

    const ctx = canvas.getContext('2d');
    const labels = snapshots.map(s => s.date);
    const dataset = {
        label: 'Global 3GPP Progress (%)',
        data: snapshots.map(s => s.data?.release_21_progress?.progress_percentage || 0),
        borderColor: '#00f2ff',
        backgroundColor: 'rgba(0, 242, 255, 0.1)',
        tension: 0.4,
        fill: true
    };

    new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [dataset] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: {
                y: { beginAtZero: true, max: 100 }
            }
        }
    });
}

function renderTopicFrequencyChart(articles) {
    const canvas = document.getElementById('topics-chart-canvas');
    const topicsChart = document.getElementById('topics-chart');

    // Always remove the loading spinner regardless of outcome
    if (topicsChart) {
        const loader = topicsChart.querySelector('.loading-state');
        if (loader) loader.remove();
    }

    if (!canvas || !window.Chart) return;

    let topicCounts = {};
    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights['6g_topics']) {
            article.ai_insights['6g_topics'].forEach(topic => {
                topicCounts[topic] = (topicCounts[topic] || 0) + 1;
            });
        }
    });

    const topics = Object.entries(topicCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);

    if (topics.length === 0) {
        if (topicsChart) {
            topicsChart.innerHTML = '<p class="empty-state">No topic data available for this cycle.</p>';
        }
        return;
    }

    const ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topics.map(t => t[0]),
            datasets: [{
                label: 'Signal Frequency',
                data: topics.map(t => t[1]),
                backgroundColor: 'rgba(112, 0, 255, 0.6)',
                borderColor: '#7000ff',
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { display: false } }
            }
        }
    });
}

// ... existing helper functions (renderArticles, populateSourceFilter, etc.) ...
// (Kept for completeness but assumed they follow similar patterns)

function renderStandardizationPanel(stdData) {
    const container = document.getElementById('standardization-content');
    if (!container) return;

    if (!stdData || !stdData.release_21_progress) {
        container.innerHTML = `<p>No standardization data available.</p>`;
        return;
    }

    const progress = stdData.release_21_progress;
    const meetings = stdData.recent_meetings || [];
    const byGroup = stdData.work_items_by_group || {};
    const dataSource = progress.data_source || "live";

    let html = `<h3>3GPP Release 21 Progress</h3>`;

    if (dataSource === "sample") {
        html += `<div class="sample-data-badge">⚠️ Using sample data</div>`;
    }

    html += `
        <div class="progress-bar-container">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress.progress_percentage}%">${progress.progress_percentage}%</div>
            </div>
            <p class="progress-stats">${progress.completed}/${progress.total_work_items} Completed</p>
        </div>
    `;

    if (meetings.length > 0) {
        html += `<div class="meetings-list">`;
        meetings.forEach(m => {
            html += `
                <div class="meeting-card">
                    <div class="meeting-header">
                        <span class="meeting-wg">${m.working_group}</span>
                        <span class="meeting-id">${m.meeting_id}</span>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    container.innerHTML = html;
}

function renderConceptsPanel(articles) {
    const container = document.getElementById('concepts-content');
    if (!container) return;
    let concepts = [];
    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights.emerging_concepts) {
            concepts.push(...article.ai_insights.emerging_concepts);
        }
    });
    concepts = [...new Set(concepts)];
    if (concepts.length === 0) {
        container.innerHTML = '<p class="empty-state">No emerging concepts extracted this cycle.</p>';
        return;
    }
    container.innerHTML = concepts.map(c => `<span class="concept-tag">${c}</span>`).join('');
}

function renderEvidencePanel(articles) {
    const container = document.getElementById('evidence-content');
    if (!container) return;
    let evidence = [];
    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights.key_evidence) {
            evidence.push(...article.ai_insights.key_evidence);
        }
    });
    if (evidence.length === 0) {
        container.innerHTML = '<p class="empty-state">No key evidence extracted this cycle.</p>';
        return;
    }
    container.innerHTML = evidence.map(e => `<div class="evidence-card">• ${e}</div>`).join('');
}

function renderFlowMatrix(matrix) {
    const container = document.getElementById('flow-matrix');
    if (!container) return;
    const regions = ["US", "EU", "China", "Japan", "Korea", "India"];
    let html = `<table class="flow-table"><thead><tr><th>Source → Target</th>${regions.map(r => `<th>${r}</th>`).join('')}</tr></thead><tbody>`;
    regions.forEach(source => {
        html += `<tr><td>${source}</td>`;
        regions.forEach(target => {
            const val = matrix[source]?.[target] ?? 0;
            html += `<td>${val}</td>`;
        });
        html += `</tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
}

function getRegionFlag(region) {
    const flags = { "US": "🇺🇸", "EU": "🇪🇺", "China": "🇨🇳", "Japan": "🇯🇵", "Korea": "🇰🇷", "India": "🇮🇳" };
    return flags[region] || "🌍";
}

function populateSourceFilter(articles) {
    const sources = [...new Set(articles.map(a => a.source))];
    if (!sourceFilter) return;
    sources.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        sourceFilter.appendChild(opt);
    });
}

function checkQuietMonth(articles) {
    const banner = document.getElementById('quiet-banner');
    if (banner && articles.length === 0) banner.style.display = 'block';
}

// ---------------------------------------------------------------------------
// Chart.js Visualizations (require Chart.js loaded in index.html)
// ---------------------------------------------------------------------------

const REGIONS = ["US", "EU", "China", "Japan", "Korea", "India"];

const REGION_COLORS = {
    "US":     "rgba( 59, 130, 246, 0.8)",
    "EU":     "rgba( 16, 185, 129, 0.8)",
    "China":  "rgba(239,  68,  68, 0.8)",
    "Japan":  "rgba(245, 158,  11, 0.8)",
    "Korea":  "rgba(139,  92, 246, 0.8)",
    "India":  "rgba(236,  72, 153, 0.8)",
};

/**
 * Render all three Chart.js visualisations from momentumData.
 * @param {Array} momentumData
 */
function renderMomentumCharts(momentumData) {
    if (!momentumData || momentumData.length === 0) return;
    if (typeof Chart === 'undefined') return; // Chart.js not loaded

    _renderHeatmap(momentumData);
    _renderRadarCharts(momentumData);
    _renderLineChart(momentumData);
}

// --- Heatmap: regions × quarters, cell colour = momentum score ---

function _renderHeatmap(momentumData) {
    const canvas = document.getElementById('chart-heatmap');
    if (!canvas) return;

    // Collect all unique time windows (quarters), sorted
    const quarters = [...new Set(momentumData.map(d => d.time_window))].sort();

    // Build matrix: region → quarter → momentum_score
    const matrix = {};
    REGIONS.forEach(r => { matrix[r] = {}; });
    momentumData.forEach(d => {
        if (matrix[d.region]) {
            matrix[d.region][d.time_window] = d.momentum_score;
        }
    });

    const datasets = REGIONS.map(region => ({
        label: region,
        data: quarters.map(q => matrix[region][q] ?? null),
        borderColor: REGION_COLORS[region],
        backgroundColor: REGION_COLORS[region],
        fill: false,
        tension: 0.3,
        pointRadius: 6,
    }));

    new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: quarters, datasets },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: '6G Momentum Heatmap (Regions × Quarters)' },
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) : 'N/A'}`,
                    },
                },
            },
            scales: {
                y: { title: { display: true, text: 'Momentum Score' }, min: 0, max: 5 },
                x: { title: { display: true, text: 'Quarter' } },
            },
        },
    });
}

// --- Radar: latest year per region, impact dimensions as axes ---

const RADAR_DIMS = [
    'research_intensity',
    'standardization_influence',
    'industrial_deployment',
    'spectrum_policy_signal',
    'ecosystem_maturity',
];
const RADAR_LABELS = ['Research', 'Standardization', 'Deployment', 'Spectrum', 'Ecosystem'];

function _renderRadarCharts(momentumData) {
    const container = document.getElementById('chart-radar-container');
    if (!container) return;

    // Get the latest quarter per region
    const latestByRegion = {};
    momentumData.forEach(d => {
        if (!latestByRegion[d.region] || d.time_window > latestByRegion[d.region].time_window) {
            latestByRegion[d.region] = d;
        }
    });

    container.innerHTML = ''; // clear

    REGIONS.forEach(region => {
        const entry = latestByRegion[region];
        if (!entry) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'radar-wrapper';
        const canvas = document.createElement('canvas');
        canvas.id = `radar-${region}`;
        wrapper.appendChild(canvas);
        container.appendChild(wrapper);

        new Chart(canvas.getContext('2d'), {
            type: 'radar',
            data: {
                labels: RADAR_LABELS,
                datasets: [{
                    label: `${getRegionFlag(region)} ${region} (${entry.time_window})`,
                    data: RADAR_DIMS.map(d => entry[d] ?? 0),
                    backgroundColor: REGION_COLORS[region].replace('0.8)', '0.25)'),
                    borderColor: REGION_COLORS[region],
                    pointBackgroundColor: REGION_COLORS[region],
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } },
                scales: { r: { min: 0, max: 5, ticks: { stepSize: 1 } } },
            },
        });
    });
}

// --- Stacked line chart: momentum evolution over time per region ---

function _renderLineChart(momentumData) {
    const canvas = document.getElementById('chart-momentum-line');
    if (!canvas) return;

    const quarters = [...new Set(momentumData.map(d => d.time_window))].sort();

    const matrix = {};
    REGIONS.forEach(r => { matrix[r] = {}; });
    momentumData.forEach(d => {
        if (matrix[d.region]) {
            matrix[d.region][d.time_window] = d.momentum_score;
        }
    });

    const datasets = REGIONS.map(region => ({
        label: `${getRegionFlag(region)} ${region}`,
        data: quarters.map(q => matrix[region][q] ?? null),
        borderColor: REGION_COLORS[region],
        backgroundColor: REGION_COLORS[region].replace('0.8)', '0.15)'),
        fill: true,
        tension: 0.4,
        spanGaps: true,
    }));

    new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: { labels: quarters, datasets },
        options: {
            responsive: true,
            plugins: {
                title: { display: true, text: '6G Momentum Evolution by Region' },
                legend: { position: 'bottom' },
            },
            scales: {
                y: { title: { display: true, text: 'Momentum Score' }, min: 0 },
                x: { title: { display: true, text: 'Quarter' } },
            },
        },
    });
}

// Initial load
loadData();
