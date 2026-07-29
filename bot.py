import os
import json
import random
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from deep_translator import GoogleTranslator

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
JSON_FILE_PATH = "docs/cases.json"

def translate_safe(text, target_lang='tr'):
    """Çeviri Emniyeti: Hata durumunda boş dönmez, orijinal metni korur."""
    if not text or len(text.strip()) == 0:
        return ""
    try:
        if len(text) > 1200:
            text = text[:1200] + "..."
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"Çeviri emniyeti devreye girdi: {e}")
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

def is_valid_clinical_case(text):
    text_lower = text.lower()
    patient_indicators = ["year-old", "yr-old", "patient presented", "male presented", "female presented", "admitted with", "history of"]
    return any(ind in text_lower for ind in patient_indicators)

def extract_advanced_metadata(full_text):
    """Branş, Triyaj (Aciliyet) ve Arama Kelimelerini tespit eder."""
    text_upper = full_text.upper()
    
    # 1. Branş Tespiti
    category = "Genel Tıp"
    if "CARDIAC" in text_upper or "ECG" in text_upper or "MYOCARDIAL" in text_upper or "HEART" in text_upper:
        category = "Kardiyoloji"
    elif "NEUROLOGICAL" in text_upper or "BRAIN" in text_upper or "SEIZURE" in text_upper or "STROKE" in text_upper:
        category = "Nöroloji"
    elif "ABDOMINAL" in text_upper or "SURGERY" in text_upper or "APPENDICITIS" in text_upper or "GASTRO" in text_upper:
        category = "Genel Cerrahi / Gastroenteroloji"
    elif "PEDIATRIC" in text_upper or "CHILD" in text_upper or "INFANT" in text_upper:
        category = "Pediatri"
    elif "PULMONARY" in text_upper or "LUNG" in text_upper or "PNEUMONIA" in text_upper:
        category = "Göğüs Hastalıkları"

    # 2. Triyaj (Aciliyet) Derecesi
    triage = "Green" # Rutin / Poliklinik
    if any(k in text_upper for k in ["CPR", "SHOCK", "ICU", "ANAPHYLAXIS", "ACUTE RESPIRATORY", "CARDIAC ARREST"]):
        triage = "Red" # Acil / Kritik
    elif any(k in text_upper for k in ["ACUTE PAIN", "HIGH FEVER", "FRACTURE", "TACHYCARDIA"]):
        triage = "Yellow" # Orta Derece Acil

    # 3. Anahtar Kelimeler (Keywords)
    keywords = []
    possible_kw = ["ECG", "CT Scan", "MRI", "Ultrasound", "Biopsy", "Fever", "Chest Pain", "Dyspnea", "Hypertension", "Tachycardia"]
    for kw in possible_kw:
        if kw.upper() in text_upper:
            keywords.append(kw)

    return category, triage, keywords

def build_contextual_options(full_text, category):
    """Metnin ve branşın bağlamına özel soru/şıklar üretir."""
    if category == "Kardiyoloji":
        q_tr = "Bu kardiyak tablo ile başvuran hastada ilk yapılması gereken acil tanısal yaklaşım nedir?"
        q_en = "What is the most appropriate immediate diagnostic evaluation for this cardiac presentation?"
        correct = "Urgent 12-lead ECG and serial cardiac biomarker (Troponin) tracking"
        wrongs = ["Emergency upper gastrointestinal endoscopy", "Empirical oral antibiotic and antipyretic administration", "Routine non-contrast brain CT scan"]
    elif category == "Nöroloji":
        q_tr = "Bu nörolojik bulgularla başvuran hastada en uygun yaklaşım hangisidir?"
        q_en = "What is the most appropriate next step for this neurological presentation?"
        correct = "Urgent Neuroimaging (Brain MRI/CT) and comprehensive neurological evaluation"
        wrongs = ["Immediate empirical oral antifungal therapy", "Abdominal ultrasound and liver function blood panel", "Discharge with outpatient physical therapy referral only"]
    elif "Cerrahi" in category:
        q_tr = "Bu akut karın / cerrahi tablo gösteren hastada ilk aşamada ne yapılmalıdır?"
        q_en = "What is the most appropriate initial evaluation for this acute abdominal case?"
        correct = "Contrast-enhanced Abdominal/Pelvic CT Scan and urgent surgical consultation"
        wrongs = ["Immediate outpatient chest radiography only", "High-dose IV corticosteroid pulse therapy", "Empirical psychiatric consultation"]
    else:
        q_tr = "Yukarıdaki klinik öykü ve fizik muayene bulgularına dayanarak en uygun sonraki adım nedir?"
        q_en = "Based on the clinical history above, what is the most appropriate next management step?"
        correct = "Targeted specialized laboratory workup and targeted diagnostic imaging"
        wrongs = ["Empirical high-dose therapy without further laboratory testing", "Immediate invasive surgical procedure without prior imaging", "Discharge with routine outpatient follow-up only"]
        
    return q_tr, q_en, correct, wrongs

