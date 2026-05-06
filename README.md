## 🎬 HT-Movies
**The Ultimate Highly Advanced, Local-First Cinematic Discovery Engine.**

Have you ever tried to find a specific type of movie or show, but standard streaming services only let you filter by generic categories like Action, Release Year, IMDb Rating, etc.? 

HT-Movies is built to solve that exact problem. Instead of relying only on basic metadata, this engine takes the raw database information and enhances it using a local Language Model. The AI reads the plot, understands the narrative, and creates dozens of new, highly specific tags. This turns subjective storytelling into a strictly filterable offline database, allowing you to search for movies and shows like never before.

**What makes this different?**
* **Hyper-Granular Filtering:** You can filter media by Action Intensity percentages, Setting (Big City vs. Wilderness), the estimated IQ of the main character, and highly specific narrative tags (e.g., are there car chases? Snipers? Superpowers? Does the main character fly?).
* **Strict Inclusion & Exclusion:** Don't just search for what you want—strictly remove what you dislike. You can force-exclude specific genres or AI traits so they never appear in your results.
* **The Cast Engine:** Select your favorite actors to push their movies to the top of your list, or use strict `ANY`/`ALL` logic to only show movies where specific actors share the screen. You can even filter out massive casts by setting a maximum cast size limit.
* **Advanced Multi-Word Search:** Use the Pipe operator (`|`) to search for multiple, space-sensitive keywords simultaneously within a movie's plot, title, or cast (e.g., `heist | action | forest`).
* **Complete UI Customization:** Change the entire color scheme of the interface, move the sidebar tabs to fit your workflow, and save your progress into separate user profiles so you never lose your active filters.
* **100% Offline & Local:** Once the AI finishes parsing your dataset, the entire UI and database run completely offline in a single, lightning-fast interface.

### 🧠 5 Ways You Can Filter Reality
Because the AI generates such a deep matrix of tags, you can combine sliders, toggles, and percentages to run incredibly specific queries. For example:

1. **The Action Enjoyer:** *"Show me a movie with an Action Intensity over 85%, where the main character is a killer/assassin, snipers and car chases are present, but absolutely no romantic subplots."*
2. **The Sci-Fi Detective:** *"Find a Sci-Fi movie set in a Big City, where the main character has an estimated IQ over 130, people have superpowers, but no one can turn invisible or teleport."*
3. **The Gritty Realism Fan:** *"I want a Crime Thriller with a 100% Western cast, zero Sci-Fi elements, where people actually die, and the Russian Mafia is involved."*
4. **The Actor Combo:** *"Show me movies released between 2005 and 2015, with a rating higher than 7.5, that absolutely MUST include Brad Pitt AND Leonardo DiCaprio."*
5. **The Short Binge:** *"Find me a TV Show with a maximum of 3 seasons, fewer than 30 total episodes, a high 'Mystery' vibe, and a highly intelligent female lead character."*

You provide the raw data, the AI parses the narrative, and you get the ultimate control to find exactly what you want to watch. But don't get excited yet, because you would need a good enough GPU and many days of processing before this happens.

---

