# 🚧 Under construction 🚧
# 🚧 Under construction 🚧
## Do not use this project yet. It's under construction. When you no longer see this message, you can proceed to use this project. Until then, do not use this project.
# 🚧 Under construction 🚧
# 🚧 Under construction 🚧

---

## 🎬 HT-Movies
A high-performance, local-first movie discovery engine.

---

## ⚠️ LEGAL NOTICE & DISCLAIMER
HT-Movies is provided strictly for educational and personal research purposes.

* NO DATA DISTRIBUTION: This repository contains zero movie records, metadata, or database files.
* USER RESPONSIBILITY: Users are 100% responsible for their own data acquisition. By using this tool, you agree to abide by the [IMDb Conditions of Use](https://www.imdb.com/conditions/).
* LOCAL USE ONLY: This software is designed to run on a localhost environment. Any commercial use or public redistribution of the resulting processed data is strictly prohibited by the data source providers.
* BYOD (Bring Your Own Data): This is a software engine only. You provide the fuel; we provide the engine.

---

## 🚀 How to Use HT-Movies## 1. Acquire the Raw Data
You must manually download the official datasets from IMDb.

* Source URL: https://datasets.imdbws.com/
* Files Required: You must download ALL of the following files:
   * name.basics.tsv.gz
   * title.akas.tsv.gz
   * title.basics.tsv.gz
   * title.crew.tsv.gz
   * title.episode.tsv.gz
   * title.principals.tsv.gz
   * title.ratings.tsv.gz

Note on .gz files: These are compressed "Gzip" files. Do not extract them. The HT-Movies scripts are designed to read these compressed files directly to save you disk space. Place all seven files into the /raw_data folder.
## 2. Install AI Prerequisites1
This project uses Ollama for local AI processing.

   1. Download/Install [Ollama](https://ollama.com/).
   2. Open your terminal and run: ollama pull [MODEL_NAME] (e.g., ollama pull mistral).

## 3. Run the Processing Pipeline

To run ...

---

## 📜 Licensing
This software (the source code and UI logic) is licensed under the GNU GPL v3 License.

* This license applies only to the original code written for HT-Movies.
* It does not grant any rights to the data processed by the tool.
* A copy of the license is included in the LICENSE file in this repository.

Educational Purpose: This project was built to demonstrate local AI data-enrichment and browser-based data management. Use responsibly.
