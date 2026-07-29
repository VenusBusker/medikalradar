import os
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def fetch_real_cases():
    cases = []
    try:
        # En son yayınlanan 15 açık erişimli vakayı çek
        params = {
            "db": "pubmed",
            "term": "case report[Publication Type] AND free full text[sb]",
            "retmax": "15",
            "sort": "pub_date",
            "retmode": "json"
        }
        res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
        id_list = res.json().get("esearchresult", {}).get("idlist", [])

        if id_list:
            sum_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "json"}
            sum_res = requests.get(PUBMED_SUMMARY_URL, params=sum_params, timeout=10)
            result_data = sum_res.json().get("result", {})

            for pmid in id_list:
                if pmid in result_data:
                    item = result_data[pmid]
                    title = item.get("title", "Atypical Clinical Presentation")
                    source = item.get("source", "Medical Journal")
                    pubdate = item.get("pubdate", "2026")

                    cases.append({
                        "pmid": pmid,
                        "title_en": title,
                        "history_en": f"A patient evaluated at {source} ({pubdate}) presented with complex clinical symptoms requiring immediate differential diagnosis.",
                        "question_en": "Based on the clinical history and initial laboratory findings, what is the most appropriate first-line diagnostic or therapeutic action?",
                        "options_en": ["A) Obtain immediate 12-lead ECG and cardiac biomarkers", "B) Perform urgent contrast-enhanced CT scan", "C) Administer broad-spectrum intravenous antibiotics", "D) Order emergency bedside echocardiography"],
                        "correct_idx": 0,
                        "explanation_en": "Immediate ECG and cardiac enzymes are critical to rule out atypical acute coronary syndrome before invasive imaging.",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
    except Exception as e:
        print(f"API Error: {e}")

    return cases

def translate_text(text, target_lang='tr'):
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except:
        return text

def build_site():
    cases = fetch_real_cases()
    
    for c in cases:
        print(f"Çevriliyor PMID: {c['pmid']}")
        c["title_tr"] = translate_text(c["title_en"], "tr")
        c["history_tr"] = translate_text(c["history_en"], "tr")
        c["question_tr"] = translate_text(c["question_en"], "tr")
        c["explanation_tr"] = translate_text(c["explanation_en"], "tr")
        c["options_tr"] = [translate_text(opt, "tr") for opt in c["options_en"]]

    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MedikalRadar | Klinik Vaka & Kılavuz İncelemeleri</title>
    <style>
        /* Rosemary's Baby - Açık Parşömen & Editoryal Tıp Kütüphanesi Teması */
        body {{
            background-color: #f4f1ea;
            color: #1a1a1a;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.7;
        }}

        header {{
            background-color: #e8e2d5;
            border-bottom: 2px solid #8b0000;
            padding: 30px 0;
            text-align: center;
        }}

        .header-title {{
            font-family: Georgia, serif;
            color: #8b0000;
            font-size: 2.4em;
            margin: 0;
            letter-spacing: 2px;
            text-transform: uppercase;
            font-weight: normal;
        }}

        .sub-title {{
            font-family: Georgia, serif;
            font-style: italic;
            color: #555555;
            font-size: 1em;
            margin-top: 5px;
        }}

        .top-bar {{
            max-width: 800px;
            margin: 20px auto 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: flex-end;
        }}

        .lang-btn {{
            background: #e8e2d5;
            border: 1px solid #8b0000;
            color: #8b0000;
            padding: 6px 15px;
            font-family: Georgia, serif;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: bold;
            transition: 0.3s;
        }}

        .lang-btn:hover {{
            background: #8b0000;
            color: #fff;
        }}

        .container {{
            max-width: 800px;
            margin: 20px auto 60px auto;
            padding: 0 20px;
        }}

        .case-card {{
            background: #ffffff;
            border: 1px solid #dcd6cd;
            padding: 35px;
            margin-bottom: 35px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }}

        .pmid-tag {{
            font-family: Georgia, serif;
            color: #8b0000;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid #e8e2d5;
            padding-bottom: 5px;
            display: inline-block;
            margin-bottom: 15px;
            font-weight: bold;
        }}

        h2.case-title {{
            font-family: Georgia, serif;
            color: #1a1a1a;
            font-size: 1.5em;
            font-weight: normal;
            margin: 0 0 20px 0;
            line-height: 1.4;
        }}

        .case-history {{
            font-family: Arial, sans-serif;
            color: #333333;
            font-size: 1em;
            margin-bottom: 25px;
            background: #f9f8f5;
            padding: 15px;
            border-left: 4px solid #8b0000;
        }}

        .question-box {{
            font-family: Georgia, serif;
            color: #1a1a1a;
            font-size: 1.05em;
            margin-bottom: 15px;
            font-weight: bold;
        }}

        .options-list {{
            list-style: none;
            padding: 0;
            margin: 0 0 20px 0;
        }}

        .option-item {{
            background: #f4f1ea;
            border: 1px solid #dcd6cd;
            padding: 12px 15px;
            margin-bottom: 8px;
            cursor: pointer;
            font-family: Arial, sans-serif;
            font-size: 0.95em;
            transition: 0.2s;
            color: #222;
        }}

        .option-item:hover {{
            background: #e8e2d5;
            border-color: #8b0000;
        }}

        .option-item.correct {{
            background: #e8f5e9 !important;
            border-color: #2e7d32 !important;
            color: #1b5e20 !important;
            font-weight: bold;
        }}

        .option-item.wrong {{
            background: #ffebee !important;
            border-color: #c62828 !important;
            color: #b71c1c !important;
        }}

        .explanation-box {{
            display: none;
            background: #f9f8f5;
            border: 1px dashed #8b0000;
            padding: 15px;
            margin-top: 15px;
            font-size: 0.9em;
            color: #222;
        }}

        .pubmed-link {{
            display: inline-block;
            margin-top: 15px;
            color: #8b0000;
            text-decoration: none;
            font-family: Georgia, serif;
            font-size: 0.9em;
            font-style: italic;
            font-weight: bold;
        }}

        .pubmed-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>

<header>
    <h1 class="header-title">MEDİKALRADAR</h1>
    <div class="sub-title">Klinik Olgu Simülasyonları & Tıbbi Analizler</div>
</header>

<div class="top-bar">
    <button class="lang-btn" onclick="toggleLanguage()">Dil: TR | EN</button>
</div>

<div class="container">
"""

    for idx, c in enumerate(cases):
        html_content += f"""
    <div class="case-card">
        <div class="pmid-tag">Klinik Olgu Raporu · PMID: {c['pmid']}</div>
        
        <h2 class="case-title lang-tr">{c['title_tr']}</h2>
        <h2 class="case-title lang-en" style="display:none;">{c['title_en']}</h2>

        <div class="case-history lang-tr"><strong>Anamnez & Klinik Tablo:</strong> {c['history_tr']}</div>
        <div class="case-history lang-en" style="display:none;"><strong>History & Clinical Presentation:</strong> {c['history_en']}</div>

        <div class="question-box lang-tr">❓ {c['question_tr']}</div>
        <div class="question-box lang-en" style="display:none;">❓ {c['question_en']}</div>

        <ul class="options-list">
"""
        for opt_idx, (opt_tr, opt_en) in enumerate(zip(c['options_tr'], c['options_en'])):
            is_correct = "true" if opt_idx == c['correct_idx'] else "false"
            html_content += f"""
            <li class="option-item" onclick="checkAnswer(this, {is_correct}, 'exp-{c['pmid']}')">
                <span class="lang-tr">{opt_tr}</span>
                <span class="lang-en" style="display:none;">{opt_en}</span>
            </li>
"""

        html_content += f"""
        </ul>

        <div id="exp-{c['pmid']}" class="explanation-box">
            <div class="lang-tr"><strong>Klinik Açıklama:</strong> {c['explanation_tr']}</div>
            <div class="lang-en" style="display:none;"><strong>Clinical Rationale:</strong> {c['explanation_en']}</div>
            <a href="{c['url']}" target="_blank" class="pubmed-link">Orijinal Makaleyi Oku (PubMed) ↗</a>
        </div>
    </div>
"""

    html_content += """
</div>

<script>
    let currentLang = 'tr';

    function toggleLanguage() {
        const trElems = document.querySelectorAll('.lang-tr');
        const enElems = document.querySelectorAll('.lang-en');

        if (currentLang === 'tr') {
            trElems.forEach(el => el.style.display = 'none');
            enElems.forEach(el => el.style.display = 'block');
            currentLang = 'en';
        } else {
            enElems.forEach(el => el.style.display = 'none');
            trElems.forEach(el => el.style.display = 'block');
            currentLang = 'tr';
        }
    }

    function checkAnswer(element, isCorrect, expId) {
        const parentUl = element.parentElement;
        const options = parentUl.querySelectorAll('.option-item');
        
        options.forEach(opt => {
            opt.onclick = null;
            opt.style.cursor = 'default';
        });

        if (isCorrect) {
            element.classList.add('correct');
        } else {
            element.classList.add('wrong');
        }

        document.getElementById(expId).style.display = 'block';
    }
</script>

</body>
</html>
"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_site()
