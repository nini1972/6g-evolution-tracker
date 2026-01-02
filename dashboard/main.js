const articlesGrid = document.getElementById('articles-grid');
const searchInput = document.getElementById('search');
const sourceFilter = document.getElementById('source-filter');
const lastUpdateBadge = document.getElementById('last-update');

let allArticles = [];

// Fetch data from the generated JSON
async function loadData() {
    try {
        const response = await fetch('./latest_digest.json');
        if (!response.ok) throw new Error('Could not load data');

        const data = await response.json();
        allArticles = data.articles;

        // Try to load momentum data (optional for now)
        try {
            const momResponse = await fetch('./momentum_data.json');
            if (momResponse.ok) {
                const momentumData = await momResponse.json();
                console.log('Deep Analysis Momentum Data Loaded:', momentumData);
                renderMomentumPanel(momentumData);
                                  }
        } catch (mErr) {
            console.log('Momentum data not yet available.');
        }
        // Load Source → Target Region Matrix
        try {
            const flowResponse = await fetch('./source_target_matrix.json');
            if (flowResponse.ok) {
                const flowMatrix = await flowResponse.json();
                console.log("Source→Target Matrix Loaded:", flowMatrix);
                renderFlowMatrix(flowMatrix);
            }
        } catch (err) {
            console.log("Flow matrix not available yet.");
        }

        lastUpdateBadge.textContent = `Last Update: ${data.date}`;

        populateSourceFilter(allArticles);
        renderArticles(allArticles);
        renderConceptsPanel(allArticles);
        renderEvidencePanel(allArticles);

    } catch (err) {
        console.error('Error loading 6G data:', err);
        articlesGrid.innerHTML = `
            <div class="loading-state">
                <p style="color: #ff4b4b;">Error loading intelligence signals. Ensure latest_digest.json is generated.</p>
            </div>
        `;
    }
}

function populateSourceFilter(articles) {
    const sources = [...new Set(articles.map(a => a.source))];
    sources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        sourceFilter.appendChild(option);
    });
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

        return `
            <div class="article-card" onclick="window.open('${article.link}', '_blank')">
                <div class="source-tag">${article.source}</div>
                <h3>${article.title}</h3>
                <p class="article-summary">${summary}</p>
                <div class="article-footer">
                    <div class="impact-badge">${impactLabel}: ${impact}/10</div>
                    <div class="date-text">${article.date}</div>
                </div>
            </div>
        `;
    }).join('');
}
function renderMomentumPanel(momentumData) {
    const container = document.getElementById('momentum-content');
    if (!container) return;

    if (!momentumData || momentumData.length === 0) {
        container.innerHTML = `<p>No momentum data available.</p>`;
        return;
    }

    // For now, momentumData is an array of region-quarter entries
    const cards = momentumData.map(entry => {
        const flag = getRegionFlag(entry.region);
        return `
            <div class="momentum-card">
                <div class="momentum-header">
                    <span class="region-flag">${flag}</span>
                    <span class="region-name">${entry.region}</span>
                </div>
                <div class="momentum-score">Momentum: <strong>${entry.momentum_score.toFixed(1)}</strong></div>
                <div class="momentum-quarter">${entry.time_window}</div>

                <div class="momentum-breakdown">
                    <div>Research: ${entry.research_intensity}</div>
                    <div>Standardization: ${entry.standardization_influence}</div>
                    <div>Deployment: ${entry.industrial_deployment}</div>
                    <div>Spectrum: ${entry.spectrum_policy_signal}</div>
                    <div>Ecosystem: ${entry.ecosystem_maturity}</div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = cards;
}
function renderConceptsPanel(articles) {
    const container = document.getElementById('concepts-content');
    if (!container) return;

    // Collect all emerging concepts from all articles
    let concepts = [];

    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights.emerging_concepts) {
            concepts.push(...article.ai_insights.emerging_concepts);
        }
    });

    // Remove duplicates
    concepts = [...new Set(concepts)];

    if (concepts.length === 0) {
        container.innerHTML = `<p>No emerging concepts detected.</p>`;
        return;
    }

    // Render as concept tags
    const html = concepts.map(c => `
        <span class="concept-tag">${c}</span>
    `).join('');

    container.innerHTML = html;
}

function renderEvidencePanel(articles) {
    const container = document.getElementById('evidence-content');
    if (!container) return;

    let evidenceList = [];

    // Collect all evidence from all articles
    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights.key_evidence) {
            evidenceList.push(...article.ai_insights.key_evidence);
        }
    });

    if (evidenceList.length === 0) {
        container.innerHTML = `<p>No technical evidence available.</p>`;
        return;
    }

    // Render each evidence point as a card
    const html = evidenceList.map(item => `
        <div class="evidence-card">
            <span class="evidence-bullet">•</span>
            <p>${item}</p>
        </div>
    `).join('');

    container.innerHTML = html;
}


function getRegionFlag(region) {
    const flags = {
        "US": "🇺🇸",
        "EU": "🇪🇺",
        "China": "🇨🇳",
        "Japan": "🇯🇵",
        "Korea": "🇰🇷",
        "India": "🇮🇳"
    };
    return flags[region] || "🌍";
}


function renderFlowMatrix(matrix) {
    const container = document.getElementById('flow-matrix');
    if (!container) return;

    const regions = ["US", "EU", "China", "Japan", "Korea", "India"];

    let html = `
        <table class="flow-table">
            <thead>
                <tr>
                    <th>Source ↓ / Target →</th>
                    ${regions.map(r => `<th>${r}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
    `;

    regions.forEach(source => {
        html += `<tr><td class="row-label">${source}</td>`;
        regions.forEach(target => {
            const value = matrix[source]?.[target] ?? 0;
            html += `<td class="flow-cell" data-value="${value}">${value}</td>`;
        });
        html += `</tr>`;
    });

    html += `
            </tbody>
        </table>
    `;

    container.innerHTML = html;

    // Optional: heatmap coloring
    const cells = container.querySelectorAll('.flow-cell');
    let max = 0;
    cells.forEach(c => max = Math.max(max, parseInt(c.dataset.value)));

    cells.forEach(cell => {
        const v = parseInt(cell.dataset.value);
        const intensity = max > 0 ? v / max : 0;
        cell.style.backgroundColor = `rgba(0, 150, 255, ${intensity * 0.6})`;
    });
}

// Filtering logic
function filterArticles() {
    const searchTerm = searchInput.value.toLowerCase();
    const selectedSource = sourceFilter.value;

    const filtered = allArticles.filter(article => {
        const matchesSearch = article.title.toLowerCase().includes(searchTerm) ||
            article.summary.toLowerCase().includes(searchTerm);
        const matchesSource = selectedSource === 'all' || article.source === selectedSource;

        return matchesSearch && matchesSource;
    });

    renderArticles(filtered);
}

searchInput.addEventListener('input', filterArticles);
sourceFilter.addEventListener('change', filterArticles);

// Initial load
loadData();
