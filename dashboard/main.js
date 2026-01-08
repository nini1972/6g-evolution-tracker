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

        // Load standardization data if available
        if (data.standardization) {
            console.log('3GPP Standardization Data Loaded:', data.standardization);
            renderStandardizationPanel(data.standardization);
        }

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
        checkQuietMonth(allArticles);
        renderConceptsPanel(allArticles);
        renderEvidencePanel(allArticles);
        renderTopicFrequencyChart(allArticles);


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

    // Sort by region + time_window (ensures chronological order)
    momentumData.sort((a, b) => {
        if (a.region !== b.region) return a.region.localeCompare(b.region);
        return a.time_window.localeCompare(b.time_window);
    });

    // Compute trends
    const trends = {};
    for (let i = 0; i < momentumData.length; i++) {
        const entry = momentumData[i];
        const prev = momentumData[i - 1];

        if (!prev || prev.region !== entry.region) {
            trends[entry.region] = "•"; // No previous data
        } else {
            const diff = entry.momentum_score - prev.momentum_score;
            if (diff > 0.1) trends[entry.region] = "↑";
            else if (diff < -0.1) trends[entry.region] = "↓";
            else trends[entry.region] = "→";
        }
    }

    // Render cards
    const cards = momentumData.map(entry => {
        const flag = getRegionFlag(entry.region);
        const trend = trends[entry.region];

        return `
            <div class="momentum-card">
                <div class="momentum-header">
                    <span class="region-flag">${flag}</span>
                    <span class="region-name">${entry.region}</span>
                    <span class="momentum-trend">${trend}</span>
                </div>

                <div class="momentum-score">
                    Momentum: <strong>${entry.momentum_score.toFixed(1)}</strong>
                </div>

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

function renderStandardizationPanel(stdData) {
    const container = document.getElementById('standardization-content');
    if (!container) {
        // Panel doesn't exist yet, we'll add it to the HTML
        return;
    }

    if (!stdData || !stdData.release_21_progress) {
        container.innerHTML = `<p>No standardization data available.</p>`;
        return;
    }

    const progress = stdData.release_21_progress;
    const meetings = stdData.recent_meetings || [];
    const byGroup = stdData.work_items_by_group || {};
    const dataSource = progress.data_source || "live";

    // Build the HTML
    let html = `
        <h3>3GPP Release 21 Progress</h3>
    `;
    
    // Add badge if using sample data
    if (dataSource === "sample") {
        html += `
            <div class="sample-data-badge">
                ⚠️ Using sample data - Live 3GPP integration pending
            </div>
        `;
    } else if (dataSource === "cached") {
        html += `
            <div class="cached-data-badge">
                📦 Using cached data from ${progress.last_updated}
            </div>
        `;
    }
    
    html += `
        <div class="progress-bar-container">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress.progress_percentage}%">
                    ${progress.progress_percentage}%
                </div>
            </div>
            <p class="progress-stats">
                ${progress.completed}/${progress.total_work_items} Work Items Completed 
                (${progress.in_progress} in progress, ${progress.postponed} postponed)
            </p>
            <p class="progress-updated">Last updated: ${progress.last_updated}</p>
        </div>
    `;

    // Working Group Breakdown
    if (Object.keys(byGroup).length > 0) {
        html += `
            <div class="wg-breakdown">
                <h4>Progress by Working Group</h4>
                <div class="wg-cards">
        `;

        for (const [wg, stats] of Object.entries(byGroup)) {
            html += `
                <div class="wg-card">
                    <div class="wg-name">${wg}</div>
                    <div class="wg-progress">${stats.progress}%</div>
                    <div class="wg-stats">${stats.completed}/${stats.total} completed</div>
                </div>
            `;
        }

        html += `
                </div>
            </div>
        `;
    }

    // Recent Meetings
    if (meetings.length > 0) {
        html += `
            <div class="meetings-section">
                <h4>Recent 3GPP Meetings</h4>
                <div class="meetings-list">
        `;

        meetings.forEach(meeting => {
            const sentimentIcon = {
                'positive': '✅',
                'negative': '⚠️',
                'mixed': '🔄',
                'neutral': '📋'
            }[meeting.sentiment] || '📋';
            
            // Show sample data indicator on meeting cards
            const meetingDataSource = meeting.data_source || dataSource;
            const sampleBadge = meetingDataSource === "sample" ? 
                '<span class="sample-badge" title="Sample Data">📋</span>' : '';

            html += `
                <div class="meeting-card">
                    <div class="meeting-header">
                        <span class="meeting-wg">${meeting.working_group}</span>
                        <span class="meeting-id">${meeting.meeting_id}</span>
                        <span class="meeting-sentiment">${sentimentIcon}</span>
                        ${sampleBadge}
                    </div>
                    <div class="meeting-meta">
                        ${meeting.date ? `📅 ${meeting.date}` : ''} 
                        ${meeting.location ? `📍 ${meeting.location}` : ''}
                    </div>
            `;

            if (meeting.key_agreements && meeting.key_agreements.length > 0) {
                html += `
                    <div class="meeting-agreements">
                        <strong>Key Agreements:</strong>
                        <ul>
                `;
                meeting.key_agreements.slice(0, 3).forEach(agreement => {
                    html += `<li>${agreement}</li>`;
                });
                html += `
                        </ul>
                    </div>
                `;
            }

            if (meeting.tdoc_references && meeting.tdoc_references.length > 0) {
                html += `
                    <div class="meeting-tdocs">
                        <strong>TDocs:</strong> 
                `;
                meeting.tdoc_references.slice(0, 5).forEach(tdoc => {
                    const tdocUrl = `https://www.3gpp.org/ftp/tsg_ran/WG1_RL1/`;
                    html += `<a href="${tdocUrl}" target="_blank" class="tdoc-link">${tdoc}</a> `;
                });
                html += `
                    </div>
                `;
            }

            html += `</div>`;
        });

        html += `
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
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
function renderTopicFrequencyChart(articles) {
    const container = document.getElementById('topics-chart');
    if (!container) return;

    let topicCounts = {};

    // Collect all emerging concepts
    articles.forEach(article => {
        if (article.ai_insights && article.ai_insights.emerging_concepts) {
            article.ai_insights.emerging_concepts.forEach(topic => {
                topicCounts[topic] = (topicCounts[topic] || 0) + 1;
            });
        }
    });

    const topics = Object.entries(topicCounts)
        .sort((a, b) => b[1] - a[1]) // sort by frequency
        .slice(0, 10); // top 10 topics

    if (topics.length === 0) {
        container.innerHTML = `<p>No topic data available.</p>`;
        return;
    }

    // Find max count for scaling
    const maxCount = Math.max(...topics.map(t => t[1]));

    // Build bar chart
    const html = topics.map(([topic, count]) => {
        const width = (count / maxCount) * 100;

        return `
            <div class="topic-row">
                <span class="topic-label">${topic}</span>
                <div class="topic-bar">
                    <div class="topic-bar-fill" style="width: ${width}%"></div>
                </div>
                <span class="topic-count">${count}</span>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}


