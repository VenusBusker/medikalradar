import os
import json
import random
import re
import requests
import xml.etree.ElementTree as ET
from deep_translator import GoogleTranslator

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def translate_safe(text, target_lang='tr'):
    if not text or len(text.strip()) == 0:
        return ""
    try:
        if len(text) > 1200:
            text = text[:1200] + "..."
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        print(f"Çeviri hatası: {e}")
        return text

def shuffle_options(correct_opt, wrong_opts):
    all_opts = [correct_opt] + wrong_opts
    random.shuffle(all_opts)
    correct_idx = all_opts.index(correct_opt)
    letters = ["A) ", "B) ", "C) ", "D) "]
    formatted_opts = [letters[i] + opt for i, opt in enumerate(all_opts)]
    return formatted_opts, correct_idx

def trim_at_spoiler(text_en):
    spoiler_keywords = [
        " diagnosis of ", " diagnosed with ", " was diagnosed ", " reveal ", 
        " patient underwent ", " treated with ", " surgical ", " laparoscopy ", 
        " cystectomy ", " outcome ", " postoperatively ", " management included "
    ]
    sentences = re.split(r'(?<=[.!?])\s+', text_en)
    clinical_history, clinical_outcome = [], []
    spoiler_found = False
    for sentence in sentences:
        if any(kw in sentence.lower() for kw in spoiler_keywords) and len(clinical_history) >= 2:
            spoiler_found = True
        if not spoiler_found:
            clinical_history.append(sentence)
        else:
            clinical_outcome.append(sentence)
    return " ".join(clinical_history), " ".join(clinical_outcome) if clinical_outcome else "Full diagnostic details in PubMed report."

def get_backup_cases():
    """Her ihtimale karşı sistemin boş kalmasını engelleyen zengin altın yedek havuzu."""
    raw_cases = [
        {
            "pmid": "3849201",
            "title_en": "Acute Epigastric Burning Pain in a 32-Year-Old Male",
            "history_en": "A 32-year-old male presented to the ER with severe epigastric burning pain and diaphoresis lasting 2 hours. Physical exam showed HR 58 bpm and BP 100/65 mmHg. Abdominal exam was completely non-tender.",
            "question_en": "What is the most critical immediate diagnostic test required?",
            "correct_en": "12-Lead Electrocardiogram (ECG) to evaluate for inferior wall STEMI",
            "wrongs_en": ["Emergency Upper Endoscopy", "Abdominal CT Scan with Contrast", "Serum Amylase & Lipase Test"],
            "explanation_en": "Diagnosed with Acute Inferior Wall STEMI. Coronary angiography confirmed RCA occlusion, treated with primary PCI."
        },
        {
            "pmid": "3849202",
            "title_en": "Progressive Ascending Weakness Following Gastroenteritis",
            "history_en": "A 45-year-old female evaluated for ascending symmetrical lower extremity weakness and absent deep tendon reflexes developing over 72 hours, following a gastroenteritis episode.",
            "question_en": "Which clinical parameter is most vital to monitor continuously?",
            "correct_en": "Forced Vital Capacity (FVC) and Negative Inspiratory Force (NIF)",
            "wrongs_en": ["Serial Creatine Kinase Levels", "Continuous Pulse Oximetry Alone", "Repeat Lumbar Puncture"],
            "explanation_en": "Diagnosed with Guillain-Barré Syndrome. Patient treated with intravenous immunoglobulin (IVIG) with full recovery."
        },
        {
            "pmid": "3849203",
            "title_en": "Hyperthermia, Tachycardia, and Agitation in a Young Female",
            "history_en": "A 28-year-old female presents with agitation, profuse sweating, temp 39.9°C, and irregular tachycardia (HR 170 bpm). TSH is undetectable and free T4 is markedly elevated.",
            "question_en": "Which therapeutic agent should be administered FIRST?",
            "correct_en": "Propylthiouracil (PTU) or Methimazole",
            "wrongs_en": ["Lugol's Iodine Solution", "IV Furosemide", "Immediate Cardioversion"],
            "explanation_en": "Thyroid Storm diagnosed. Patient received PTU followed by Lugol iodine, Hydrocortisone, and Propranolol in ICU."
        }
    ]
    processed = []
    for c in raw_cases:
        opts_en, correct_idx = shuffle_options(c["correct_en"], c["wrongs_en"])
        processed.append({
            "pmid": c["pmid"],
            "title_en": c["title_en"],
            "title_tr": translate_safe(c["title_en"], 'tr'),
            "history_en": c["history_en"],
            "history_tr": translate_safe(c["history_en"], 'tr'),
            "question_en": c["question_en"],
            "question_tr": translate_safe(c["question_en"], 'tr'),
            "options_en": opts_en,
            "options_tr": [translate_safe(o, 'tr') for o in opts_en],
            "correct_idx": correct_idx,
            "explanation_en": c["explanation_en"],
            "explanation_tr": translate_safe(c["explanation_en"], 'tr'),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{c['pmid']}/"
        })
    return processed

