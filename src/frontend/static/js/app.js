/* ==========================================
   OSI News Automation - Results Viewer JS
   ========================================== */

// State
let articles = [];

// DOM Elements
const articlesGrid = document.getElementById('articles-grid');
const articleCount = document.getElementById('article-count');
const lastUpdated = document.getElementById('last-updated');
const loading = document.getElementById('loading');
const statusMessage = document.getElementById('status-message');
const modal = document.getElementById('article-modal');
const modalBody = document.getElementById('modal-body');

// Buttons
const btnScrape = document.getElementById('btn-scrape');
const btnSave = document.getElementById('btn-save');
const btnLoad = document.getElementById('btn-load');
const maxArticlesInput = document.getElementById('max-articles');

// Event Listeners
btnScrape.addEventListener('click', runScraper);
btnSave.addEventListener('click', saveToJson);
btnLoad.addEventListener('click', loadFromJson);

// Close modal on outside click
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Functions
async function runScraper() {
    const maxArticles = parseInt(maxArticlesInput.value) || 10;

    showLoading(true);
    hideStatus();
    setButtonsDisabled(true);

    try {
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_articles: maxArticles })
        });

        const data = await response.json();

        if (data.status === 'success') {
            showStatus(`✅ Successfully scraped ${data.count} articles!`, 'success');
            await loadArticles();
        } else {
            showStatus(`❌ Error: ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
        setButtonsDisabled(false);
    }
}

async function loadArticles() {
    try {
        const response = await fetch('/api/articles');
        const data = await response.json();

        if (data.status === 'success') {
            articles = data.articles;
            renderArticles();
            updateStats();
        }
    } catch (error) {
        console.error('Failed to load articles:', error);
    }
}

async function saveToJson() {
    try {
        const response = await fetch('/api/save', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            showStatus(`✅ ${data.message}`, 'success');
        } else {
            showStatus(`❌ ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    }
}

async function loadFromJson() {
    showLoading(true);

    try {
        const response = await fetch('/api/load', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            showStatus(`✅ ${data.message}`, 'success');
            await loadArticles();
        } else {
            showStatus(`❌ ${data.message}`, 'error');
        }
    } catch (error) {
        showStatus(`❌ Error: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

function renderArticles() {
    if (articles.length === 0) {
        articlesGrid.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <p>No articles yet. Click "Run Scraper" to fetch news articles.</p>
            </div>
        `;
        return;
    }

    articlesGrid.innerHTML = articles.map((article, index) => {
        const preview = (article.story || '').substring(0, 180) + '...';
        const wordCount = (article.story || '').split(/\s+/).length;
        const image = article.top_image || article.image_url || '';
        const category = detectCategory(article);
        const readTime = calculateReadTime(wordCount);
        const formattedDate = formatDate(article.date || article.publish_date);

        return `
            <div class="article-card" onclick="openArticle(${index})">
                <div class="article-image-container">
                    ${image ? `<img src="${image}" alt="${escapeHtml(article.heading || '')}" class="article-image" onerror="this.parentElement.style.height='120px'">` : ''}
                    <div class="article-image-overlay">
                        <span class="article-category" style="background: ${category.color};">${category.name}</span>
                    </div>
                </div>
                <div class="article-content">
                    <span class="article-source">${article.source_name || 'Unknown Source'}</span>
                    <h3 class="article-heading">${escapeHtml(article.heading || 'No Title')}</h3>
                    <p class="article-preview">${escapeHtml(preview)}</p>
                    <div class="article-meta">
                        <div class="article-meta-item article-date">
                            <span>📅</span>
                            <span>${formattedDate}</span>
                        </div>
                        <div class="article-meta-item article-read-time">
                            <span>⏱️</span>
                            <span>${readTime}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function openArticle(index) {
    const article = articles[index];
    if (!article) return;

    const storyHtml = (article.story || '').replace(/## /g, '<h2>').replace(/\n\n/g, '</p><p>');

    modalBody.innerHTML = `
        <h2 class="modal-heading">${escapeHtml(article.heading || 'No Title')}</h2>
        <div class="modal-meta">
            <span>📰 ${article.source_name || 'Unknown'}</span>
            <span>📍 ${article.location || 'Unknown'}</span>
            <span>🌐 ${article.language || 'en'}</span>
            <span>📊 ${(article.story || '').split(/\s+/).length} words</span>
        </div>
        <div class="modal-story">
            <p>${storyHtml}</p>
        </div>
        <div class="modal-json">
            <h3 style="margin-bottom: 12px; color: #94a3b8;">JSON Format:</h3>
            <pre>${escapeHtml(JSON.stringify(article, null, 2))}</pre>
        </div>
    `;

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function updateStats() {
    articleCount.textContent = `${articles.length} Articles`;
    lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}

function showLoading(show) {
    loading.classList.toggle('hidden', !show);
}

function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');

    setTimeout(() => {
        statusMessage.classList.add('hidden');
    }, 5000);
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}

function setButtonsDisabled(disabled) {
    btnScrape.disabled = disabled;
    btnSave.disabled = disabled;
    btnLoad.disabled = disabled;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Category detection from heading/content
function detectCategory(article) {
    const text = `${article.heading} ${article.story}`.toLowerCase();

    if (text.match(/\b(election|government|parliament|minister|politics|president|prime minister|congress|senate)\b/)) {
        return { name: 'Politics', color: 'var(--category-politics)' };
    }
    if (text.match(/\b(country|international|foreign|global|war|peace|diplomacy|treaty)\b/)) {
        return { name: 'World', color: 'var(--category-world)' };
    }
    if (text.match(/\b(tech|technology|ai|software|hardware|cyber|digital|innovation|startup)\b/)) {
        return { name: 'Technology', color: 'var(--category-technology)' };
    }
    if (text.match(/\b(business|economy|market|stock|company|corporate|trade|finance)\b/)) {
        return { name: 'Business', color: 'var(--category-business)' };
    }
    if (text.match(/\b(sport|football|cricket|tennis|olympics|championship|athlete)\b/)) {
        return { name: 'Sports', color: 'var(--category-sports)' };
    }
    if (text.match(/\b(entertainment|movie|music|celebrity|film|actor|actress|hollywood)\b/)) {
        return { name: 'Entertainment', color: 'var(--category-entertainment)' };
    }
    if (text.match(/\b(health|medical|disease|hospital|doctor|patient|medicine|covid)\b/)) {
        return { name: 'Health', color: 'var(--category-health)' };
    }
    if (text.match(/\b(science|research|study|scientist|discovery|space|climate)\b/)) {
        return { name: 'Science', color: 'var(--category-science)' };
    }

    return { name: 'News', color: 'var(--category-default)' };
}

// Format date to human-readable format
function formatDate(dateString) {
    if (!dateString) return 'Recent';

    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        // Format as "Jan 24, 2026"
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch (e) {
        return 'Recent';
    }
}

// Calculate read time based on word count
function calculateReadTime(wordCount) {
    const wordsPerMinute = 200;
    const minutes = Math.ceil(wordCount / wordsPerMinute);
    return `${minutes} min read`;
}

// Initial load
loadArticles();
