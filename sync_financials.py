import sqlite3, json, os, urllib.request, urllib.parse, time

DB_FILE = "movies.db"
CACHE_FILE = "financials_cache.json"

def chunk_list(lst, n):
    for i in range(0, len(lst), n): yield lst[i:i + n]

def main():
    print("🚀 HT-Movies Hyper-Scraper Initializing...")
    
    # 1. Load existing cache so we don't overwrite it
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: cache = json.load(f)

    # 2. Get all IMDb IDs from your database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM media")
    all_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Filter out ones we already scraped to save time (if you run it twice)
    missing_ids = [m_id for m_id in all_ids if m_id not in cache]
    print(f"📊 Found {len(all_ids)} total movies. {len(missing_ids)} missing financials.")

    # 3. Query Wikidata in massive batches of 300 movies at once!
    chunks = list(chunk_list(missing_ids, 300))
    for idx, batch in enumerate(chunks):
        print(f"🔄 Processing batch {idx+1}/{len(chunks)}...")
        
        # Build a massive SPARQL string injecting 300 IDs
        id_values = " ".join([f'"{m_id}"' for m_id in batch])
        query = f"""
        SELECT ?imdb ?budget ?boxOffice WHERE {{
          VALUES ?imdb {{ {id_values} }}
          ?movie wdt:P345 ?imdb .
          OPTIONAL {{ ?movie wdt:P2130 ?budget . }}
          OPTIONAL {{ ?movie wdt:P2142 ?boxOffice . }}
        }}
        """
        
        url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'HT-Movies-Bot/2.0'})
        
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
                # Pre-fill batch with Nulls so we don't check them again
                for m_id in batch: cache[m_id] = {"budget": None, "box_office": None}
                
                for row in data.get("results", {}).get("bindings", []):
                    m_id = row.get("imdb", {}).get("value")
                    if not m_id: continue
                    
                    b_raw = row.get("budget", {}).get("value")
                    g_raw = row.get("boxOffice", {}).get("value")
                    
                    cache[m_id]["budget"] = float(b_raw) if b_raw else None
                    cache[m_id]["box_office"] = float(g_raw) if g_raw else None
            
            # Save progress after every batch!
            with open(CACHE_FILE, 'w') as f: json.dump(cache, f)
            time.sleep(1) # Polite delay
            
        except Exception as e:
            print(f"💀 Batch failed (will skip for now): {e}")
            time.sleep(3)
            
    print("✅ Financial Sync Complete! Restart your engine!")

if __name__ == "__main__": main()