## 📑 Table of Contents
- [⚠️ LEGAL NOTICE & DISCLAIMER](#️-legal-notice--disclaimer)
- [🚀 How to Use HT-Movies](#-how-to-use-ht-movies)
  - [1. Acquire the Raw Data](#1-acquire-the-raw-data)
  - [2. Install AI Prerequisites](#2-install-ai-prerequisites)
  - [3. Run the Processing Pipeline](#3-run-the-processing-pipeline)
  - [4. Build and View the Database](#4-build-and-view-the-database)
- [⚙️ System Quirks & Architecture Notes](#️-system-quirks--architecture-notes)
- [📜 Licensing (GNU GPL v3)](#-licensing-gnu-gpl-v3)
- [📛 LEGAL WARNING & USER RESPONSIBILITY](#-legal-warning--user-responsibility)

---

## ⚠️ LEGAL NOTICE & DISCLAIMER
HT-Movies is provided strictly for educational and personal research purposes.

* NO DATA DISTRIBUTION: This repository contains zero movie records, metadata, or database files.
* USER RESPONSIBILITY: Users are 100% responsible for their own data acquisition. By using this tool, you agree to abide by the [IMDb Conditions of Use](https://www.imdb.com/conditions/).
* LOCAL USE ONLY: This software is designed to run on a localhost environment. Any commercial use or public redistribution of the resulting processed data is strictly prohibited by the data source providers.
* BYOD (Bring Your Own Data): This is a software engine only. You provide the fuel; we provide the engine.

---

## 🚀 How to Use HT-Movies

### 1. Acquire the Raw Data
You must manually download the official datasets from IMDb.

* Source URL: https://datasets.imdbws.com/
* Files Required: You must download ALL of the following files:
   * `name.basics.tsv.gz`
   * `title.akas.tsv.gz`
   * `title.basics.tsv.gz`
   * `title.crew.tsv.gz`
   * `title.episode.tsv.gz`
   * `title.principals.tsv.gz`
   * `title.ratings.tsv.gz`

**Important:** These files must be placed directly into the `raw_data/` folder. Do not extract them. The HT-Movies scripts are designed to read these compressed files directly to save disk space.

### 2. Install AI Prerequisites
This project relies on Ollama for local AI processing.

1. Download and install [Ollama](https://ollama.com/).
2. Open your terminal and pull the required model:
   ```bash
   ollama pull deepseek-r1:8b
   ```
*Note: DeepSeek-R1 8B is the default because it offers the perfect balance between intelligent reasoning and hardware efficiency. If you have substantial GPU power and wish to use a larger or different model, you can change the model name inside `master_pipeline.py` line 297 (look for the `subprocess.run` command invoking Ollama).*

### 3. Run the Processing Pipeline
The data processing is split into several stages. Run these scripts in order from the root directory:

**Step 3.1: Filter the Dataset**
```bash
python get_info.py
```
This scans the massive IMDb files and filters for English/US/UK regions, sorting them by vote thresholds. We target media with >10,000 votes, which equates to roughly ~15,000 highly-rated movies and shows.

**Step 3.2: Extract Base JSONs**
```bash
python get_json_top10k.py
```
This extracts the standard metadata (cast, runtime, rating, genres) for the targeted movies and shows into the `raw_data/over_10k_movies_jsons` and `raw_data/over_10k_shows_jsons` folders.

**Step 3.3: Build Priority Queues**
```bash
python sort_by_votes.py
```
This script sorts the extracted items by popularity. The AI will process the most voted-on (most popular) movies and shows first.

**Step 3.4: Start the AI Engine**
Before running the main AI pipeline, ensure the Ollama service is running in the background. If it isn't running natively, start it in a separate terminal:
```bash
ollama serve
```
Then, start the extraction loop:
```bash
python final.py
```
**Time Expectation:** Processing ~15,000 entries will take days to weeks depending heavily on your GPU. The engine automatically processes one movie, then one show, moving down the popularity list.

**How to safely stop the engine:** 
Do not `CTRL+C` while the AI is writing. Open the `do_we_stop.txt` file, change the `0` to a `1`, and save it. The script will finish its current movie and shut down gracefully.

### 4. Build and View the Database
You do not have to wait weeks for `final.py` to finish. You can use the UI and browse whatever the AI has processed so far at any time.

1. If you are updating an existing database, delete it first to avoid conflicts:
   ```bash
   rm movies.db
   ```
2. Compile the processed AI JSONs into SQLite:
   ```bash
   python build_db.py
   ```
3. Start the Web UI Backend:
   ```bash
   python app.py
   ```
4. Open your web browser and navigate to: `http://localhost:8000`

---

## ⚙️ System Quirks & Architecture Notes

* **OS Compatibility:** This software was built and heavily tested on Artix Linux. It relies on bash pipes and native Unix commands. It may run smoothly on other Unix-like systems and WSL (Windows Subsystem for Linux), but native Windows CMD/PowerShell is not supported.
* **Wikipedia Accuracy:** The pipeline automatically scrapes Wikipedia for plot summaries to feed the AI. Sometimes Wikipedia redirects incorrectly, provides an ambiguous page, or lacks a plot entirely. Because of this, the AI may occasionally hallucinate or classify data based on the wrong film. This is the inherent price of fully automated, unassisted scraping. If you know how to fix or improve the Wikipedia routing logic, feel free to do so.
* **Hardware Scaling:** If you have access to a server farm or multiple GPUs, you are entirely free to rewrite the pipeline scripts to process entries concurrently. 

---

## 📜 Licensing (GNU GPL v3)
This software (the source code, scripts, and UI logic) is licensed under the GNU GPL v3 License.

* **Personal Use:** You can modify, break, and run this code privately as much as you want.
* **Distribution:** If you modify this source code and distribute or host it publicly, you **must** open-source your modifications under the same GPL v3 license.
* **The Data:** This license applies **only** to the original code written for HT-Movies. It does not grant any rights to the IMDb data processed by the tool.

Educational Purpose: This project was built to demonstrate local AI data-enrichment for movies and shows. Use responsibly.

## 📛 LEGAL WARNING & USER RESPONSIBILITY

**This software is a tool – it does not contain, host, or distribute any IMDb data. However, the data you process with this tool is subject to IMDb's own legal terms.**

By using HT‑Movies to download or process data from IMDb, you agree to be bound by the **[IMDb Conditions of Use](https://www.imdb.com/conditions/)**. In particular, note that IMDb’s terms:

- Allow the data to be used **only for personal, non‑commercial purposes**.
- **Forbid** any alteration, republishing, reselling, or repurposing of the data to create a new database (except for individual personal use).
- **Forbid** the redistribution of any derived database, whether modified or not.

**Your responsibilities:**  
- You must manually download the raw IMDb data from [datasets.imdbws.com](https://datasets.imdbws.com/).  
- Any database you create using HT‑Movies is a **derived work** of IMDb’s copyrighted data.  
- You may **not** share, upload, or commercially exploit that derived database.  
- The GNU GPLv3 license that covers the **source code** of HT‑Movies **does not** apply to the IMDb data or to any database you generate with it.

**Disclaimer of liability:** The author of HT‑Movies provides this software for educational and research purposes only. The author does not encourage or condone any violation of IMDb’s terms. You are solely responsible for your own compliance with all applicable licenses and laws.
