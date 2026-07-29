let globalCases = [];
let filteredCases = [];
let visibleCount = 9; // Grid düzenine uygun (1 Manşet + 8 Izgara Kartı)
let savedPmids = JSON.parse(localStorage.getItem('cr_saved_cases') || '[]');

async function loadCases() {
    try {
        const response = await fetch('cases.json?v=' + new Date().getTime());
        if (!response.ok) throw new Error("cases.json error");
        
        globalCases = await response.json();
        filteredCases = [...globalCases];

        updateSavedCount();
        renderPortal();
        renderSidebar();
    } catch (e) {
        console.error("Portal Error:", e);
    }
}

function updateSavedCount() {
    const el = document.getElementById('saved-count');
    if (el) el.innerText = savedPmids.length;
}

function toggleBookmark(pmid) {
    if (savedPmids.includes(pmid)) {
        savedPmids = savedPmids.filter(id => id !== pmid);
    } else {
        savedPmids.push(pmid);
    }
    localStorage.setItem('cr_saved_cases', JSON.stringify(savedPmids));
    updateSavedCount();
    renderPortal();
}

function generatePearl(text) {
    if (!text) return "Key clinical outcome details in full report.";
    const parts = text.split('. ');
    return parts[0] + (parts[0].endsWith('.') ? '' : '.');
}

function renderPortal() {
    const heroArea = document.getElementById('hero-area');
    const gridArea = document.getElementById('grid-area');
    const pageArea = document.getElementById('pagination-area');

    heroArea.innerHTML = '';
    gridArea.innerHTML = '';
    pageArea.innerHTML = '';

    if (filteredCases.length === 0) {
        gridArea.innerHTML = '<p style="grid-column: 1/-1; text-align:center; padding:30px;">No literature found for this filter.</p>';
        return;
    }

    // 1. MANŞET VAKA (HERO FEATURED CASE) - Listenin ilk elemanı
    const heroCase = filteredCases[0];
    const heroSaved = savedPmids.includes(heroCase.pmid);
    heroArea.innerHTML = `
        <div class="hero-card">
            <button class="bookmark-btn ${heroSaved ? 'active' : ''}" onclick="toggleBookmark('${heroCase.pmid}')">
                ${heroSaved ? '🔖' : '🏷️'}
            </button>
            <span class="hero-badge">⭐ FEATURED CASE · ${heroCase.category || 'General Medicine'}</span>
            <h1 class="hero-title">${heroCase.title_en || heroCase.title_tr}</h1>
            <p class="hero-snippet">${heroCase.history_en || heroCase.history_tr}</p>
            <div style="background:#fffde7; border-left:3px solid #fbc02d; padding:10px 12px; font-size:0.88em; color:#574300; margin-bottom:12px;">
                <strong>⚡ High-Yield Pearl:</strong> ${generatePearl(heroCase.explanation_en || heroCase.explanation_tr)}
            </div>
            <a href="${heroCase.url}" target="_blank" style="color:#8b0000; font-weight:bold; font-size:0.9em; text-decoration:none;">Read Full Case Report ↗</a>
        </div>
    `;

    // 2. 2-COLUMN NEWS GRID (Kalan Vakalar)
    const gridCases = filteredCases.slice(1, visibleCount);

    gridCases.forEach(c => {
        const isSaved = savedPmids.includes(c.pmid);
        const card = document.createElement('div');
        card.className = 'grid-card';

        const category = c.category || 'General';
        const triage = c.triage || 'Yellow';
        const triageBadgeClass = triage === 'Red' ? 'badge-red' : 'badge-yellow';

        card.innerHTML = `
            <button class="bookmark-btn ${isSaved ? 'active' : ''}" onclick="toggleBookmark('${c.pmid}')">
                ${isSaved ? '🔖' : '🏷️'}
            </button>
            <div>
                <div class="card-meta">
                    <span class="badge badge-cat">${category}</span>
                    <span class="badge ${triageBadgeClass}">${triage}</span>
                </div>
                <h3 class="grid-title">${c.title_en || c.title_tr}</h3>
                <p class="grid-snippet">${c.history_en || c.history_tr}</p>
            </div>
            <div>
                <div class="grid-pearl">
                    <strong>⚡ Pearl:</strong> ${generatePearl(c.explanation_en || c.explanation_tr)}
                </div>
                <div style="margin-top:10px; text-align:right;">
                    <a href="${c.url}" target="_blank" style="color:#1a73e8; font-size:0.8em; font-weight:bold; text-decoration:none;">Paper ↗</a>
                </div>
            </div>
        `;
        gridArea.appendChild(card);
    });

    // Daha Fazla Yükle Butonu
    if (visibleCount < filteredCases.length) {
        pageArea.innerHTML = `
            <button onclick="loadMore()" style="background:#8b0000; color:#fff; border:none; padding:10px 22px; font-family:Georgia, serif; font-size:0.9em; cursor:pointer; border-radius:4px;">
                Load More Articles 👇
            </button>
        `;
    }
}

function renderSidebar() {
    const container = document.getElementById('sidebar-scroll');
    const countTag = document.getElementById('article-count');
    if (!container) return;

    container.innerHTML = '';
    countTag.innerText = globalCases.length;

    globalCases.forEach(c => {
        const item = document.createElement('a');
        item.className = 'sidebar-item';
        item.href = `article.html?id=${c.pmid}`;
        item.target = '_blank';

        item.innerHTML = `
            <div class="sidebar-item-tag">📌 ${c.category || 'General Medicine'}</div>
            <div class="sidebar-item-title">${c.title_en || c.title_tr}</div>
        `;
        container.appendChild(item);
    });
}

function filterCases(filterType) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    if (window.event && window.event.target) window.event.target.classList.add('active');

    if (filterType === 'ALL') filteredCases = [...globalCases];
    else if (filterType === 'BOOKMARKS') filteredCases = globalCases.filter(c => savedPmids.includes(c.pmid));
    else if (filterType === 'Red') filteredCases = globalCases.filter(c => c.triage === 'Red');
    else filteredCases = globalCases.filter(c => c.category && c.category.includes(filterType));

    visibleCount = 9;
    renderPortal();
}

function loadMore() {
    visibleCount += 8;
    renderPortal();
}

document.addEventListener('DOMContentLoaded', loadCases);
