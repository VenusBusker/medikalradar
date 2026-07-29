let currentLang = 'tr';
let globalCases = [];
let visibleCount = 10; // Tek seferde ekrana basılacak vaka sayısı (Kasmayı önler)

async function loadCases() {
    const appContainer = document.getElementById('app');
    try {
        const response = await fetch('cases.json?v=' + new Date().getTime());
        
        if (!response.ok) {
            throw new Error("cases.json dosyası okunamadı.");
        }

        globalCases = await response.json();
        
        if (!globalCases || globalCases.length === 0) {
            appContainer.innerHTML = '<p style="text-align:center; padding:20px;">Henüz yüklü vaka bulunmuyor.</p>';
            return;
        }

        renderCases();
    } catch (e) {
        console.error("Yükleme Hatası:", e);
        appContainer.innerHTML = `
            <div style="text-align:center; padding:30px; background:#fff; border:1px solid #dcd6cd;">
                <h3 style="color:#8b0000; font-family:Georgia, serif;">Vakalar Yükleniyor...</h3>
                <p style="font-size:0.9em; color:#555;">Lütfen sayfayı yenileyin.</p>
            </div>
        `;
    }
}

function renderCases() {
    const container = document.getElementById('app');
    container.innerHTML = '';

    // Sadece belirlenen miktardaki vakayı ekrana bas (Pagination)
    const casesToDisplay = globalCases.slice(0, visibleCount);

    casesToDisplay.forEach(c => {
        const card = document.createElement('div');
        card.className = 'case-card';

        let optionsHtml = '';
        const opts = currentLang === 'tr' ? c.options_tr : c.options_en;
        opts.forEach((opt, idx) => {
            const isCorrect = idx === c.correct_idx;
            optionsHtml += `<li class="option-item" onclick="checkAnswer(this, ${isCorrect}, 'exp-${c.pmid}')">${opt}</li>`;
        });

        card.innerHTML = `
            <div class="pmid-tag">Klinik Olgu Raporu · PMID: ${c.pmid} · ${c.published_date || ''}</div>
            <h2 class="case-title">${currentLang === 'tr' ? c.title_tr : c.title_en}</h2>
            <div class="case-history"><strong>${currentLang === 'tr' ? 'Anamnez & Klinik Tablo:' : 'History & Presentation:'}</strong> ${currentLang === 'tr' ? c.history_tr : c.history_en} ...</div>
            <div class="question-box">❓ ${currentLang === 'tr' ? c.question_tr : c.question_en}</div>
            <ul class="options-list">${optionsHtml}</ul>
            <div id="exp-${c.pmid}" class="explanation-box">
                <div><strong>${currentLang === 'tr' ? 'Klinik Seyir & Sonuç:' : 'Clinical Outcome:'}</strong> ${currentLang === 'tr' ? c.explanation_tr : c.explanation_tr}</div>
                <a href="${c.url}" target="_blank" class="pubmed-link">${currentLang === 'tr' ? 'Orijinal Yayın (PubMed) ↗' : 'Read Paper (PubMed) ↗'}</a>
            </div>
        `;
        container.appendChild(card);
    });

    // Eğer gösterilmeyen daha fazla vaka varsa "Daha Fazla Yükle" Butonu Ekle
    if (visibleCount < globalCases.length) {
        const loadMoreBtn = document.createElement('div');
        loadMoreBtn.style.textAlign = 'center';
        loadMoreBtn.style.marginTop = '30px';
        loadMoreBtn.innerHTML = `
            <button onclick="loadMoreCases()" style="background:#8b0000; color:#fff; border:none; padding:12px 25px; font-family:Georgia, serif; font-size:1em; cursor:pointer; transition:0.3s;">
                ${currentLang === 'tr' ? 'Daha Fazla Vaka Yükle 👇' : 'Load More Cases 👇'}
            </button>
        `;
        container.appendChild(loadMoreBtn);
    }
}

function loadMoreCases() {
    visibleCount += 10; // Her tıkta 10 vaka daha açar
    renderCases();
}

function toggleLanguage() {
    currentLang = currentLang === 'tr' ? 'en' : 'tr';
    renderCases();
}

function checkAnswer(element, isCorrect, expId) {
    const parentUl = element.parentElement;
    const options = parentUl.querySelectorAll('.option-item');
    options.forEach(opt => { opt.onclick = null; opt.style.cursor = 'default'; });

    if (isCorrect) element.classList.add('correct');
    else element.classList.add('wrong');

    document.getElementById(expId).style.display = 'block';
}

document.addEventListener('DOMContentLoaded', loadCases);
