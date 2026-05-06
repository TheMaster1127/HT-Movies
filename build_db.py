#!/usr/bin/env python3
import sqlite3, json, os, glob

DATA_DIR = "raw_data/final_output"
DB_FILE = "movies.db"

def build_database():
    movies = glob.glob(f"{DATA_DIR}/movies/*.json")
    shows = glob.glob(f"{DATA_DIR}/shows/*.json")
    all_files = movies + shows
    target_files = [f for f in all_files if not f.endswith("_ai_enrichment.json")]
    
    if not target_files:
        print("No JSON files found!")
        return
        
    print(f"Found {len(target_files)} media files. Analyzing schema...")
    ai_keys = {}
    
    for f in target_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if "ai_enrichment" in data:
                    for k, v in data["ai_enrichment"].items():
                        if k not in ai_keys:
                            if isinstance(v, bool): ai_keys[k] = "INTEGER"
                            elif isinstance(v, int): ai_keys[k] = "INTEGER"
                            elif isinstance(v, float): ai_keys[k] = "REAL"
                            else: ai_keys[k] = "TEXT"
        except: pass
            
    schema = {
        "id": "TEXT PRIMARY KEY", "type": "TEXT", "title": "TEXT", 
        "year": "TEXT", "year_int": "INTEGER", 
        "runtime": "TEXT", "runtime_int": "INTEGER", 
        "rating": "REAL", "votes": "INTEGER", "genres": "TEXT", 
        "cast_list": "TEXT", "vibe": "TEXT", "short_summary": "TEXT", 
        "total_seasons": "INTEGER", "total_episodes": "INTEGER", "season_episodes": "TEXT" 
    }
    schema.update(ai_keys)
    
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cols_def = ", ".join([f"{k} {v}" for k, v in schema.items()])
    cursor.execute(f"CREATE TABLE media ({cols_def})")
    
    print("Inserting data...")
    inserted = 0
    
    for idx, f in enumerate(target_files, 1):
        try:
            with open(f, 'r', encoding='utf-8') as file: data = json.load(file)
            if "id" not in data: continue
                
            row = {k: None for k in schema.keys()}
            row["id"] = data.get("id")
            row["type"] = data.get("type")
            row["title"] = data.get("title") or data.get("original_title")
            row["year"] = data.get("year")
            row["runtime"] = data.get("runtime")
            
            try:
                y_str = str(data.get("year", ""))
                row["year_int"] = int(''.join(filter(str.isdigit, y_str))[:4]) if any(c.isdigit() for c in y_str) else 0
            except: row["year_int"] = 0
            
            try:
                r_str = str(data.get("runtime", ""))
                row["runtime_int"] = int(''.join(filter(str.isdigit, r_str))) if any(c.isdigit() for c in r_str) else 0
            except: row["runtime_int"] = 0
            
            try: row["rating"] = float(data.get("rating", 0) or 0)
            except: row["rating"] = 0.0
            try: row["votes"] = int(data.get("votes", 0) or 0)
            except: row["votes"] = 0
                
            row["genres"] = json.dumps(data.get("genres", []))
            
            # Extract Cast smartly
            cast_raw = data.get("cast", [])
            cast_names = [c["name"] for c in cast_raw if "name" in c and c.get("category") in ("actor", "actress")]
            row["cast_list"] = json.dumps(cast_names)
            
            # Fix Season "None" bug
            episodes = data.get("episodes", [])
            season_counts = {}
            for ep in episodes:
                s = str(ep.get("season"))
                if s.lower() in ("none", "null", ""): s = "Specials"
                season_counts[s] = season_counts.get(s, 0) + 1
                
            row["total_seasons"] = len([k for k in season_counts.keys() if k != "Specials"])
            row["total_episodes"] = len(episodes)
            row["season_episodes"] = json.dumps(season_counts)
            
            if "ai_enrichment" in data:
                for k, v in data["ai_enrichment"].items():
                    if k == "short_summary": row["short_summary"] = v
                    elif k == "vibe": row["vibe"] = str(v)
                    elif k in schema:
                        if isinstance(v, bool): row[k] = 1 if v else 0
                        else: row[k] = v
                            
            columns = list(row.keys())
            values = list(row.values())
            placeholders = ", ".join(["?"] * len(columns))
            cursor.execute(f"INSERT INTO media ({', '.join(columns)}) VALUES ({placeholders})", values)
            inserted += 1
            if idx % 100 == 0: print(f"Processed {idx}/{len(target_files)}...")
                
        except Exception as e: print(f"Error processing {f}: {e}")
            
    conn.commit()
    conn.close()
    print(f"✓ Database built successfully! Inserted {inserted} records.")

if __name__ == "__main__": build_database()
