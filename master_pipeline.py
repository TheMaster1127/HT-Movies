import os
import sys
import json
import subprocess
import re

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
RAW_DATA_DIR = "raw_data"
MOVIES_DIR = os.path.join(RAW_DATA_DIR, "over_10k_movies_jsons")
SHOWS_DIR = os.path.join(RAW_DATA_DIR, "over_10k_shows_jsons")
WIKI_OUTPUT = "wikipedia_extracted_data_raw.txt"
AI_PROMPT_TMP = "current_prompt.txt"
AI_OUTPUT = "AI_Output.txt"

MAX_AI_RETRIES = 10          # Keep trying until valid JSON is received

# ==========================================
# 🧠 PROMPT (unchanged, used for validation)
# ==========================================
PROMPT_INSTRUCTIONS = """
You are an elite film analysis AI. Output ONLY a STRICT JSON object. No intro, no summary, no markdown. 

Definitions:
- Western/White Cast: Actors with names from USA, UK, Europe, Russia, Canada, Australia.
- Eastern/Brown/Asian-Looking Cast: Actors with names from India (Bollywood), Asia, Middle East.
- Action Intensity: 100% is non-stop combat (Die Hard), 0% is a talky drama.

Required JSON structure (Every key must exist):
{
  "short_summary": "2-sentence spoiler-free summary. DO NOT use newlines inside the string.",
  "vibe": "3-word description",
  "western_cast_percentage": 0, 
  "eastern_cast_percentage": 0,
  "action_intensity_percentage": 0,
  "sci_fi_percentage": 0,
  "is_bollywood": false,
  "is_main_character_male": false,
  "is_main_character_female": false,
  "is_anyone_runaway_boy": false,
  "is_anyone_runaway_son": false,
  "is_anyone_runaway_female": false,
  "is_anyone_runaway_daughter": false,
  "is_anyone_runaway_mother": false,
  "is_anyone_runaway_father": false,
  "is_anyone_runaway_grandfather": false,
  "is_anyone_runaway_grandmother": false,
  "is_russian_mafia_present": false,
  "is_main_actor_russian": false,
  "is_romantic_sexual_subplot_present": false,
  "main_actor_count": 0,
  "is_setting_big_city": false,
  "is_setting_village": false,
  "is_setting_wilderness": false,
  "is_military_present": false,
  "are_snipers_present": false,
  "are_car_chases_present": false,
  "is_main_character_child": false,
  "is_main_character_killer_assassin": false,
  "do_people_die": false,
  "has_anyone_superpowers": false,
  "is_anyone_invincible": false,
  "can_anyone_fly": false,
  "can_anyone_shoot_lasers_from_eyes": false,
  "can_anyone_become_invisible": false,
  "can_anyone_teleport": false,
  "can_anyone_read_minds": false,
  "is_intelligence_extremely_smart": false,
  "is_intelligence_smart": false,
  "is_intelligence_average": false,
  "is_intelligence_dumb": false,
  "is_intelligence_extremely_dumb": false,
  "main_character_estimated_iq": 0
}
"""

# Extract the expected keys and their types from the JSON example
EXPECTED_KEYS = {
    "short_summary": str,
    "vibe": str,
    "western_cast_percentage": int,
    "eastern_cast_percentage": int,
    "action_intensity_percentage": int,
    "sci_fi_percentage": int,
    "is_bollywood": bool,
    "is_main_character_male": bool,
    "is_main_character_female": bool,
    "is_anyone_runaway_boy": bool,
    "is_anyone_runaway_son": bool,
    "is_anyone_runaway_female": bool,
    "is_anyone_runaway_daughter": bool,
    "is_anyone_runaway_mother": bool,
    "is_anyone_runaway_father": bool,
    "is_anyone_runaway_grandfather": bool,
    "is_anyone_runaway_grandmother": bool,
    "is_russian_mafia_present": bool,
    "is_main_actor_russian": bool,
    "is_romantic_sexual_subplot_present": bool,
    "main_actor_count": int,
    "is_setting_big_city": bool,
    "is_setting_village": bool,
    "is_setting_wilderness": bool,
    "is_military_present": bool,
    "are_snipers_present": bool,
    "are_car_chases_present": bool,
    "is_main_character_child": bool,
    "is_main_character_killer_assassin": bool,
    "do_people_die": bool,
    "has_anyone_superpowers": bool,
    "is_anyone_invincible": bool,
    "can_anyone_fly": bool,
    "can_anyone_shoot_lasers_from_eyes": bool,
    "can_anyone_become_invisible": bool,
    "can_anyone_teleport": bool,
    "can_anyone_read_minds": bool,
    "is_intelligence_extremely_smart": bool,
    "is_intelligence_smart": bool,
    "is_intelligence_average": bool,
    "is_intelligence_dumb": bool,
    "is_intelligence_extremely_dumb": bool,
    "main_character_estimated_iq": int,
}

