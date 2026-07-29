let globalCases = [];
let filteredCases = [];
let visibleCount = 10;
let savedPmids = JSON.parse(localStorage.getItem('cr_saved_cases') || '[]');

async function loadCases() {
    const appContainer = document.getElementById('app');
    try {
        const response = await fetch('cases.json?v=' + new Date().getTime());
        
        if (!response.ok) {
            throw new Error("cases.json could not be loaded.");
        }

        globalCases = await response.json();
        filteredCases = [...globalCases];
        
        if (!globalCases || globalCases.length === 0) {
            appContainer.innerHTML = '<p style="text-align:center; padding:20px;">No cases found in archive.</p>';
            return;
        }

        updateSavedCount();
        renderCases();
        renderSidebarArticles();
    } catch (e) {
        console.error("Load Error:", e);
        appContainer.innerHTML = `
            <div style="text-align:center; padding:30px; background:#fff; border:1px solid #dcd6cd;">
                <h3 style="color:#8b0000; font-family:Georgia, serif;">Loading Cases...</h3>
                <p style="font-size:0.9em; color:#555;">Please refresh the page.</p>
            </div>
        `;
    }
}

// Favori Sayısını Günceller
function updateSavedCount() {
    const countSpan = document.getElementById('saved-count');
    if (countSpan) countSpan.innerText = savedPmids.length;
}

// Favori Ekle / Çıkar
function toggleBookmark(pmid) {
    if (savedPmids.includes(pmid)) {
        savedPmids = savedPmids.filter(id => id !== pmid);
    } else {
        savedPmids.push(pmid);
    }
    localStorage.setItem('cr_saved_cases', JSON.stringify(savedPmids));
    updateSavedCount();
    renderCases();
}

// High-Yield Pearl Çıkarıcı (Metindeki en vurucu ilk cümleyi öne çıkarır)
function generateClinicalPearl(outcomeText) {
    if (!outcomeText) return "Key clinical diagnosis and management strategy outlined in full paper.";
    const sentences = outcomeText.split('. ');
    return sentences[0] + (sentences[0].endsWith('.') ? '' : '.');
}

function renderCases() {
    const container = document.getElementById('app');
    container.innerHTML = '';

    const casesToDisplay = filteredCases.slice(0, visibleCount);

    if (casesToDisplay.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:30px;">No cases match the selected filter.</p>';
        return;
    }

    casesToDisplay.forEach(c => {
        const card = document.createElement('div');
        card.className = 'interactive-card';

        const category = c.category || 'General Medicine';
        const triage = c.triage || 'Yellow';
        const triageBadgeClass = triage === 'Red' ? 'badge-red' : (triage === 'Green' ? 'badge-green' : 'badge-yellow');
        const isSaved = savedPmids.includes(c.pmid);

        const pearlText = generateClinicalPearl(c.explanation_en || c.explanation_tr);

        card.innerHTML = `
            <button class="bookmark-btn ${isSaved ? 'active' : ''}" onclick="toggleBookmark('${c.pmid}')" title="Save to Personal Journal">
                ${isSaved ? '🔖' : '🏷️'}
            </button>
            <div class="card-header">
                <span class="badge badge-cat">📌 ${category}</span>
                <span class="badge ${triageBadgeClass}">${triage} Acuity</span>
            </div>
            <h2 class="case-title">${c.title_en || c.title_tr}</h2>
            
            <div class="patient-history">
                <strong>🩺 Clinical Presentation & History:</strong><br>
                ${c.history_en || c.history_tr}
            </div>
            
            <div class="diagnosis-box">
                <div class="diag-title">💡 Diagnostic Outcome & Management:</div>
                <p>${c.explanation_en || c.explanation_tr}</p>
            </div>

            <!-- 🔥 HIGH-YIELD CLINICAL PEARL KUTUSU -->
            <div class="pearl-box">
                <div class="pearl-title">⚡ High-Yield Clinical Pearl</div>
                <div>${pearlText}</div>
            </div>

            <div style="margin-top:12px; text-align:right;">
                <a href="${c.url}" target="_blank" style="color:#1a73e8; font-weight:bold; font-size:0.85em; text-decoration:none;">Read Full PubMed Paper ↗</a>
            </div>
        `;
        container.appendChild(card);
    });

    if (visibleCount < filteredCases.length) {
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.style.textAlign = 'center';
        loadMoreBtn.style.marginTop = '25px';
        loadMoreBtn.innerHTML = `
            <button onclick="loadMoreCases()" style="background:#8b0000; color:#fff; border:none; padding:12px 25px; font-family:Georgia, serif; font-size:0.95em; cursor:pointer; border-radius:4px;">
                Load More Cases 👇
            </button>
        `;
        container.appendChild(loadMoreBtn);
    }
}

function renderSidebarArticles() {
    const listContainer = document.getElementById('articles-list');
    const countTag = document.getElementById('article-count');
    
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    countTag.innerText = `${globalCases.length} Papers`;

    globalCases.forEach(c => {
        const articleCard = document.createElement('a');
        articleCard.className = 'article-card';
        articleCard.href = `article.html?id=${c.pmid}`;
        articleCard.target = '_blank';

        articleCard.innerHTML = `
            <div class="article-card-tag">📄 ${c.category || 'General Medicine'}</div>
            <div class="article-card-title">${c.title_en || c.title_tr}</div>
        `;

        listContainer.appendChild(articleCard);
    });
}

function filterCases(filterType) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    if (window.event && window.event.target) {
        window.event.target.classList.add('active');
    }

    if (filterType === 'ALL') {
        filteredCases = [...globalCases];
    } else if (filterType === 'BOOKMARKS') {
        filteredCases = globalCases.filter(c => savedPmids.includes(c.pmid));
    } else if (filterType === 'Red') {
        filteredCases = globalCases.filter(c => c.triage === 'Red');
    } else {
        filteredCases = globalCases.filter(c => (c.category && c.category.includes(filterType)));
    }
    visibleCount = 10;
    renderCases();
}

function loadMoreCases() {
    visibleCount += 10;
    renderCases();
}

document.addEventListener('DOMContentLoaded', loadCases);
