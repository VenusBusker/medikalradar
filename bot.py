import os
import json
import random
import requests
from deep_translator import GoogleTranslator

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
HISTORY_FILE = "docs/history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(history_set), f, ensure_ascii=False, indent=2)

def translate_safe(text, target_lang='tr'):
    if not text:
        return ""
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return text

def shuffle_options(correct_opt, wrong_opts):
    """Doğru cevabı her seferinde A, B, C, D arasında rastgele bir yere koyar."""
    all_opts = [correct_opt] + wrong_opts
    random.shuffle(all_opts)
    correct_idx = all_opts.index(correct_opt)
    
    letters = ["A) ", "B) ", "C) ", "D) "]
    formatted_opts = [letters[i] + opt for i, opt in enumerate(all_opts)]
    return formatted_opts, correct_idx

def fetch_cases(history_set):
    cases = []
    try:
        # Arama terimini ve sayısını (retmax: 40) genişlettik
        params = {
            "db": "pubmed",
            "term": "(case report[Publication Type] OR clinical trial) AND free full text[sb]",
            "retmax": "40",
            "sort": "pub_date",
            "retmode": "json"
        }
        res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
        id_list = res.json().get("esearchresult", {}).get("idlist", [])

        new_id_list = [pmid for pmid in id_list if pmid not in history_set][:15]

        if new_id_list:
            sum_params = {"db": "pubmed", "id": ",".join(new_id_list), "retmode": "json"}
            sum_res = requests.get(PUBMED_SUMMARY_URL, params=sum_params, timeout=10)
            result_data = sum_res.json().get("result", {})

            for pmid in new_id_list:
                if pmid in result_data:
                    item = result_data[pmid]
                    title_en = item.get("title", "Clinical Case Report")
                    source = item.get("source", "Medical Journal")
                    
                    hist_en = f"A clinical case published in {source}. Patient presented with unique clinical symptoms requiring diagnostic workup."
                    quest_en = "What is the most appropriate next clinical step?"
                    
                    # Şıkları dinamik karıştırma
                    correct_en = "Order targeted clinical diagnostic imaging / evaluation"
                    wrongs_en = ["Start empirical treatment immediately without testing", "Proceed to invasive surgical intervention", "Routine outpatient observation only"]
                    
                    opts_en, correct_idx = shuffle_options(correct_en, wrongs_en)

                    cases.append({
                        "pmid": pmid,
                        "title_en": title_en,
                        "title_tr": translate_safe(title_en, 'tr'),
                        "history_en": hist_en,
                        "history_tr": translate_safe(hist_en, 'tr'),
                        "question_en": quest_en,
                        "question_tr": translate_safe(quest_en, 'tr'),
                        "options_en": opts_en,
                        "options_tr": [translate_safe(o, 'tr') for o in opts_en],
                        "correct_idx": correct_idx, # Artık değişken! (0, 1, 2 veya 3)
                        "explanation_en": "Full diagnostic rationale and clinical management are available in the open-access publication.",
                        "explanation_tr": "Detaylı tanısal gerekçe ve klinik tedavi yönetimi açık erişimli orijinal yayında mevcuttur.",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
                    history_set.add(pmid)

    except Exception as e:
        print(f"API Hatası: {e}")

    return cases, history_set

def build_site():
    history_set = load_history()
    cases, updated_history = fetch_cases(history_set)
    save_history(updated_history)

    # Şıklar ve Şablon Oluşturucu
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MedikalRadar | Klinik Olgu Simülasyonları</title>
    <style>
        body {{ background-color: #f4f1ea; color: #1a1a1a; font-family: Arial, sans-serif; margin: 0; padding: 0; line-height: 1.7; }}
        header {{ background-color: #e8e2d5; border-bottom: 2px solid #8b0000; padding: 30px 0; text-align: center; }}
        .header-title {{ font-family: Georgia, serif; color: #8b0000; font-size: 2.4em; margin: 0; letter-spacing: 2px; text-transform: uppercase; font-weight: normal; }}
        .sub-title {{ font-family: Georgia, serif; font-style: italic; color: #555555; font-size: 1em; margin-top: 5px; }}
        .top-bar {{ max-width: 800px; margin: 20px auto 0 auto; padding: 0 20px; display: flex; justify-content: flex-end; }}
        .lang-btn {{ background: #e8e2d5; border: 1px solid #8b0000; color: #8b0000; padding: 6px 15px; font-family: Georgia, serif; cursor: pointer; font-size: 0.9em; font-weight: bold; transition: 0.3s; }}
        .lang-btn:hover {{ background: #8b0000; color: #fff; }}
        .container {{ max-width: 800px; margin: 20px auto 60px auto; padding: 0 20px; }}
        .case-card {{ background: #ffffff; border: 1px solid #dcd6cd; padding: 35px; margin-bottom: 35px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        .pmid-tag {{ font-family: Georgia, serif; color: #8b0000; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #e8e2d5; padding-bottom: 5px; display: inline-block; margin-bottom: 15px; font-weight: bold; }}
        h2.case-title {{ font-family: Georgia, serif; color: #1a1a1a; font-size: 1.5em; font-weight: normal; margin: 0 0 20px 0; line-height: 1.4; }}
        .case-history {{ font-family: Arial, sans-serif; color: #333333; font-size: 1em; margin-bottom: 25px; background: #f9f8f5; padding: 15px; border-left: 4px solid #8b0000; }}
        .question-box {{ font-family: Georgia, serif; color: #1a1a1a; font-size: 1.05em; margin-bottom: 15px; font-weight: bold; }}
        .options-list {{ list-style: none; padding: 0; margin: 0 0 20px 0; }}
        .option-item {{ background: #f4f1ea; border: 1px solid #dcd6cd; padding: 12px 15px; margin-bottom: 8px; cursor: pointer; font-family: Arial, sans-serif; font-size: 0.95em; transition: 0.2s; color: #222; }}
        .option-item:hover {{ background: #e8e2d5; border-color: #8b0000; }}
        .option-item.correct {{ background: #e8f5e9 !important; border-color: #2e7d32 !important; color: #1b5e20 !important; font-weight: bold; }}
        .option-item.wrong {{ background: #ffebee !important; border-color: #c62828 !important; color: #b71c1c !important; }}
        .explanation-box {{ display: none; background: #f9f8f5; border: 1px dashed #8b0000; padding: 15px; margin-top: 15px; font-size: 0.9em; color: #222; }}
        .pubmed-link {{ display: inline-block; margin-top: 15px; color: #8b0000; text-decoration: none; font-family: Georgia, serif; font-size: 0.9em; font-style: italic; font-weight: bold; }}
        .pubmed-link:hover {{ text-decoration: underline; }}
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

    for c in cases:
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