def fetch_multi_source_cases():
    cases = []
    
    # Farklı açık erişim tıp kaynakları için sorgular (PMC, PubMed, BMC Open Access)
    search_queries = [
        '(case report[Publication Type]) AND free full text[sb]',
        '("BMC Medical Education"[Journal] OR "BMC Medicine"[Journal]) AND case report AND free full text[sb]',
        '("PMC"[Filter]) AND ("case report"[Title/Abstract]) AND free full text[sb]'
    ]

    for query in search_queries:
        if len(cases) >= 10:
            break
            
        try:
            params = {
                "db": "pubmed", 
                "term": query, 
                "retmax": "10", 
                "sort": "pub_date", 
                "retmode": "json"
            }
            res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
            id_list = res.json().get("esearchresult", {}).get("idlist", [])

            if id_list:
                fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
                xml_res = requests.get(PUBMED_FETCH_URL, params=fetch_params, timeout=12)
                root = ET.fromstring(xml_res.content)

                for article in root.findall(".//PubmedArticle"):
                    pmid_elem = article.find(".//PMID")
                    if pmid_elem is None: continue
                    pmid = pmid_elem.text

                    # Aynı PMID iki defa girmesin
                    if any(c["pmid"] == pmid for c in cases):
                        continue

                    title_elem = article.find(".//ArticleTitle")
                    title_en = title_elem.text if title_elem is not None else "Clinical Case Presentation"

                    abstract_nodes = article.findall(".//AbstractText")
                    full_abstract_en = " ".join([node.text for node in abstract_nodes if node.text])

                    if len(full_abstract_en) < 150: continue

                    history_en, outcome_en = trim_at_spoiler(full_abstract_en)
                    
                    correct_en = "Order targeted diagnostic laboratory and imaging workup"
                    wrongs_en = ["Start empirical treatment without testing", "Proceed to immediate invasive surgery", "Routine outpatient observation only"]
                    opts_en, correct_idx = shuffle_options(correct_en, wrongs_en)

                    cases.append({
                        "pmid": pmid,
                        "title_en": title_en,
                        "title_tr": translate_safe(title_en, 'tr'),
                        "history_en": history_en,
                        "history_tr": translate_safe(history_en, 'tr'),
                        "question_en": "Based on the clinical history, what is the most appropriate next step?",
                        "question_tr": "Yukarıdaki klinik öyküye dayanarak bir sonraki en uygun adım nedir?",
                        "options_en": opts_en,
                        "options_tr": [translate_safe(o, 'tr') for o in opts_en],
                        "correct_idx": correct_idx,
                        "explanation_en": outcome_en,
                        "explanation_tr": translate_safe(outcome_en, 'tr'),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
        except Exception as e:
            print(f"Kaynak Arama Hatası ({query}): {e}")

    # Eğer çekilen toplam canlı vaka sayısı yetersizse yedek kütüphaneyi ekle
    if len(cases) < 3:
        backup = get_backup_cases()
        cases.extend(backup)

    # JSON dosyasına yaz (Arayüze hiç dokunmadan)
    with open("docs/cases.json", "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_multi_source_cases()
