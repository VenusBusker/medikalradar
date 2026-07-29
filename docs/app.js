let globalCases = [];
let filteredCases = [];
let visibleCount = 10;

// Genişletilmiş Tıbbi Terim & Kısaltma Sözlüğü (Hover yapınca çıkacak tanımlar)
const MEDICAL_DICTIONARY = {
    "ECG": "Electrocardiogram — Measures electrical activity of the heart.",
    "EKG": "Electrocardiogram — Measures electrical activity of the heart.",
    "Troponin": "Cardiac biomarker elevated during myocardial injury or infarction.",
    "MRI": "Magnetic Resonance Imaging — High resolution non-radiation soft tissue scan.",
    "CT": "Computed Tomography scan — Cross-sectional X-ray imaging.",
    "STEMI": "ST-Elevation Myocardial Infarction — Acute severe heart attack requiring urgent reperfusion.",
    "Areflexia": "Absence of neurological deep tendon reflexes.",
    "Tachycardia": "Abnormally rapid heart rate (usually over 100 bpm in adults).",
    "Bradycardia": "Abnormally slow heart rate (usually below 60 bpm).",
    "Dyspnea": "Shortness of breath or difficult/labored breathing.",
    "Laparoscopy": "Minimally invasive surgical procedure inside the abdomen.",
    "Hypokalemia": "Abnormally low potassium concentration in the blood.",
    "Hyperkalemia": "Abnormally high potassium level in the blood.",
    "Anaphylaxis": "Severe, potentially life-threatening systemic allergic reaction.",
    "Pneumothorax": "Abnormal collection of air in the pleural space that causes lung collapse.",
    "Ascites": "Abnormal accumulation of fluid within the peritoneal cavity.",
    "Biopsy": "Removal of tissue sample for diagnostic microscopic examination."
};

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

// Tıbbi Metinlerin İçindeki Terimleri Otomatik Tespit Edip Tooltip Ekler
function highlightMedicalTerms(text) {
    if (!text) return "";

    let processedText = text;
    for (let key in MEDICAL_DICTIONARY) {
        // Tam kelime eşleşmesi için Regex kullanımı
        const regex = new RegExp(`\\b(${key})\\b`, 'gi');
        processedText = processedText.replace(regex, `<span class="spot-term" title="${MEDICAL_DICTIONARY[key]}">$1</span>`);
    }
    return processedText;
}

// Sol Taraf: Açık, Net Vaka Kartları (Butonsuz)
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
            
            <!-- Doğrudan Görünür Düzgün Sonuç Kutusu (Reveal Butonu Kaldırıldı) -->
            <div class="diagnosis-box" style="display:block;">
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
                Load More Cases 👇
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

// İnteraktif Branş / Aciliyet Filtreleme
function filterCases(filterType) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    if (event && event.target) {
        event.target.classList.add('active');
    }

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