def load_existing_cases():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON okuma hatası: {e}")
    return []

def fetch_and_append_cases():
    existing_cases = load_existing_cases()
    existing_pmids = {c["pmid"] for c in existing_cases}
    
    new_cases = []
    try:
        params = {
            "db": "pubmed", 
            "term": "(case report[Publication Type]) AND free full text[sb]", 
            "retmax": "100", 
            "sort": "pub_date", 
            "retmode": "json"
        }
        res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=12)
        id_list = res.json().get("esearchresult", {}).get("idlist", [])

        if id_list:
            fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
            xml_res = requests.get(PUBMED_FETCH_URL, params=fetch_params, timeout=15)
            root = ET.fromstring(xml_res.content)

            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                if pmid_elem is None: continue
                pmid = pmid_elem.text

                if pmid in existing_pmids: continue

                title_elem = article.find(".//ArticleTitle")
                title_en = title_elem.text if title_elem is not None else "Clinical Case Presentation"

                # Yayın Tarihi Tespiti
                pub_date_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
                published_year = pub_date_elem.text if pub_date_elem is not None else str(datetime.now().year)

                abstract_nodes = article.findall(".//AbstractText")
                full_abstract_en = " ".join([node.text for node in abstract_nodes if node.text])

                if len(full_abstract_en) < 180 or not is_valid_clinical_case(full_abstract_en):
                    continue

                # Görsel Tespiti (PubMed Central Görsel Bağlantısı Altyapısı)
                has_image = False
                image_url = ""
                pmc_elem = article.find(".//ArticleIdList/ArticleId[@IdType='pmc']")
                if pmc_elem is None:
                    # Alternatif ID arama
                    for aid in article.findall(".//ArticleId"):
                        if aid.get("IdType") == "pmc":
                            pmc_elem = aid
                            break
                if pmc_elem is not None and pmc_elem.text:
                    has_image = True
                    image_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_elem.text}/bin/"

                history_en, outcome_en = trim_at_spoiler(full_abstract_en)
                category, triage, keywords = extract_advanced_metadata(full_abstract_en)
                q_tr, q_en, correct_en, wrongs_en = build_contextual_options(full_abstract_en, category)
                opts_en, correct_idx = shuffle_options(correct_en, wrongs_en)

                # Türkçe Çeviriler (Emniyetli)
                title_tr = translate_safe(title_en, 'tr')
                history_tr = translate_safe(history_en, 'tr')
                outcome_tr = translate_safe(outcome_en, 'tr')
                opts_tr = [translate_safe(o, 'tr') for o in opts_en]

                new_case = {
                    "pmid": pmid,
                    "title_en": title_en,
                    "title_tr": title_tr,
                    "history_en": history_en,
                    "history_tr": history_tr,
                    "question_en": q_en,
                    "question_tr": q_tr,
                    "options_en": opts_en,
                    "options_tr": opts_tr,
                    "correct_idx": correct_idx,
                    "explanation_en": outcome_en,
                    "explanation_tr": outcome_tr,
                    "category": category,
                    "triage": triage,
                    "keywords": keywords,
                    "has_image": has_image,
                    "image_url": image_url,
                    "published_date": published_year,
                    "fetched_at": datetime.now().strftime("%Y-%m-%d"),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                }
                
                new_cases.append(new_case)
                existing_pmids.add(pmid)

    except Exception as e:
        print(f"Çekim hatası: {e}")

    # Yeni vakaları en başa ekle (Sınırsız Büyüyen Arşiv)
    combined_cases = new_cases + existing_cases

    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_append_cases()
