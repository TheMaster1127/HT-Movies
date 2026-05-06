import os
import json

def sort_and_save_queue(directory):
    print(f"📂 Scanning directory: {directory}")
    
    if not os.path.exists(directory):
        print(f"❌ Error: {directory} does not exist.")
        return

    items = []
    
    # 1. Loop through all JSON files
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    movie_id = data.get('id')
                    # Convert votes to an integer so it sorts numerically, not alphabetically!
                    votes = int(data.get('votes', 0)) 
                    
                    if movie_id:
                        items.append((movie_id, votes))
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

    # 2. Sort the list by the number of votes in descending order (highest first)
    items.sort(key=lambda x: x[1], reverse=True)
    
    # 3. Save to a text file inside the same folder
    # I added an underscore at the start so it always appears at the top of your folder!
    output_file = os.path.join(directory, "_top_ratings.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item_id, votes in items:
            f.write(f"{item_id}:{votes}\n")
            
    print(f"✅ Sorted {len(items):,} files. Queue saved to: {output_file}\n")

if __name__ == "__main__":
    movies_dir = os.path.join("raw_data", "over_10k_movies_jsons")
    shows_dir = os.path.join("raw_data", "over_10k_shows_jsons")
    
    print("🚀 Building the Priority Processing Queues...\n")
    sort_and_save_queue(movies_dir)
    sort_and_save_queue(shows_dir)
