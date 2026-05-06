import os
import gzip
import csv
import json
import sys

# FIX: Increase the CSV field size limit to the maximum possible for your system
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

# Paths
RAW_DATA_DIR = "raw_data"
MOVIES_DIR = os.path.join(RAW_DATA_DIR, "popularity_movies")
SHOWS_DIR = os.path.join(RAW_DATA_DIR, "popularity_shows")

# Create the directories
for directory in [MOVIES_DIR, SHOWS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"📁 Created directory: {directory}")

def calculate_stats():
    # Base ID sets
    movie_ids = set()
    show_ids = set()
    english_movie_ids = set()
    english_show_ids = set()
    
    # Dictionaries to hold our threshold sets and stats cleanly
    movies_data = {
        "rated_count": 0,
        "1k": set(), "5k": set(), "10k": set(), "50k": set(), "100k": set(), "250k": set()
    }
    
    shows_data = {
        "rated_count": 0,
        "1k": set(), "5k": set(), "10k": set(), "50k": set(), "100k": set(), "250k": set()
    }

    # Step 1: Get ALL movies and shows
    print("🔍 Step 1/3: Finding all Movies and Shows in title.basics.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.basics.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            t_type = row['titleType']
            if t_type == 'movie':
                movie_ids.add(row['tconst'])
            elif t_type in ['tvSeries', 'tvMiniSeries']:
                show_ids.add(row['tconst'])
                
    print(f"   Found {len(movie_ids):,} total movies globally.")
    print(f"   Found {len(show_ids):,} total shows globally.")

    # Step 2: Filter to English / US / UK region
    print("\n🔍 Step 2/3: Filtering for English regions in title.akas.tsv.gz...")
    print("   (This is the biggest file, hang tight...)")
    valid_regions = {'US', 'GB', 'CA', 'AU', 'NZ'}
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.akas.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            title_id = row['titleId']
            is_english = (row['region'] in valid_regions or row['language'] == 'en')
            
            if is_english:
                if title_id in movie_ids:
                    english_movie_ids.add(title_id)
                elif title_id in show_ids:
                    english_show_ids.add(title_id)
                    
    print(f"   Found {len(english_movie_ids):,} English movies.")
    print(f"   Found {len(english_show_ids):,} English shows.")

    # Step 3: Count the votes!
    print("\n🔍 Step 3/3: Counting votes in title.ratings.tsv.gz...")
    with gzip.open(os.path.join(RAW_DATA_DIR, "title.ratings.tsv.gz"), 'rt', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tconst = row['tconst']
            votes = int(row['numVotes'])
            
            # Helper function to add to the right sets
            def process_thresholds(data_dict):
                data_dict["rated_count"] += 1
                if votes > 1000: data_dict["1k"].add(tconst)
                if votes > 5000: data_dict["5k"].add(tconst)
                if votes > 10000: data_dict["10k"].add(tconst)
                if votes > 50000: data_dict["50k"].add(tconst)
                if votes > 100000: data_dict["100k"].add(tconst)
                if votes > 250000: data_dict["250k"].add(tconst)

            if tconst in english_movie_ids:
                process_thresholds(movies_data)
            elif tconst in english_show_ids:
                process_thresholds(shows_data)

    # Step 4: Helper to save everything
    def save_category_data(directory, global_count, english_count, data_dict):
        # Save text files
        for key in ["1k", "5k", "10k", "50k", "100k", "250k"]:
            filepath = os.path.join(directory, f"over_{key}.txt")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(data_dict[key]))
                
        # Build and save info.json
        stats = {
            "total_globally": global_count,
            "total_english": english_count,
            "total_english_with_ratings": data_dict["rated_count"],
            "over_1k_votes": len(data_dict["1k"]),
            "over_5k_votes": len(data_dict["5k"]),
            "over_10k_votes": len(data_dict["10k"]),
            "over_50k_votes": len(data_dict["50k"]),
            "over_100k_votes": len(data_dict["100k"]),
            "over_250k_votes": len(data_dict["250k"])
        }
        with open(os.path.join(directory, "info.json"), 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4)

    print("\n💾 Step 4/4: Saving IDs to text files...")
    save_category_data(MOVIES_DIR, len(movie_ids), len(english_movie_ids), movies_data)
    save_category_data(SHOWS_DIR, len(show_ids), len(english_show_ids), shows_data)

    print("✅ DONE! Check popularity_movies and popularity_shows folders.")

if __name__ == "__main__":
    calculate_stats()
