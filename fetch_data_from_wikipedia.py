import sys
import subprocess
import urllib.parse
import urllib.request
import json

def fetch_movie_data():
    # 1. Ensure the user provided a query
    if len(sys.argv) < 2:
        print('❌ Error: Please provide a query. Example: python fetch_data_from_wikipedia.py "The beekeeper 2024"')
        sys.exit(1)

    query = sys.argv[1]
    print(f"🎬 Searching for: '{query}'")

    # Encode the query so spaces become '+' for the URL
    encoded_query = urllib.parse.quote_plus(query)

    # 2. YOUR GENIUS BASH COMMAND
    # We pass this exactly as you wrote it straight into the Linux shell
    bash_cmd = f"""curl -s -A 'HT-Movies/1.0' 'https://en.wikipedia.org/w/index.php?search={encoded_query}&title=Special%3ASearch&ns0=1' | grep -oP 'href="/wiki/\K[^"]+(?=")' | awk '!/:/ && !/Main_Page/ {{print "https://en.wikipedia.org/wiki/"$0; exit}}'"""

    try:
        # Run the bash command and capture the output
        print("⚡ Running the master curl command...")
        result = subprocess.check_output(bash_cmd, shell=True, executable='/bin/bash')
        wiki_url = result.decode('utf-8').strip()
        
        if not wiki_url:
            print(f"❌ Could not find a Wikipedia page for '{query}'")
            sys.exit(1)
            
        print(f"🔗 Found URL: {wiki_url}")

        # 3. Parse the JSON text exactly as you requested
        # We extract the title slug from the end of your URL (e.g., "The_Beekeeper_(2024_film)")
        page_title = wiki_url.split('/')[-1]
        
        # Hit the Wikipedia API for the pure, raw JSON text
        api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&titles={page_title}&explaintext=1&format=json"
        
        print("📄 Parsing the JSON data...")
        req = urllib.request.Request(api_url, headers={'User-Agent': 'HT-Movies/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            
        # Extract the pure text from the JSON
        pages = data.get('query', {}).get('pages', {})
        page_id = list(pages.keys())[0]
        raw_text = pages[page_id].get('extract', '')

        if not raw_text:
            print("❌ Found the page, but no text was extracted.")
            sys.exit(1)

        # 4. Dump it to the text file with your exact requested formatting
        output_filename = "wikipedia_extracted_data_raw.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(f"{query}\n\n")  # The parameter, a new line, and an empty line
            f.write(raw_text)        # The raw dump

        print(f"✅ Flawless victory! Data saved to {output_filename}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Bash command failed: {e}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    fetch_movie_data()
