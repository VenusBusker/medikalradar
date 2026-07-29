import os
import json
import random
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
JSON_FILE_PATH = "docs/cases.json"

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
        " cystectomy ", " outcome ", " postoperatively ", " management included ",
        " tanısı konuldu ", " teşhis edildi ", " tedavisi yapıldı ", " ameliyata alındı "
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
    return " ".join(clinical_history), " ".join(clinical_outcome) if clinical_outcome else "Full diagnostic details in report."

def detect_language(text):
    """Metnin Türkçe mi yoksa İngilizce mi olduğunu basitçe tespit eder."""
    turkish_chars = ["ı", "ğ", "ü", "ş", "ö", "ç", "veya", "hasta", "tanı", "tedavi", "klinik"]
    text_lower = text.lower()
    matches = sum(1 for char in turkish_chars if char in text_lower)
    return "tr" if matches >= 2 else "en"

def extract_advanced_metadata(full_text):
    text_upper = full_text.upper()
    
    category = "General Medicine / Genel Tıp"
    if any(k in text_upper for k in ["CARDIAC", "ECG", "MYOCARDIAL", "HEART", "KARDİYO", "EKG", "KALP"]):
        category = "Cardiology / Kardiyoloji"
    elif any(k in text_upper for k in ["NEUROLOGICAL", "BRAIN", "SEIZURE", "STROKE", "NÖROLOJİ", "BEYİN", "FELÇ"]):
        category = "Neurology / Nöroloji"
    elif any(k in text_upper for k in ["ABDOMINAL", "SURGERY", "GASTRO", "KARIN", "CERRAHİ", "MİDE"]):
        category = "Gastroenterology / Cerrahi"
    elif any(k in text_upper for k in ["PEDIATRIC", "CHILD", "INFANT", "PEDİATRİ", "ÇOCUK"]):
        category = "Pediatrics / Pediatri"
    elif any(k in text_upper for k in ["PULMONARY", "LUNG", "PNEUMONIA", "GÖĞÜS", "AKCİĞER"]):
        category = "Pulmonology / Göğüs Hastalıkları"

    return category

def build_contextual_options(full_text, category, lang):
    if lang == "tr":
        if "Kardiyoloji" in category:
            q = "Bu kardiyak tablo ile başvuran hastada ilk yapılması gereken acil tanısal yaklaşım nedir?"
            correct = "Acil 12 Derivasyonlu EKG ve seri kardiyak enzim (Troponin) takibi"
            wrongs = ["Acil üst gastrointestinal sistem endoskopisi", "Ampirik sözlü antibiyotik tedavisi", "Rutin beyin tomografisi"]
        elif "Nöroloji" in category:
            q = "Bu nörolojik bulgularla başvuran hastada en uygun yaklaşım hangisidir?"
            correct = "Acil Beyin Görüntülemesi (MR/BT) ve kapsamlı nörolojik muayene"
            wrongs = ["Ampirik oral antifungal tedavi başlanması", "Batın ultrasonu ve karaciğer enzim paneli", "Fizik tedavi poliklinik sevki"]
        else:
            q = "Yukarıdaki klinik öyküye dayanarak bir sonraki en uygun tanı/tedavi adımı nedir?"
            correct = "Hedefe yönelik laboratuvar tetkikleri ve spesifik görüntüleme yöntemleri"
            wrongs = ["Tetkik yapmaksızın ampirik yüksek doz tedavi", "Görüntüleme yapmadan acil cerrahi müdahale", "Sadece rutin poliklinik kontrolü önerilmesi"]
    else:
        if "Cardiology" in category:
            q = "What is the most appropriate immediate diagnostic evaluation for this cardiac presentation?"
            correct = "Urgent 12-lead ECG and serial cardiac biomarker (Troponin) tracking"
            wrongs = ["Emergency upper gastrointestinal endoscopy", "Empirical oral antibiotic administration", "Routine non-contrast brain CT scan"]
        elif "Neurology" in category:
            q = "What is the most appropriate next step for this neurological presentation?"
            correct = "Urgent Neuroimaging (Brain MRI/CT) and comprehensive neurological evaluation"
            wrongs = ["Immediate empirical oral antifungal therapy", "Abdominal ultrasound panel", "Discharge with physical therapy referral only"]
        else:
            q = "Based on the clinical history above, what is the most appropriate next management step?"
            correct = "Targeted specialized laboratory workup and targeted diagnostic imaging"
            wrongs = ["Empirical high-dose therapy without further laboratory testing", "Immediate invasive surgical procedure without prior imaging", "Discharge with routine outpatient follow-up only"]
            
    return q, correct, wrongs

def load_existing_cases():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON load error: {e}")
    return []

def fetch_multi_source_cases():
    existing_cases = load_existing_cases()
    existing_pmids = {c["pmid"] for c in existing_cases}
    
    new_cases = []
    
    # ÇOKLU SORGU AĞI: Hem Global Hem Türkçe Yayın Yapan Tıp Dergileri
    search_queries = [
        '(case report[Publication Type]) AND free full text[sb]', # Global PubMed
        '("Turkey"[Location] OR "Turkish"[Language] OR "TR"[Journal]) AND ("case report"[Title/Abstract]) AND free full text[sb]', # Türkçe / Türkiye Kaynaklı Tıp Yayınları
        '("BMC Medical Education"[Journal] OR "BMC Medicine"[Journal]) AND case report AND free full text[sb]' # BMC Open Access
    ]

    for query in search_queries:
        try:
            params = {
                "db": "pubmed", 
                "term": query, 
                "retmax": "50", 
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

                    if pmid in existing_pmids: continue

                    title_elem = article.find(".//ArticleTitle")
                    title_text = title_elem.text if title_elem is not None else "Clinical Case Presentation"

                    pub_date_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
                    published_year = pub_date_elem.text if pub_date_elem is not None else str(datetime.now().year)

                    abstract_nodes = article.findall(".//AbstractText")
                    full_abstract = " ".join([node.text for node in abstract_nodes if node.text])

                    if len(full_abstract) < 120: continue

                    lang = detect_language(full_abstract + " " + title_text)
                    history_text, outcome_text = trim_at_spoiler(full_abstract)
                    category = extract_advanced_metadata(full_abstract)
                    q_text, correct_opt, wrong_opts = build_contextual_options(full_abstract, category, lang)
                    opts, correct_idx = shuffle_options(correct_opt, wrong_opts)

                    new_case = {
                        "pmid": pmid,
                        "lang": lang, # Metnin Dili ("tr" veya "en")
                        "title_en": title_text,
                        "title_tr": title_text,
                        "history_en": history_text,
                        "history_tr": history_text,
                        "question_en": q_text,
                        "question_tr": q_text,
                        "options_en": opts,
                        "options_tr": opts,
                        "correct_idx": correct_idx,
                        "explanation_en": outcome_text,
                        "explanation_tr": outcome_text,
                        "category": category,
                        "published_date": published_year,
                        "fetched_at": datetime.now().strftime("%Y-%m-%d"),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    }
                    
                    new_cases.append(new_case)
                    existing_pmids.add(pmid)

        except Exception as e:
            print(f"Fetch Error ({query}): {e}")

    combined_cases = new_cases + existing_cases

    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_multi_source_cases()
