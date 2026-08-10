#!/usr/bin/env python3
import sqlite3, json, os, re, urllib.request, urllib.parse, time
from flask import Flask, request, jsonify, make_response, send_from_directory

app = Flask(__name__, static_folder='website', static_url_path='')
USER_DATA_FILE = "website_local_storage.json"
POSTER_CACHE_FILE = "poster_cache.json"
FIN_CACHE_FILE = "financials_cache.json"

# Create physical directory for true offline image storage
POSTER_DIR = os.path.join("website", "posters")
os.makedirs(POSTER_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect("movies.db")
    conn.row_factory = sqlite3.Row
    return conn

def load_user_data():
    default_profile = {"rejected": [], "hidden": [], "watch_later": {}, "preferred_cast": [], "banned_cast": [], "colors": {}, "section_order": {}, "filters": {}, "show_posters": True}
    if not os.path.exists(USER_DATA_FILE):
        return {"profiles": {"Default": default_profile}, "current_profile": "Default"}
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"profiles": {"Default": default_profile}, "current_profile": "Default"}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

def load_json_cache(filename):
    if not os.path.exists(filename): return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_json_cache(data, filename):
    with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f)

poster_cache = load_json_cache(POSTER_CACHE_FILE)
fin_cache = load_json_cache(FIN_CACHE_FILE)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS', 'GET'])
@app.route('/<path:path>', methods=['OPTIONS'])
def index(path):
    if request.method == 'OPTIONS': return make_response(), 200
    return send_from_directory('website', 'index.html')

@app.route("/api/user_data", methods=["GET", "POST"])
def user_data_endpoint():
    if request.method == "GET": return jsonify({"success": True, "data": load_user_data()})
    else: save_user_data(request.json); return jsonify({"success": True})

