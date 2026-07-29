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

def extract_advanced_metadata(full_text):
    text_upper = full_text.upper()
    
    category = "General Medicine"
    if "CARDIAC" in text_upper or "ECG" in text_upper or "MYOCARDIAL" in text_upper or "HEART" in text_upper:
        category = "Cardiology"
    elif "NEUROLOGICAL" in text_upper or "BRAIN" in text_upper or "SEIZURE" in text_upper or "STROKE" in text_upper:
        category = "Neurology"
    elif "ABDOMINAL" in text_upper or "SURGERY" in text_upper or "GASTRO" in text_upper:
        category = "Gastroenterology / Surgery"
    elif "PEDIATRIC" in text_upper or "CHILD" in text_upper or "INFANT" in text_upper:
        category = "Pediatrics"
    elif "PULMONARY" in text_upper or "LUNG" in text_upper or "PNEUMONIA" in text_upper:
        category = "Pulmonology"

    return category

def build_contextual_options(full_text, category):
    if category == "Cardiology":
        q_en = "What is the most appropriate immediate diagnostic evaluation for this cardiac presentation?"
        correct = "Urgent 12-lead ECG and serial cardiac biomarker (Troponin) tracking"
        wrongs = ["Emergency upper gastrointestinal endoscopy", "Empirical oral antibiotic and antipyretic administration", "Routine non-contrast brain CT scan"]
    elif category == "Neurology":
        q_en = "What is the most appropriate next step for this neurological presentation?"
        correct = "Urgent Neuroimaging (Brain MRI/CT) and comprehensive neurological evaluation"
        wrongs = ["Immediate empirical oral antifungal therapy", "Abdominal ultrasound and liver function blood panel", "Discharge with outpatient physical therapy referral only"]
    elif "Surgery" in category:
        q_en = "What is the most appropriate initial evaluation for this acute abdominal case?"
        correct = "Contrast-enhanced Abdominal/Pelvic CT Scan and urgent surgical consultation"
        wrongs = ["Immediate outpatient chest radiography only", "High-dose IV corticosteroid pulse therapy", "Empirical psychiatric consultation"]
    else:
        q_en = "Based on the clinical history above, what is the most appropriate next management step?"
        correct = "Targeted specialized laboratory workup and targeted diagnostic imaging"
        wrongs = ["Empirical high-dose therapy without further laboratory testing", "Immediate invasive surgical procedure without prior imaging", "Discharge with routine outpatient follow-up only"]
        
    return q_en, correct, wrongs

def load_existing_cases():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON load error: {e}")
    return []

def fetch_and_append_cases():
    existing_cases = load_existing_cases()
    existing_pmids = {c["pmid"] for c in existing_cases}
    
    new_cases = []
    try:
        # PubMed'den 100 taze makale/vaka talep ediyoruz
        params = {
            "db": "pubmed", 
            "term": "(case report[Publication Type] OR clinical trial[Publication Type]) AND free full text[sb]", 
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

                pub_date_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
                published_year = pub_date_elem.text if pub_date_elem is not None else str(datetime.now().year)

                abstract_nodes = article.findall(".//AbstractText")
                full_abstract_en = " ".join([node.text for node in abstract_nodes if node.text])

                if len(full_abstract_en) < 120: continue

                history_en, outcome_en = trim_at_spoiler(full_abstract_en)
                category = extract_advanced_metadata(full_abstract_en)
                q_en, correct_en, wrongs_en = build_contextual_options(full_abstract_en, category)
                opts_en, correct_idx = shuffle_options(correct_en, wrongs_en)

                new_case = {
                    "pmid": pmid,
                    "title_en": title_en,
                    "title_tr": title_en, # Çeviri engeline takılmamak için orijinal İngilizce metin
                    "history_en": history_en,
                    "history_tr": history_en,
                    "question_en": q_en,
                    "question_tr": q_en,
                    "options_en": opts_en,
                    "options_tr": opts_en,
                    "correct_idx": correct_idx,
                    "explanation_en": outcome_en,
                    "explanation_tr": outcome_en,
                    "category": category,
                    "published_date": published_year,
                    "fetched_at": datetime.now().strftime("%Y-%m-%d"),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                }
                
                new_cases.append(new_case)
                existing_pmids.add(pmid)

    except Exception as e:
        print(f"Fetch Error: {e}")

    # Yeni çekilen onlarca içeriği arşivin en başına koy
    combined_cases = new_cases + existing_cases

    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_and_append_cases()
