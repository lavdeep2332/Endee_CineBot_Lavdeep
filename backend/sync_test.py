import json
import requests
import os
from sentence_transformers import SentenceTransformer

# CONFIG
ENDEE_URL = "http://localhost:8080/api/v1/index/movies/search"
JSON_FILE = "movies_db.json"
MODEL_NAME = 'all-MiniLM-L6-v2'

def verify_system():
    print("🕵️‍♂️ Starting Data Integrity Check (Binary Safe)...")
    
    # 1. Load Data
    if not os.path.exists(JSON_FILE):
        print("❌ JSON Database file missing!")
        return
    
    with open(JSON_FILE, "r") as f:
        db = json.load(f)
    
    print(f"📚 Loaded {len(db)} movies from JSON.")
    print("🧠 Loading AI Model...")
    model = SentenceTransformer(MODEL_NAME)

    errors = 0
    
    # 2. Test Every Movie
    for movie_id, description in db.items():
        print(f"\n   Testing ID: {movie_id}...")
        
        # Vectorize
        vector = model.encode(description).tolist()
        
        # Search Endee
        try:
            # We ask for the top 1 result
            resp = requests.post(ENDEE_URL, json={"vector": vector, "k": 1})
            
            if resp.status_code != 200:
                print(f"      ❌ API Error: {resp.status_code}")
                errors += 1
                continue
            
            # THE FIX: Check Raw Bytes (.content) instead of String (.text)
            # We encode the ID (e.g., 'mov_1') into bytes (b'mov_1') to match the binary response
            movie_id_bytes = movie_id.encode('utf-8')
            
            if movie_id_bytes in resp.content:
                print(f"      ✅ Sync OK (Found {movie_id})")
            else:
                # If simple byte search fails, let's look closer
                print(f"      ⚠️ SYNC FAIL! Endee returned results but {movie_id} was missing.")
                print(f"      Response size: {len(resp.content)} bytes")
                errors += 1
                
        except Exception as e:
            print(f"      ❌ Connection Error: {e}")
            errors += 1

    print("\n" + "="*30)
    if errors == 0:
        print("🎉 INTEGRITY CHECK PASSED: System is 100% Synced.")
    else:
        print(f"🚫 INTEGRITY CHECK FAILED: Found {errors} errors.")
    print("="*30)

if __name__ == "__main__":
    verify_system()