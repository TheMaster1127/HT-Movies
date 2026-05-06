import os
import gzip
import csv
import json
import sys

# FIX: Prevent CSV from crashing on massive rows
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

RAW_DATA_DIR = "raw_data"
MOVIES_JSON_DIR = os.path.join(RAW_DATA_DIR, "over_10k_movies_jsons")
SHOWS_JSON_DIR = os.path.join(RAW_DATA_DIR, "over_10k_shows_jsons")

for d in [MOVIES_JSON_DIR, SHOWS_JSON_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def load_ids(filepath):
    if not os.path.exists(filepath):
        print(f"❌ Error: Cannot find {filepath}")
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def extract_all():
    print("🚀 Starting the 'One-Pass' Data Extraction...")
    
    # 1. Load the IDs we care about
    movie_ids = load_ids(os.path.join(RAW_DATA_DIR, "popularity_movies", "over_10k.txt"))
    show_ids = load_ids(os.path.join(RAW_DATA_DIR, "popularity_shows", "over_10k.txt"))
    target_ids = movie_ids.union(show_ids)
    
    print(f"🎯 Target: {len(movie_ids):,} Movies and {len(show_ids):,} Shows (Total: {len(target_ids):,})")

    # 2. Initialize the master dictionary in RAM
    master_data = {}
    for tconst in target_ids:
        master_data[tconst] = {
            "id": tconst,
            "type": "movie" if tconst in movie_ids else "show",
            "title": "", "original_title": "", "year": "", "end_year": "",
            "runtime": "", "genres": [], "rating": "", "votes": "",
            "akas": [], "directors": [], "writers": [], "cast": [], "episodes": []
        }

    person_ids = set() # We will collect all actor/director IDs here to look up their names later

    # 3. Sweep title.basics
    print("🔍 1/7 Sweeping title.basics.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.basics.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['tconst']
            if tconst in master_data:
                master_data[tconst]['title'] = row['primaryTitle']
                master_data[tconst]['original_title'] = row['originalTitle']
                master_data[tconst]['year'] = row['startYear']
                master_data[tconst]['end_year'] = row['endYear'] if row['endYear'] != '\\N' else None
                master_data[tconst]['runtime'] = row['runtimeMinutes'] if row['runtimeMinutes'] != '\\N' else None
                master_data[tconst]['genres'] = row['genres'].split(',') if row['genres'] != '\\N' else []

    # 4. Sweep title.ratings
    print("🔍 2/7 Sweeping title.ratings.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.ratings.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['tconst']
            if tconst in master_data:
                master_data[tconst]['rating'] = row['averageRating']
                master_data[tconst]['votes'] = row['numVotes']

    # 5. Sweep title.akas (Alternative Titles / Translations)
    print("🔍 3/7 Sweeping title.akas.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.akas.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['titleId']
            if tconst in master_data:
                aka_info = {
                    "title": row['title'],
                    "region": row['region'] if row['region'] != '\\N' else None,
                    "language": row['language'] if row['language'] != '\\N' else None
                }
                master_data[tconst]['akas'].append(aka_info)

    # 6. Sweep title.crew (Directors and Writers)
    print("🔍 4/7 Sweeping title.crew.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.crew.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['tconst']
            if tconst in master_data:
                dirs = row['directors'].split(',') if row['directors'] != '\\N' else []
                writers = row['writers'].split(',') if row['writers'] != '\\N' else []
                
                master_data[tconst]['directors'] = [{"id": d, "name": ""} for d in dirs]
                master_data[tconst]['writers'] = [{"id": w, "name": ""} for w in writers]
                
                person_ids.update(dirs)
                person_ids.update(writers)

    # 7. Sweep title.principals (Cast and Crew Roles)
    print("🔍 5/7 Sweeping title.principals.tsv.gz (This is a massive file, wait for it!)...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.principals.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['tconst']
            if tconst in master_data:
                person_id = row['nconst']
                cast_member = {
                    "id": person_id,
                    "category": row['category'],
                    "characters": row['characters'] if row['characters'] != '\\N' else "",
                    "name": "" # We will fill this in the next step
                }
                master_data[tconst]['cast'].append(cast_member)
                person_ids.add(person_id)

    # 8. Sweep title.episode (Link episodes to Shows)
    print("🔍 6/7 Sweeping title.episode.tsv.gz (Finding episodes for our Shows)...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.episode.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            parent = row['parentTconst']
            if parent in show_ids:
                ep_info = {
                    "episode_id": row['tconst'],
                    "season": row['seasonNumber'] if row['seasonNumber'] != '\\N' else None,
                    "episode": row['episodeNumber'] if row['episodeNumber'] != '\\N' else None
                }
                master_data[parent]['episodes'].append(ep_info)

    # 9. Sweep name.basics (Get the actual names of actors/directors)
    print(f"🔍 7/7 Sweeping name.basics.tsv.gz to find {len(person_ids):,} Actor/Director Names...")
    name_lookup = {}
    with gzip.open(os.path.join(RAW_DATA_DIR, "name.basics.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            nconst = row['nconst']
            if nconst in person_ids:
                name_lookup[nconst] = row['primaryName']

    # Inject the real names into our master dictionary
    print("💉 Injecting names into the master data...")
    for tconst, data in master_data.items():
        for d in data['directors']: d['name'] = name_lookup.get(d['id'], "Unknown")
        for w in data['writers']: w['name'] = name_lookup.get(w['id'], "Unknown")
        for c in data['cast']: c['name'] = name_lookup.get(c['id'], "Unknown")

    # 10. Write the 15,000 JSON files!
    print("💾 Saving 15,000+ JSON files to disk... (this might take a minute)")
    movies_saved = 0
    shows_saved = 0
    
    for tconst, data in master_data.items():
        if data['type'] == 'movie':
            filepath = os.path.join(MOVIES_JSON_DIR, f"{tconst}.json")
            movies_saved += 1
        else:
            filepath = os.path.join(SHOWS_JSON_DIR, f"{tconst}.json")
            shows_saved += 1
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    print("\n" + "="*45)
    print(" 🎉 EXTRACTION COMPLETE 🎉")
    print(f" Saved {movies_saved:,} Movie JSONs to: {MOVIES_JSON_DIR}")
    print(f" Saved {shows_saved:,} Show JSONs to:  {SHOWS_JSON_DIR}")
    print("="*45)

if __name__ == "__main__":
    extract_all()
