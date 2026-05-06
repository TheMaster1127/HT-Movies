import os
import json
import subprocess
import shutil

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
RAW_DATA_DIR = "raw_data"
MOVIES_DIR = os.path.join(RAW_DATA_DIR, "over_10k_movies_jsons")
SHOWS_DIR = os.path.join(RAW_DATA_DIR, "over_10k_shows_jsons")

FINAL_OUT_DIR = os.path.join(RAW_DATA_DIR, "final_output")
FINAL_MOVIES_DIR = os.path.join(FINAL_OUT_DIR, "movies")
FINAL_SHOWS_DIR = os.path.join(FINAL_OUT_DIR, "shows")

MEMORY_FILE = "memory.txt"
STOP_FILE = "do_we_stop.txt"

def setup_directories():
    """Ensure our pristine final output folders exist."""
    os.makedirs(FINAL_MOVIES_DIR, exist_ok=True)
    os.makedirs(FINAL_SHOWS_DIR, exist_ok=True)

def load_queue(folder):
    """Load the sorted priority list."""
    queue = []
    q_file = os.path.join(folder, "_top_ratings.txt")
    if os.path.exists(q_file):
        with open(q_file, 'r') as f:
            for line in f:
                if line.strip():
                    tid, _ = line.strip().split(':')
                    queue.append(tid)
    return queue

def load_memory():
    """Load where we left off, or start at 0."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"movie_index": 0, "show_index": 0}

def save_memory(mem):
    """Save progress after every single item."""
    with open(MEMORY_FILE, 'w') as f:
        json.dump(mem, f, indent=4)

def check_stop():
    """Check if the user wants to pause the engine."""
    if os.path.exists(STOP_FILE):
        with open(STOP_FILE, 'r') as f:
            if f.read().strip() == "1":
                return True
    return False

def reset_stop():
    """Set the stop file back to 0."""
    with open(STOP_FILE, 'w') as f:
        f.write("0")

def process_item(imdb_id, media_type):
    """Call the master pipeline and move the outputs to the final folder."""
    print(f"\n" + "="*60)
    print(f"🎬 ENGINE TRIGGERED: {media_type.upper()} [{imdb_id}]")
    print("="*60)

    # Call your brilliant master_pipeline.py
    result = subprocess.run(["python", "master_pipeline.py", imdb_id])
    
    source_dir = MOVIES_DIR if media_type == 'movie' else SHOWS_DIR
    dest_dir = FINAL_MOVIES_DIR if media_type == 'movie' else FINAL_SHOWS_DIR
    
    source_json = os.path.join(source_dir, f"{imdb_id}.json")
    enrichment_json = f"{imdb_id}_ai_enrichment.json" 
    
    # If the script succeeded (return code 0) and the file exists, move it!
    if result.returncode == 0 and os.path.exists(enrichment_json):
        # 1. Move the enrichment file
        dest_enrichment = os.path.join(dest_dir, f"{imdb_id}_ai_enrichment.json")
        shutil.move(enrichment_json, dest_enrichment)
        
        # 2. Copy the updated original JSON
        dest_source = os.path.join(dest_dir, f"{imdb_id}.json")
        shutil.copy(source_json, dest_source)
        
        print(f"📁 Organised! Saved beautifully to {dest_dir}/")
    else:
        print(f"⚠️ {imdb_id} failed or was skipped. Index moved forward to prevent looping.")
        # Clean up the enrichment file if it somehow generated but the pipeline crashed
        if os.path.exists(enrichment_json):
            os.remove(enrichment_json)

def main():
    setup_directories()
    reset_stop() # Always ensure we start at 0
    
    movies_queue = load_queue(MOVIES_DIR)
    shows_queue = load_queue(SHOWS_DIR)
    memory = load_memory()
    
    print(f"🚀 HT-MOVIES ENGINE STARTING...")
    print(f"📊 Loaded {len(movies_queue):,} movies and {len(shows_queue):,} shows.")
    print(f"📌 Resuming from Movie #{memory['movie_index']}, Show #{memory['show_index']}")
    print(f"🛑 To pause safely, open {STOP_FILE} and change 0 to 1.\n")
    
    while True:
        # Check if we are totally done
        if memory['movie_index'] >= len(movies_queue) and memory['show_index'] >= len(shows_queue):
            print("🎉 ALL ITEMS IN THE DATABASE HAVE BEEN PROCESSED!")
            break
            
        # ---------------------------
        # 1. PROCESS THE NEXT MOVIE
        # ---------------------------
        if memory['movie_index'] < len(movies_queue):
            movie_id = movies_queue[memory['movie_index']]
            process_item(movie_id, 'movie')
            
            # Save state immediately
            memory['movie_index'] += 1
            save_memory(memory)
            
            # Check for emergency stop
            if check_stop():
                print(f"\n🛑 STOP SIGNAL DETECTED in {STOP_FILE}! Halting engine safely...")
                reset_stop()
                break

        # ---------------------------
        # 2. PROCESS THE NEXT SHOW
        # ---------------------------
        if memory['show_index'] < len(shows_queue):
            show_id = shows_queue[memory['show_index']]
            process_item(show_id, 'show')
            
            # Save state immediately
            memory['show_index'] += 1
            save_memory(memory)
            
            # Check for emergency stop
            if check_stop():
                print(f"\n🛑 STOP SIGNAL DETECTED in {STOP_FILE}! Halting engine safely...")
                reset_stop()
                break

if __name__ == "__main__":
    main()
