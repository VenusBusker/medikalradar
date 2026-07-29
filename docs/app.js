let globalCases = [];
let filteredCases = [];
let visibleCount = 8;
let savedPmids = JSON.parse(localStorage.getItem('cr_saved_cases') || '[]');
let isStudyMode = false;

async function loadCases() {
    try {
        const response = await fetch('cases.json?v=' + new Date().getTime());
        if (!response.ok) throw new Error("cases.json error");
        
        globalCases = await response.json();
        filteredCases = [...globalCases];

        updateSavedCount();
        renderCases();
        renderSidebar();
    } catch (e) {
        console.error("Engine Error:", e);
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
    renderCases();
}

function toggleStudyMode() {
    isStudyMode = !isStudyMode;
    const btn = document.getElementById('study-toggle');
    if (isStudyMode) {
        btn.innerText = "🧠 Active Recall Mode: ON";
        btn.classList.add('active');
    } else {
        btn.innerText = "🧠 Active Recall Mode: OFF";
        btn.classList.remove('active');
    }
    renderCases();
}

// MODÜL: Ayrıcı Tanı (Differential Diagnosis - DDx) Algoritması
function generateDDx(category) {
    if (category === "Cardiology") {
        return ["Acute Coronary Syndrome (STEMI/NSTEMI)", "Aortic Dissection", "Pulmonary Embolism", "Acute Pericarditis"];
    } else if (category === "Neurology") {
        return ["Acute Ischemic Stroke", "Subarachnoid Hemorrhage", "Status Epilepticus", "Central Nervous System Infection"];
    } else if (category === "Surgery") {
        return ["Acute Appendicitis", "Acute Cholecystitis / Cholangitis", "Bowel Perforation", "Acute Pancreatitis"];
    } else {
        return ["Targeted Inflammatory Etiology", "Infectious Pathogen Process", "Acute Metabolic Imbalance"];
    }
}

// MODÜL: İlk Basamak Klinik Tedavi Şeması (First-Line Management)
function generateManagement(category) {
    if (category === "Cardiology") {
        return "12-Lead ECG within 10 mins ➔ High-flow O2 ➔ Serial Troponin tracking ➔ Dual Antiplatelet Therapy (DAPT) consideration.";
    } else if (category === "Neurology") {
        return "Immediate Non-contrast Brain CT scan ➔ NIHSS Score evaluation ➔ Blood Glucose check ➔ Thrombolytic window assessment.";
    } else if (category === "Surgery") {
        return "NPO (Nothing by mouth) ➔ IV Fluid resuscitation ➔ Abdominal/Pelvic CT ➔ Urgent Surgical Consult.";
    } else {
        return "Vital sign stabilization ➔ Targeted Diagnostic Imaging ➔ Targeted Laboratory Panel.";
    }
}

function renderCases() {
    const container = document.getElementById('app');
    container.innerHTML = '';

    const casesToDisplay = filteredCases.slice(0, visibleCount);

    if (casesToDisplay.length === 0) {
        container.innerHTML = '<p style="text-align:center; padding:30px;">No clinical cases found for this view.</p>';
        return;
    }

    casesToDisplay.forEach(c => {
        const card = document.createElement('div');
        card.className = 'case-card';

        const category = c.category || 'General Medicine';
        const isSaved = savedPmids.includes(c.pmid);
        const ddxList = generateDDx(category);
        const mgmtText = generateManagement(category);

        let ddxHtml = ddxList.map(item => `<li>${item}</li>`).join('');

        card.innerHTML = `
            <button class="bookmark-btn ${isSaved ? 'active' : ''}" onclick="toggleBookmark('${c.pmid}')">
                ${isSaved ? '🔖' : '🏷️'}
            </button>

            <div class="card-header">
                <span class="badge badge-cat">📌 ${category}</span>
                <span class="badge badge-hy">⚡ High-Yield Exam Value: 85%+</span>
            </div>

            <h2 class="case-title">${c.title_en || c.title_tr}</h2>

            <div class="patient-history">
                <strong>🩺 Patient Presentation & History:</strong><br>
                ${c.history_en || c.history_tr}
            </div>

            <!-- ACTIVE RECALL / STUDY MODE MANTIĞI -->
            ${isStudyMode ? `
                <button class="study-reveal-btn" onclick="this.nextElementSibling.style.display='block'; this.style.display='none';">
                    🤔 Test Yourself: Click to Reveal Diagnosis & Management Plan
                </button>
                <div class="answer-section" style="display:none;">
            ` : `<div class="answer-section">`}

                <!-- MODÜL 1: Differential Diagnosis (DDx) -->
                <div class="ddx-box">
                    <div class="ddx-title">🧬 Differential Diagnosis (DDx) Tree:</div>
                    <ul class="ddx-list">${ddxHtml}</ul>
                </div>

                <!-- MODÜL 2: First-Line Clinical Action -->
                <div class="mgmt-box">
                    <div class="mgmt-title">💊 First-Line Emergency / Clinical Management:</div>
                    <div>${mgmtText}</div>
                </div>

                <div style="background:#fffde7; border-left:3px solid #fbc02d; padding:10px; font-size:0.88em; color:#574300; margin-top:10px;">
                    <strong>💡 Clinical Summary & Outcome:</strong> ${c.explanation_en || c.explanation_tr}
                </div>

                <!-- ANKI / ACTIVE RECALL OYLAMA BUTONLARI -->
                ${isStudyMode ? `
                    <div class="rating-bar">
                        <button class="rate-btn rate-easy" onclick="alert('Marked as Easy - Review in 5 days')">🟢 Easy</button>
                        <button class="rate-btn rate-med" onclick="alert('Marked as Medium - Review tomorrow')">🟡 Medium</button>
                        <button class="rate-btn rate-hard" onclick="alert('Marked as Hard - Repeat today')">🔴 Hard</button>
                    </div>
                ` : ''}

                <div style="margin-top:12px; text-align:right;">
                    <a href="${c.url}" target="_blank" style="color:#1a73e8; font-size:0.85em; font-weight:bold; text-decoration:none;">PubMed Reference Paper ↗</a>
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
            <button onclick="loadMore()" style="background:#8b0000; color:#fff; border:none; padding:12px 25px; font-family:Georgia, serif; font-size:0.95em; cursor:pointer; border-radius:4px;">
                Load More Cases 👇
            </button>
        `;
        container.appendChild(loadMoreBtn);
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
            <div style="font-size:0.7em; color:#8b0000; font-weight:bold;">📌 ${c.category || 'General'}</div>
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
    else filteredCases = globalCases.filter(c => c.category && c.category.includes(filterType));

    visibleCount = 8;
    renderCases();
}

function loadMore() {
    visibleCount += 8;
    renderCases();
}

document.addEventListener('DOMContentLoaded', loadCases);
