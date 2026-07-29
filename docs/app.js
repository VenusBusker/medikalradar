let globalCases = [];
let filteredCases = [];
let visibleCount = 10;

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

// Spot Bilgi Vurguları (Klinik Terim İşleyici)
function highlightMedicalTerms(text) {
    if (!text) return "";
    const terms = {
        "ECG": "Electrocardiogram — measures heart electrical activity",
        "EKG": "Electrocardiogram — measures heart electrical activity",
        "Troponin": "Cardiac biomarker elevated during myocardial injury",
        "MRI": "Magnetic Resonance Imaging — high resolution soft tissue scan",
        "CT": "Computed Tomography scan",
        "Areflexia": "Absence of deep tendon reflexes",
        "STEMI": "ST-Elevation Myocardial Infarction (Acute Heart Attack)",
        "Laparoscopy": "Minimally invasive abdominal surgery procedure"
    };

    let processedText = text;
    for (let key in terms) {
        const regex = new RegExp(`\\b(${key})\\b`, 'gi');
        processedText = processedText.replace(regex, `<span class="spot-term" title="${terms[key]}">$1</span>`);
    }
    return processedText;
}

// Sol Taraf: İnteraktif Vaka & Guess the Diagnosis Kartları
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
        
        const highlightedHistory = highlightMedicalTerms(c.history_en || c.history_tr);
        const highlightedOutcome = highlightMedicalTerms(c.explanation_en || c.explanation_tr);

        card.innerHTML = `
            <div class="card-header">
                <span class="badge badge-cat">📌 ${category}</span>
                <span class="badge ${triageBadgeClass}">${triage} Acuity</span>
            </div>
            <h2 class="case-title">${c.title_en || c.title_tr}</h2>
            <div class="patient-history">
                <strong>🩺 Clinical Presentation & History:</strong><br>
                ${highlightedHistory}
            </div>
            
            <!-- Guess the Diagnosis & Flip Action -->
            <button class="reveal-btn" onclick="toggleDiagnosis('diag-${c.pmid}', this)">
                🤔 Reveal Diagnosis & Key Clinical Takeaways
            </button>
            
            <div id="diag-${c.pmid}" class="diagnosis-box">
                <div class="diag-title">💡 Diagnostic Outcome & Key Takeaways:</div>
                <p>${highlightedOutcome}</p>
                <div style="margin-top:12px; text-align:right;">
                    <a href="${c.url}" target="_blank" style="color:#1a73e8; font-weight:bold; font-size:0.88em; text-decoration:none;">Read Full PubMed Case Report ↗</a>
                </div>
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
                Load More Interactive Cases 👇
            </button>
        `;
        container.appendChild(loadMoreBtn);
    }
}

// Sağ Taraf: Literatür Paneli
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

// "Guess the Diagnosis" Kutusu Aç/Kapa
function toggleDiagnosis(id, btnElement) {
    const box = document.getElementById(id);
    if (box.style.display === 'block') {
        box.style.display = 'none';
        btnElement.innerText = "🤔 Reveal Diagnosis & Key Clinical Takeaways";
        btnElement.style.background = "#8b0000";
    } else {
        box.style.display = 'block';
        btnElement.innerText = "🔒 Hide Diagnosis";
        btnElement.style.background = "#444";
    }
}

// İnteraktif Filtreleme Fonksiyonu
function filterCases(filterType) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    if (filterType === 'ALL') {
        filteredCases = [...globalCases];
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
