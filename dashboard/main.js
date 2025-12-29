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

        lastUpdateBadge.textContent = `Last Update: ${data.date}`;

        populateSourceFilter(allArticles);
        renderArticles(allArticles);
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
