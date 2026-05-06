#!/usr/bin/env python3
import sqlite3, json, os, re
from flask import Flask, request, jsonify, make_response, send_from_directory

app = Flask(__name__, static_folder='website', static_url_path='')
USER_DATA_FILE = "website_local_storage.json"

def get_db():
    conn = sqlite3.connect("movies.db")
    conn.row_factory = sqlite3.Row
    return conn

def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {"profiles": {"Default": {"rejected": [], "hidden": [], "watch_later": {}, "preferred_cast": [], "banned_cast": [], "colors": {}, "section_order": {}, "filters": {}}}, "current_profile": "Default"}
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {"profiles": {"Default": {"rejected": [], "hidden": [], "watch_later": {}, "preferred_cast": [], "banned_cast": [], "filters": {}}}, "current_profile": "Default"}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

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
            
        # Core standard constraints
        for field in ["rating", "year_int", "runtime_int", "total_seasons", "total_episodes"]:
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
        
        pref_cast = set(data.get("preferred_cast", []))
        banned_cast = set(data.get("banned_cast", []))
        actor_mode = data.get("actor_mode", "sort")
        c_min, c_max = safe_float(data.get("cast_size_min")), safe_float(data.get("cast_size_max"))
        
        eps_min = safe_float(data.get("eps_per_season_min"))
        eps_max = safe_float(data.get("eps_per_season_max"))
        
        for row in rows:
            rec = dict(row)
            rec["short_summary"] = clean_html(rec.get("short_summary", ""))
            
            try: rec["genres"] = json.loads(rec["genres"])
            except: rec["genres"] = []
            try: rec["season_episodes"] = json.loads(rec["season_episodes"])
            except: rec["season_episodes"] = {}
            try:
                raw_cast = json.loads(rec["cast_list"] or "[]")
                rec["cast_list"] = list(dict.fromkeys(raw_cast))
            except: rec["cast_list"] = []
                
            # Grace Season Logic
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
            if val is None: return -999999 if reverse_primary else 999999
            try: return float(val)
            except: return 0
            
        results.sort(key=primary_sort_key, reverse=reverse_primary)
        if actor_mode == "sort" and pref_cast and sort_by != "preferred_cast":
            results.sort(key=lambda x: x["cast_score"], reverse=True)
            
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__": app.run(host="0.0.0.0", port=8000, debug=True)
