import os
from bs4 import BeautifulSoup

def extract_all_raw_text(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_blocks = []
    
    # Grab all structural text elements
    for element in soup.find_all(['p', 'li', 'h2', 'h3']):
        
        # 1. THE SHIELD: If this text is inside a table, infobox, navbox, or references, ignore it.
        # This completely bypasses the HTML bug that broke the Sarnitsa page.
        bad_parent = element.find_parent(
            ['table', 'div', 'ol', 'ul'], 
            class_=lambda c: c and any(bad in c for bad in ['infobox', 'navbox', 'reflist', 'references', 'metadata'])
        )
        if bad_parent:
            continue
            
        # 2. Clean the tiny [1] and [2] citations out of the text
        for sup in element.find_all('sup'):
            sup.decompose()
            
        # 3. Extract the clean text
        text = element.get_text(separator=' ', strip=True)
        
        # 4. Only keep actual sentences (20+ characters)
        if len(text) >= 20:
            extracted_blocks.append(text)
            
    return "\n\n".join(extracted_blocks)

if __name__ == "__main__":
    file_path = "raw_dump.html"
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html_data = f.read()
            
        print("🌪️ Vacuuming all raw text from HTML (Safely)...")
        final_text = extract_all_raw_text(html_data)
        
        with open("clean_dump.txt", "w", encoding="utf-8") as out:
            out.write(final_text)
            
        print("✅ DONE! Check clean_dump.txt")
    else:
        print(f"❌ Error: Cannot find {file_path}")