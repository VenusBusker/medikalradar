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
    spoiler_keywords = [" diagnosis of ", " diagnosed with ", " was diagnosed ", " reveal ", " patient underwent ", " treated with ", " surgical ", " laparoscopy ", " cystectomy ", " outcome "]
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
    return " ".join(clinical_history), " ".join(clinical_outcome) if clinical_outcome else "Full details in paper."

def extract_dynamic_options(full_text):
    text_upper = full_text.upper()
    if "ECG" in text_upper or "ELECTROCARDIOGRAM" in text_upper:
        correct_opt = "12-Lead ECG & Urgent Cardiac Marker Evaluation"
    elif "CT" in text_upper or "COMPUTED TOMOGRAPHY" in text_upper:
        correct_opt = "Urgent Contrast-Enhanced Computed Tomography (CT)"
    elif "MRI" in text_upper or "MAGNETIC RESONANCE" in text_upper:
        correct_opt = "Brain & Spine Magnetic Resonance Imaging (MRI)"
    elif "ULTRASOUND" in text_upper or "SONOGRAPHY" in text_upper:
        correct_opt = "Emergency Bedside Diagnostic Ultrasonography"
    else:
        correct_opt = "Targeted Specialized Laboratory & Diagnostic Workup"

    wrong_opts = ["Immediate Empirical High-Dose Antibiotics", "Urgent Upper Gastrointestinal Endoscopy", "Discharge with Conservative Antipyretics"]
    return correct_opt, wrong_opts

def fetch_cases():
    cases = []
    try:
        params = {"db": "pubmed", "term": "(case report[Publication Type]) AND free full text[sb]", "retmax": "10", "sort": "pub_date", "retmode": "json"}
        res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
        id_list = res.json().get("esearchresult", {}).get("idlist", [])

        if id_list:
            fetch_params = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
            xml_res = requests.get(PUBMED_FETCH_URL, params=fetch_params, timeout=12)
            root = ET.fromstring(xml_res.content)

            for article in root.findall(".//PubmedArticle"):
                pmid = article.find(".//PMID").text
                title_elem = article.find(".//ArticleTitle")
                title_en = title_elem.text if title_elem is not None else "Clinical Case Presentation"

                abstract_nodes = article.findall(".//AbstractText")
                full_abstract_en = " ".join([node.text for node in abstract_nodes if node.text])

                if len(full_abstract_en) < 200: continue

                history_en, outcome_en = trim_at_spoiler(full_abstract_en)
                correct_en, wrongs_en = extract_dynamic_options(full_abstract_en)
                opts_en, correct_idx = shuffle_options(correct_en, wrongs_en)

                cases.append({
                    "pmid": pmid,
                    "title_en": title_en,
                    "title_tr": translate_safe(title_en, 'tr'),
                    "history_en": history_en,
                    "history_tr": translate_safe(history_en, 'tr'),
                    "question_en": "Based on the clinical history above, what is the most appropriate next step?",
                    "question_tr": "Yukarıdaki klinik öyküye dayanarak bir sonraki en uygun adım nedir?",
                    "options_en": opts_en,
                    "options_tr": [translate_safe(o, 'tr') for o in opts_en],
                    "correct_idx": correct_idx,
                    "explanation_en": outcome_en,
                    "explanation_tr": translate_safe(outcome_en, 'tr'),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
    except Exception as e:
        print(f"Error: {e}")

    # Sadece JSON dosyasına kaydet!
    with open("docs/cases.json", "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_cases()
