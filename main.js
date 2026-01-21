// Chart Global Defaults
if (window.Chart) {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
    Chart.defaults.font.family = 'Inter';
}

// Fetch data from the generated JSON
// Fetch data from the generated JSON
// Fetch data from the generated JSON
let allArticles = [];

async function loadData() {
    try {
        console.log('🚀 Loading 6G Intelligence Data...');
        const response = await fetch('./latest_digest.json');
        if (!response.ok) throw new Error('latest_digest.json not found');

        const data = await response.json();
        allArticles = data.articles || [];

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

        // Render Panels with individual safety catches
        try { renderExecutiveBriefing(data.executive_briefing); } catch (e) { console.error('Briefing error:', e); }
        try { renderMomentumPanel(data.momentum_data || [], historicalMemory); } catch (e) { console.error('Momentum error:', e); }
        try { renderFlowMatrix(data.flow_matrix || {}); } catch (e) { console.error('Flow Matrix error:', e); }
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
        articlesGrid.innerHTML = errorHtml;

        // Also update other loading sectors to avoid infinite spinners
        const sectors = ['standardization-content', 'concepts-content', 'evidence-content', 'momentum-content'];
        sectors.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = errorHtml;
        });
    }
}

function renderExecutiveBriefing(briefing) {
    const container = document.getElementById('briefing-panel');
    const content = document.getElementById('briefing-content');
    if (!container || !content || !briefing) return;

    container.style.display = 'block';
    content.innerHTML = briefing; // Assuming markdown-to-html or plain HTML
}

function renderMomentumPanel(momentumData, historicalMemory) {
    const container = document.getElementById('momentum-content');
    const chartCanvas = document.getElementById('momentum-chart');
    if (!container || !chartCanvas) return;

    if (!momentumData || momentumData.length === 0) {
        container.innerHTML = `<p>No current momentum data available.</p>`;
        return;
    }

    // 1. Render Cards (Existing logic)
    renderMomentumCards(momentumData, container);

    // 2. Render Trend Chart (New Phase 3 feature)
    if (historicalMemory && historicalMemory.standardization_snapshots) {
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
    const sourceFilter = document.getElementById('source-filter');
    if (!sourceFilter) return;
    sources.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        sourceFilter.appendChild(opt);
    });
}

function renderArticles(articles) {
    const grid = document.getElementById('articles-grid');
    if (!grid) return;
    grid.innerHTML = articles.map(a => `
        <div class="article-card" onclick="window.open('${a.link}', '_blank')">
            <div class="source-tag">${a.source}</div>
            <h3>${a.title}</h3>
            <p>${a.ai_insights ? a.ai_insights.summary : a.summary}</p>
        </div>
    `).join('');
}

function checkQuietMonth(articles) {
    const banner = document.getElementById('quiet-banner');
    if (banner && articles.length === 0) banner.style.display = 'block';
}

// Initial load
loadData();