@app.route("/api/poster", methods=["POST"])
def get_poster():
    data = request.json or {}
    title = data.get("title", "")
    imdb_id = data.get("id", "")
    if not title or not imdb_id: return jsonify({"url": ""})
    
    local_url = f"/posters/{imdb_id}.jpg"
    physical_path = os.path.join(POSTER_DIR, f"{imdb_id}.jpg")
    
    # 1. Physical SSD Check
    if os.path.exists(physical_path):
        return jsonify({"url": local_url})
        
    # 2. Cache Failure Check
    if poster_cache.get(imdb_id) == "NONE":
        return jsonify({"url": ""})
        
    try:
        q = urllib.parse.quote(title.lower().strip())
        first_char = q[0] if (q and q[0].isalnum()) else 'a'
        url = f"https://v3.sg.media-imdb.com/suggestion/x/{first_char}/{q}.json"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            for item in res_data.get("d", []):
                if "i" in item and "imageUrl" in item["i"]:
                    img_url = item["i"]["imageUrl"]
                    hd_url = img_url.split("._V1_")[0] + "._V1_.jpg" if "._V1_" in img_url else img_url
                    
                    img_req = urllib.request.Request(hd_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                        with open(physical_path, 'wb') as f:
                            f.write(img_resp.read())
                            
                    return jsonify({"url": local_url})
    except Exception as e:
        pass
        
    poster_cache[imdb_id] = "NONE" 
    save_json_cache(poster_cache, POSTER_CACHE_FILE)
    return jsonify({"url": ""})

@app.route("/api/financials", methods=["POST"])
def get_financials():
    imdb_id = (request.json or {}).get("id", "")
    if not imdb_id: return jsonify({"budget": None})
    
    global fin_cache
    if imdb_id in fin_cache:
        cached = fin_cache[imdb_id]
        if isinstance(cached.get("budget"), str): cached["budget"] = float(cached["budget"].replace('$','').replace(',','')) if cached["budget"] else None
        return jsonify({"budget": cached.get("budget")})
        
    # We stripped out Box Office to keep data completely accurate
    sparql_query = f"""
    SELECT ?budget WHERE {{
      ?movie wdt:P345 "{imdb_id}" .
      OPTIONAL {{ ?movie wdt:P2130 ?budget . }}
    }}
    """
    
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(sparql_query)
    headers = {'User-Agent': 'HT-Movies-Bot/1.0'}
    
    try:
        time.sleep(0.2)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            results = data.get("results", {}).get("bindings", [])
            
            b_val = None
            if results:
                movie_data = results[0]
                b_raw = movie_data.get("budget", {}).get("value")
                if b_raw: b_val = float(b_raw)
            
            res_obj = {"budget": b_val}
            fin_cache[imdb_id] = res_obj
            save_json_cache(fin_cache, FIN_CACHE_FILE)
            return jsonify(res_obj)
    except:
        return jsonify({"budget": None})

@app.route("/api/fields", methods=["GET"])
def get_fields():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(media)")
        cols = [c["name"] for c in cursor.fetchall()]
        
        cursor.execute("SELECT genres, vibe, cast_list FROM media")
        rows = cursor.fetchall()
        
        genres_set, exact_vibes, word_vibes, all_actors = set(), {}, {}, {}
        for r in rows:
            try:
                for g in json.loads(r["genres"]): genres_set.add(g)
            except: pass
            
            v_str = str(r["vibe"] or "").strip()
            if v_str and v_str.lower() not in ("none", "null", ""):
                unified_vibe = v_str.lower().capitalize()
                exact_vibes[unified_vibe] = exact_vibes.get(unified_vibe, 0) + 1
                words = [w.strip().lower() for w in re.split(r'[ ,]+', v_str) if w.strip()]
                for w in set(words): word_vibes[w] = word_vibes.get(w, 0) + 1
                
            try:
                raw_cast = json.loads(r["cast_list"] or "[]")
                clean_cast = list(dict.fromkeys(raw_cast))
                for c in clean_cast:
                    all_actors[c] = all_actors.get(c, 0) + 1
            except: pass
            
        conn.close()
        
        sorted_exact_vibes = [{"vibe": k, "count": v} for k, v in sorted(exact_vibes.items(), key=lambda x: x[1], reverse=True)]
        sorted_word_vibes = [{"vibe": k, "count": v} for k, v in sorted(word_vibes.items(), key=lambda x: x[1], reverse=True)]
        sorted_actors = [{"name": k, "count": v} for k, v in sorted(all_actors.items(), key=lambda x: x[1], reverse=True)]
        
        sys_fields = {"id", "type", "title", "year", "year_int", "runtime", "runtime_int", "rating", "votes", "genres", "cast_list", "vibe", "short_summary", "total_seasons", "total_episodes", "season_episodes"}
        booleans = [c for c in cols if c.startswith(("is_", "has_", "can_", "do_", "are_"))]
        percents = [c for c in cols if c.endswith("_percentage")]
        integers = [c for c in cols if c not in sys_fields and c not in booleans and c not in percents and not c.endswith("_summary")]
                
        return jsonify({
            "success": True, "booleans": sorted(booleans), "percentages": sorted(percents), 
            "integers": sorted(integers), "genres": sorted(list(genres_set)),
            "exact_vibes": sorted_exact_vibes, "word_vibes": sorted_word_vibes, "actors": sorted_actors
        })
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

def safe_float(val):
    try: return float(val) if val is not None and str(val).strip() != "" else None
    except: return None

def clean_html(text):
    if not text: return ""
    return re.sub(r'<[^>]+>', '', str(text))

@app.route("/api/search", methods=["POST"])
def search():
    try:
        data = request.json or {}
        where, params = [], []
        
        if data.get("type") and data.get("type") != "both":
            where.append("type = ?"); params.append(data["type"])
            
        for f in data.get("include_booleans", []): where.append(f"{f} = 1")
        for f in data.get("exclude_booleans", []): where.append(f"{f} = 0")
            
        for pct_k, pct_v in data.get("percentages", {}).items():
            mn, mx = safe_float(pct_v.get("min")), safe_float(pct_v.get("max"))
            if mn is not None and mn > 0: where.append(f"{pct_k} >= ?"); params.append(mn)
            if mx is not None and mx < 100: where.append(f"{pct_k} <= ?"); params.append(mx)
            
        for int_k, int_v in data.get("integers", {}).items():
            mn, mx = safe_float(int_v.get("min")), safe_float(int_v.get("max"))
            if mn is not None: where.append(f"{int_k} >= ?"); params.append(mn)
            if mx is not None: where.append(f"{int_k} <= ?"); params.append(mx)
            
        for field in ["rating", "votes", "year_int", "runtime_int", "total_seasons", "total_episodes"]:
            mn, mx = safe_float(data.get(f"{field}_min")), safe_float(data.get(f"{field}_max"))
            if mn is not None: where.append(f"{field} >= ?"); params.append(mn)
            if mx is not None: where.append(f"{field} <= ?"); params.append(mx)
            
        where_sql = " AND ".join(where) if where else "1=1"
        
        if data.get("search_query"):
            queries = data["search_query"].split("|")
            for q in queries:
                if not q: continue
                where_sql = f"({where_sql}) AND (title LIKE ? OR short_summary LIKE ? OR cast_list LIKE ?)"
                sq = f"%{q}%"
                params.extend([sq, sq, sq])
            
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM media WHERE {where_sql}", params)
        rows = cursor.fetchall()
        
        results = []
        req_inc_g, req_exc_g = set(data.get("include_genres", [])), set(data.get("exclude_genres", []))
        req_exact_v = set([v.lower() for v in data.get("exact_vibes", [])])
        req_word_v = set([v.lower() for v in data.get("word_vibes", [])])
        
        req_rej_only_g = set(data.get("reject_if_only_genres", []))
        req_rej_only_pairs = set(data.get("reject_if_only_genre_pairs", []))
        
        pref_cast = set(data.get("preferred_cast", []))
        banned_cast = set(data.get("banned_cast", []))
        actor_mode = data.get("actor_mode", "sort")
        c_min, c_max = safe_float(data.get("cast_size_min")), safe_float(data.get("cast_size_max"))
        
        eps_min = safe_float(data.get("eps_per_season_min"))
        eps_max = safe_float(data.get("eps_per_season_max"))
        
        b_min, b_max = safe_float(data.get("budget_min")), safe_float(data.get("budget_max"))
        
        global fin_cache
        fin_cache = load_json_cache(FIN_CACHE_FILE) 
        
        for row in rows:
            rec = dict(row)
            rec["short_summary"] = clean_html(rec.get("short_summary", ""))
            
            fin = fin_cache.get(rec["id"], {})
            b_val = fin.get("budget")
            if isinstance(b_val, str): b_val = float(b_val.replace('$','').replace(',','')) if b_val else None
            rec["budget"] = b_val
            
            if b_min is not None and (rec["budget"] is None or rec["budget"] < b_min): continue
            if b_max is not None and (rec["budget"] is None or rec["budget"] > b_max): continue
            
            try: rec["genres"] = json.loads(rec["genres"])
            except: rec["genres"] = []
            
            # The Advanced "Only this genre" rejection logic
            if req_rej_only_g and len(rec["genres"]) == 1:
                if rec["genres"][0] in req_rej_only_g:
                    continue
                    
            # The Advanced "Only these TWO genres" rejection logic
            if req_rej_only_pairs and len(rec["genres"]) == 2:
                sg = sorted(rec["genres"])
                pair_str = f"{sg[0]}|{sg[1]}"
                if pair_str in req_rej_only_pairs:
                    continue
            
            try: rec["season_episodes"] = json.loads(rec["season_episodes"])
            except: rec["season_episodes"] = {}
            try:
                raw_cast = json.loads(rec["cast_list"] or "[]")
                rec["cast_list"] = list(dict.fromkeys(raw_cast))
            except: rec["cast_list"] = []
                
            if eps_min is not None or eps_max is not None:
                if rec.get("type") != "show" or not rec.get("season_episodes"): continue
                valid_seasons = []
                for s, count in rec["season_episodes"].items():
                    if str(s).lower() in ("specials", "none", "null", ""): continue
                    valid_seasons.append(int(count))
                    
                allowed_violations = 1 if len(valid_seasons) > 1 else 0
                violations = 0
                for c in valid_seasons:
                    if eps_min is not None and c < eps_min: violations += 1
                    elif eps_max is not None and c > eps_max: violations += 1
                if violations > allowed_violations: continue
                
            g_set = set(rec["genres"])
            if req_exc_g and not req_exc_g.isdisjoint(g_set): continue
            if req_inc_g and not req_inc_g.issubset(g_set): continue
            
            v_str = str(rec.get("vibe", "") or "").lower().strip()
            if req_exact_v and v_str not in req_exact_v: continue
            if req_word_v:
                v_words = set([w.strip() for w in re.split(r'[ ,]+', v_str) if w.strip()])
                if not req_word_v.intersection(v_words): continue
            
            c_len = len(rec["cast_list"])
            if c_min is not None and c_len < c_min: continue
            if c_max is not None and c_len > c_max: continue
            if banned_cast and not banned_cast.isdisjoint(rec["cast_list"]): continue
            
            if pref_cast and actor_mode in ["any", "all"]:
                intersect = set(rec["cast_list"]).intersection(pref_cast)
                if actor_mode == "all" and len(intersect) != len(pref_cast): continue
                if actor_mode == "any" and len(intersect) == 0: continue
            
            rec["cast_score"] = len(set(rec["cast_list"]).intersection(pref_cast))
            results.append(rec)
            
        conn.close()
        
        filter_ids = data.get("filter_ids")
        if filter_ids is not None: results = [r for r in results if r["id"] in filter_ids]
            
        sort_by = data.get("sort_by", "rating")
        reverse_primary = (data.get("sort_order", "desc").lower() == "desc")
        
        def primary_sort_key(x):
            if sort_by == "preferred_cast": return x["cast_score"]
            val = x.get(sort_by)
            
            if val is None: return -999999999999 if reverse_primary else 999999999999
            try: return float(val)
            except: return 0
            
        results.sort(key=primary_sort_key, reverse=reverse_primary)
        if actor_mode == "sort" and pref_cast and sort_by != "preferred_cast":
            results.sort(key=lambda x: x["cast_score"], reverse=True)
            
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__": app.run(host="0.0.0.0", port=8000, debug=True)