# ==========================================
# Utilities
# ==========================================
def remove_ansi_escapes(text):
    """Strip ANSI escape sequences (terminal control codes) from text."""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
    return ansi_escape.sub('', text)

def strip_thinking_section(text):
    """Remove everything from 'Thinking...' to '...done thinking.' (multi-line, non-greedy)."""
    pattern = r'^Thinking[^\n]*\n.*?^\.\.\.done thinking\.\s*'
    return re.sub(pattern, '', text, flags=re.DOTALL | re.MULTILINE)

def fix_multiline_strings(json_text):
    """Replace newline characters inside JSON strings with spaces."""
    result = []
    in_string = False
    escape = False
    for ch in json_text:
        if escape:
            result.append(ch)
            escape = False
        elif ch == '\\':
            result.append(ch)
            escape = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch in ('\n', '\r'):
            result.append(' ')
        else:
            result.append(ch)
    return ''.join(result)

def extract_json_from_markdown(raw_text):
    """Extract JSON from a ```json block, or fallback to first { ... }."""
    match = re.search(r'```json\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return raw_text[start:end+1].strip()
    return None

def clean_and_parse_json(raw_text):
    """
    Full pipeline:
      1. Remove ANSI escape codes
      2. Strip the "Thinking... ...done thinking." block
      3. Extract the JSON content
      4. Fix multiline strings
      5. Parse with strict=False
      6. Fallback: remove all newlines globally
    """
    cleaned = remove_ansi_escapes(raw_text)
    cleaned = strip_thinking_section(cleaned)
    json_candidate = extract_json_from_markdown(cleaned)
    if not json_candidate:
        return None
    fixed = fix_multiline_strings(json_candidate)
    try:
        return json.loads(fixed, strict=False)
    except Exception:
        flattened = re.sub(r'[\n\r\t]', ' ', fixed)
        try:
            return json.loads(flattened)
        except Exception:
            return None

def validate_enrichment(data):
    """
    Check that `data` is a dict containing exactly the keys in EXPECTED_KEYS,
    with each value having the correct type.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Output is not a JSON object"

    # Check for missing keys
    missing = [k for k in EXPECTED_KEYS if k not in data]
    if missing:
        return False, f"Missing keys: {missing}"

    # Check for extra keys
    extra = [k for k in data if k not in EXPECTED_KEYS]
    if extra:
        return False, f"Extra keys not allowed: {extra}"

    # Check type of each value
    for key, expected_type in EXPECTED_KEYS.items():
        value = data[key]
        if not isinstance(value, expected_type):
            # bool is a subclass of int in Python, but we want exact bool vs int
            if expected_type == bool and isinstance(value, bool):
                continue
            if expected_type == int and isinstance(value, int) and not isinstance(value, bool):
                continue
            return False, f"Key '{key}' should be {expected_type.__name__}, got {type(value).__name__}"

    # Additional semantic checks (optional, but safe)
    # Percentages should be between 0 and 100 (warn but don't fail)
    # For strictness, we could fail, but we'll only warn.
    for pct_key in ['western_cast_percentage', 'eastern_cast_percentage',
                    'action_intensity_percentage', 'sci_fi_percentage']:
        val = data[pct_key]
        if not (0 <= val <= 100):
            print(f"⚠️ Warning: {pct_key} = {val} is out of 0-100 range")

    return True, ""

# ==========================================
# Core processing for a single ID
# ==========================================
def process_imdb_id(imdb_id):
    """
    Find the JSON file for the given IMDb ID, fetch Wikipedia,
    run DeepSeek-R1 8B, extract and validate the enrichment JSON, and save it.
    Retries up to MAX_AI_RETRIES times.
    """
    # Locate the movie/show JSON file
    possible_folders = [MOVIES_DIR, SHOWS_DIR]
    item = None
    for folder in possible_folders:
        file_path = os.path.join(folder, f"{imdb_id}.json")
        if os.path.exists(file_path):
            item = {'id': imdb_id, 'folder': folder}
            break

    if item is None:
        print(f"❌ File for IMDb ID '{imdb_id}' not found in movies or shows.")
        sys.exit(1)

    file_path = os.path.join(item['folder'], f"{item['id']}.json")
    with open(file_path, 'r') as f:
        movie = json.load(f)

    if 'title' not in movie:
        print("❌ JSON file missing 'title' field. Cannot proceed.")
        sys.exit(1)

    title = movie['title']
    year = movie.get('year', '')
    media_type = 'movie' if 'movies' in item['folder'] else 'show'
    query = f"{title} {year} film" if media_type == 'movie' else f"{title} series"

    # Step 1: Fetch Wikipedia
    print(f"\n🌍 [STEP 1] Fetching Wiki: {query}")
    subprocess.run(['python', 'fetch_data_from_wikipedia.py', query])
    if not os.path.exists(WIKI_OUTPUT):
        print("⚠️ Wikipedia output missing. Aborting.")
        sys.exit(1)
    with open(WIKI_OUTPUT, 'r') as wf:
        wiki_content = wf.read()

    # Prepare prompt context
    context = {k: v for k, v in movie.items() if k not in ('ai_enrichment', 'akas')}
    readable_context = json.dumps(context, indent=2)

    with open(AI_PROMPT_TMP, 'w') as pf:
        pf.write("--- MOVIE METADATA ---\n" + readable_context)
        pf.write("\n\n--- WIKIPEDIA ARTICLE ---\n" + wiki_content)
        pf.write(PROMPT_INSTRUCTIONS)
        pf.write("\n\nYou must output in JSON only\n")

    # Step 2: Run the LLM with retries until valid JSON or max attempts
    for attempt in range(1, MAX_AI_RETRIES + 1):
        print(f"🤖 [STEP 2] AI attempt {attempt}/{MAX_AI_RETRIES}...")
        if os.path.exists(AI_OUTPUT):
            os.remove(AI_OUTPUT)

        subprocess.run(
            f'ollama run deepseek-r1:8b < {AI_PROMPT_TMP} >> {AI_OUTPUT}',
            shell=True, executable='/bin/bash'
        )

        with open(AI_OUTPUT, 'r') as af:
            raw_ai = af.read()

        # Parse JSON
        ai_json = clean_and_parse_json(raw_ai)
        if ai_json is None:
            print(f"❌ Failed to parse JSON from AI output (attempt {attempt})")
            if attempt == MAX_AI_RETRIES:
                print("\n--- RAW AI OUTPUT (last 3000 chars) ---")
                print(repr(raw_ai[-3000:]))
                sys.exit(1)
            continue

        # Validate schema
        is_valid, error_msg = validate_enrichment(ai_json)
        if is_valid:
            # Success: update movie file and save standalone enrichment
            movie['ai_enrichment'] = ai_json
            with open(file_path, 'w') as f:
                json.dump(movie, f, indent=4)
            print("✅ Movie JSON updated with enrichment.")

            enrichment_file = f"{imdb_id}_ai_enrichment.json"
            with open(enrichment_file, 'w') as ef:
                json.dump(ai_json, ef, indent=4, ensure_ascii=False)
            print(f"✅ Standalone enrichment saved to {enrichment_file}")

            print(f"🎬 Enrichment complete for '{title}' ({year})")
            return
        else:
            print(f"❌ Validation failed on attempt {attempt}: {error_msg}")
            if attempt == MAX_AI_RETRIES:
                print("\n--- RAW AI OUTPUT (last 3000 chars) ---")
                print(repr(raw_ai[-3000:]))
                sys.exit(1)

# ==========================================
# Entry point
# ==========================================
def main():
    if len(sys.argv) != 2:
        print("Usage: python master_pipeline.py <IMDb_ID>")
        print("Example: python master_pipeline.py tt7456310")
        sys.exit(1)

    imdb_id = sys.argv[1].strip()
    if not imdb_id.startswith("tt"):
        print("❌ IMDb ID must start with 'tt'.")
        sys.exit(1)

    process_imdb_id(imdb_id)

if __name__ == "__main__":
    main()