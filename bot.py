import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

os.makedirs("docs", exist_ok=True)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
JSON_FILE_PATH = "docs/cases.json"

def detect_language(text):
    turkish_chars = ["ı", "ğ", "ü", "ş", "ö", "ç", "veya", "hasta", "tanı", "tedavi", "klinik"]
    text_lower = text.lower()
    matches = sum(1 for char in turkish_chars if char in text_lower)
    return "tr" if matches >= 2 else "en"

def extract_advanced_metadata(full_text):
    text_upper = full_text.upper()
    
    # Kategori / Branş Tespiti
    category = "General Medicine"
    if any(k in text_upper for k in ["CARDIAC", "ECG", "MYOCARDIAL", "HEART", "EKG", "KALP", "CARDIO"]):
        category = "Cardiology"
    elif any(k in text_upper for k in ["NEUROLOGICAL", "BRAIN", "SEIZURE", "STROKE", "NÖROLOJİ", "BEYİN"]):
        category = "Neurology"
    elif any(k in text_upper for k in ["ABDOMINAL", "SURGERY", "GASTRO", "KARIN", "CERRAHİ", "LAPAROSCOPY"]):
        category = "Surgery"
    elif any(k in text_upper for k in ["PEDIATRIC", "CHILD", "INFANT", "PEDİATRİ", "ÇOCUK"]):
        category = "Pediatrics"
    elif any(k in text_upper for k in ["PULMONARY", "LUNG", "PNEUMONIA", "AKCİĞER", "RESPIRATORY"]):
        category = "Pulmonology"
    elif any(k in text_upper for k in ["DERMATOLOGY", "SKIN", "DERMA", "DERİ", "CİLT"]):
        category = "Dermatology"

    # Aciliyet Triyajı
    triage = "Yellow"
    if any(k in text_upper for k in ["EMERGENCY", "ACUTE", "CRITICAL", "SHOCK", "ARREST", "ACİL"]):
        triage = "Red"
    elif any(k in text_upper for k in ["CHRONIC", "ROUTINE", "STABLE", "KRONİK"]):
        triage = "Green"

    # Otomatik Anahtar Kelime (Keywords) Çıkarıcı
    medical_terms = [
        "ECG", "EKG", "Troponin", "MRI", "CT", "STEMI", "Areflexia", "Tachycardia", 
        "Bradycardia", "Dyspnea", "Laparoscopy", "Biopsy", "Ultrasound", "Hypertension",
        "Hypotension", "Anemia", "Infection", "Lesion", "Tumor", "Fracture"
    ]
    extracted_keywords = [term for term in medical_terms if re.search(r'\b' + re.escape(term) + r'\b', full_text, re.I)]

    # Okuma Süresi Hesaplayıcı (Ortalama 200 kelime/dk)
    word_count = len(full_text.split())
    read_time = max(1, round(word_count / 200))

    return category, triage, extracted_keywords, read_time

def load_existing_cases():
    if os.path.exists(JSON_FILE_PATH):
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON load error: {e}")
    return []

# 1. KAYNAK: NCBI PubMed
def fetch_from_pubmed(existing_pmids):
    new_cases = []
    try:
        params = {
            "db": "pubmed", 
            "term": "(case report[Publication Type]) AND free full text[sb]", 
            "retmax": "40", 
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
                if pmid_elem is None or pmid_elem.text in existing_pmids: continue
                pmid = pmid_elem.text

                title_elem = article.find(".//ArticleTitle")
                title_text = title_elem.text if title_elem is not None else "Clinical Case Presentation"

                journal_elem = article.find(".//Journal/Title")
                journal_name = journal_elem.text if journal_elem is not None else "Medical Journal"

                pub_date_elem = article.find(".//Journal/JournalIssue/PubDate/Year")
                published_year = pub_date_elem.text if pub_date_elem is not None else "2026"

                abstract_nodes = article.findall(".//AbstractText")
                full_abstract = " ".join([node.text for node in abstract_nodes if node.text])

                if len(full_abstract) < 120: continue

                lang = detect_language(full_abstract + " " + title_text)
                category, triage, keywords, read_time = extract_advanced_metadata(full_abstract)

                new_cases.append({
                    "pmid": pmid,
                    "source": "PubMed",
                    "lang": lang,
                    "title_en": title_text,
                    "title_tr": title_text,
                    "history_en": full_abstract, # Spoiler bölmesi yok, tam metin!
                    "history_tr": full_abstract,
                    "explanation_en": full_abstract, # Tam metin bütünü
                    "explanation_tr": full_abstract,
                    "category": category,
                    "triage": triage,
                    "keywords": keywords,
                    "read_time_min": read_time,
                    "has_image": False,
                    "image_url": "",
                    "journal_name": journal_name,
                    "published_date": published_year,
                    "fetched_at": datetime.now().strftime("%Y-%m-%d"),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
                existing_pmids.add(pmid)
    except Exception as e:
        print(f"PubMed Fetch Error: {e}")
    return new_cases

# 2. KAYNAK: Europe PMC (Görsel ve Açık Bağlantı Destekli)
def fetch_from_europe_pmc(existing_pmids):
    new_cases = []
    try:
        params = {
            "query": 'TYPE:"case-report" AND OPEN_ACCESS:y',
            "format": "json",
            "pageSize": "40",
            "sort": "P_PD_D desc"
        }
        res = requests.get(EUROPE_PMC_URL, params=params, timeout=10)
        results = res.json().get("resultList", {}).get("result", [])

        for item in results:
            pmid = item.get("pmid") or item.get("id")
            if not pmid or str(pmid) in existing_pmids: continue

            title_text = item.get("title", "Clinical Paper")
            abstract_text = item.get("abstractText", "")
            pub_year = str(item.get("pubYear", "2026"))
            journal_title = item.get("journalTitle", "Open Access Medical Journal")
            doi = item.get("doi", "")

            if len(abstract_text) < 120: continue

            lang = detect_language(abstract_text + " " + title_text)
            category, triage, keywords, read_time = extract_advanced_metadata(abstract_text)

            # Europe PMC Açık Görsel / Mantık Altyapısı
            has_image = item.get("hasDbCrossReferences", "N") == "Y"
            pmcid = item.get("pmcid", "")
            image_url = f"https://europepmc.org/articles/{pmcid}/bin/" if pmcid else ""

            new_cases.append({
                "pmid": str(pmid),
                "source": "Europe PMC",
                "lang": lang,
                "title_en": title_text,
                "title_tr": title_text,
                "history_en": abstract_text, # Spoiler bölmesi yok!
                "history_tr": abstract_text,
                "explanation_en": abstract_text,
                "explanation_tr": abstract_text,
                "category": category,
                "triage": triage,
                "keywords": keywords,
                "read_time_min": read_time,
                "has_image": has_image,
                "image_url": image_url,
                "journal_name": journal_title,
                "published_date": pub_year,
                "doi": doi,
                "fetched_at": datetime.now().strftime("%Y-%m-%d"),
                "url": f"https://europepmc.org/article/MED/{pmid}"
            })
            existing_pmids.add(str(pmid))
    except Exception as e:
        print(f"Europe PMC Fetch Error: {e}")
    return new_cases

def main():
    existing_cases = load_existing_cases()
    existing_pmids = {str(c["pmid"]) for c in existing_cases}
    
    pubmed_cases = fetch_from_pubmed(existing_pmids)
    europe_cases = fetch_from_europe_pmc(existing_pmids)

    new_cases = pubmed_cases + europe_cases
    combined_cases = new_cases + existing_cases

    with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_cases, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