function checkQuietMonth(articles) {
    const banner = document.getElementById('quiet-banner');
    if (!banner) return;

    // Default to hidden
    banner.style.display = "none";

    // 1. If no articles were fetched this cycle
    if (articles.length === 0) {
        banner.style.display = "block";

        // Load fallback: last 5 articles from cache (if available)
        fetch('./latest_digest.json')
            .then(r => r.json())
            .then(data => {
                if (data && data.articles) {
                    const fallback = data.articles.slice(-5);
                    renderArticles(fallback);
                }
            })
            .catch(e => console.error("Fallback load error:", e));
        return;
    }

    // 2. Check if last update is older than 30 days
    if (lastUpdateBadge && lastUpdateBadge.textContent) {
        const lastUpdateStr = lastUpdateBadge.textContent.replace("Last Update: ", "").trim();
        const lastUpdate = new Date(lastUpdateStr);
        const now = new Date();
        const diffDays = (now - lastUpdate) / (1000 * 60 * 60 * 24);

        if (!isNaN(diffDays) && diffDays > 30) {
            banner.style.display = "block";
        }
    }
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
                   ${regions.map(r => `<th>${getRegionFlag(r)}<br>${r}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
    `;

    regions.forEach(source => {
        html += `<tr><td class="row-label">${getRegionFlag(source)} ${source}</td>`;
        regions.forEach(target => {
            const value = matrix[source]?.[target] ?? 0;
            html += ` <td class="flow-cell" data-value="${value}" title="Influence from ${source} → ${target}: ${value}"> ${value} </td>`;
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

        // Smooth gradient: dark blue → cyan → white
        const r = Math.floor(0 + intensity * 180);
        const g = Math.floor(60 + intensity * 195);
        const b = Math.floor(120 + intensity * 135);

        cell.style.backgroundColor = `rgba(${r}, ${g}, ${b}, 0.35)`;
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
