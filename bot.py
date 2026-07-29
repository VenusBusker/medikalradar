import os
import xml.etree.ElementTree as ET
import requests
from deep_translator import GoogleTranslator

os.makedirs("docs", exist_ok=True)

# PubMed API üzerinden son yayınlanan Vaka Raporlarını (Case Reports) çekme
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def fetch_case_reports():
    try:
        # "case reports" filtresi ile son makaleleri ara
        params = {
            "db": "pubmed",
            "term": "case report[Publication Type] AND free full text[sb]",
            "retmax": "5",
            "sort": "pub_date",
            "retmode": "json"
        }
        res = requests.get(PUBMED_SEARCH_URL, params=params, timeout=10)
        id_list = res.json()["esearchresult"]["idlist"]

        # Makale detaylarını XML olarak çek
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml"
        }
        xml_res = requests.get(PUBMED_FETCH_URL, params=fetch_params, timeout=15)
        root = ET.fromstring(xml_res.content)

        cases = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.find(".//PMID").text
            title = article.find(".//ArticleTitle").text or "Untitled Case"
            
            abstract_elem = article.find(".//Abstract/AbstractText")
            abstract = abstract_elem.text if abstract_elem is not None else "Abstract not available."
            
            # Çok uzun özetleri kırp
            if len(abstract) > 1200:
                abstract = abstract[:1200] + "..."

            cases.append({
                "pmid": pmid,
                "title_en": title,
                "abstract_en": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })
        return cases
    except Exception as e:
        print(f"PubMed veri çekme hatası: {e}")
        return []

def translate_text(text, target_lang='tr'):
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        chunks = [text[i:i+3000] for i in range(0, len(text), 3000)]
        translated = [translator.translate(c) for c in chunks]
        return " ".join(translated)
    except:
        return text

def build_site():
    cases = fetch_case_reports()
    
    # Vakaları çevir
    for case in cases:
        print(f"İşleniyor PMID: {case['pmid']}")
        case["title_tr"] = translate_text(case["title_en"], "tr")
        case["abstract_tr"] = translate_text(case["abstract_en"], "tr")

    # HTML Şablonu (Editoryal Tıp Gazetesi - Neşter Keskinliğinde Arayüz)
    html_content = f"""




MedikalRadar | Klinik Vaka & Analiz






    MEDİKALRADAR
    TR | EN





    PubMed veritabanından anlık çekilen açık erişimli klinik vaka analizleri.



"""

    for c in cases:
        html_content += f"""
    
        Klinik Vaka · PMID: {c['pmid']}
        
        {c['title_tr']}
        {c['title_en']}

        {c['abstract_tr']}
        {c['abstract_en']}

        
            
                💡 Vaka Detayı & Kaynak
                💡 Case Details & Source
            
            
                Bu olgu raporunun tamamına ve klinik gidişatına orijinal PubMed yayını üzerinden erişebilirsiniz.
                You can access the full report and clinical outcome directly on PubMed.
                PubMed Kaynağına Git (PMID: {c['pmid']}) ↗
            
        
    
"""

    html_content += """







"""
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    build_site()
