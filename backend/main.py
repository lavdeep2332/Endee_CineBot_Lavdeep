import os
import json
import requests
import traceback
import re
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
from groq import Groq

# --- CONFIGURATION ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENDEE_BASE = "http://localhost:8080/api/v1"
INDEX_NAME = "movies" 
GROQ_API_KEY = "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"
STORAGE_FILE = "movies_db.json"

print("Loading AI Models...")
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"❌ CRITICAL ERROR LOADING MODELS: {e}")

# --- HELPER: CLEAN JSON ---
def clean_and_parse_json(content):
    """Strips markdown to prevent JSON crashes."""
    try:
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```", "", content)
        return json.loads(content.strip())
    except Exception as e:
        print(f"JSON Parse Error on content: {content}")
        raise e

# --- STORAGE MANAGER ---
def load_text_db():
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def save_text_db(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_movie_to_system(movie_id, text):
    print(f"   💾 Adding: {movie_id}...")
    vector = embedding_model.encode(text).tolist()
    insert_url = f"{ENDEE_BASE}/index/{INDEX_NAME}/vector/insert"
    try:
        payload = [{
            "id": movie_id, 
            "vector": vector, 
            "metadata": {"description": "Metadata stored in JSON sidecar"} 
        }]
        requests.post(insert_url, json=payload)
    except Exception as e:
        print(f"      ⚠️ Endee Insert Error: {e}")

    db = load_text_db()
    db[movie_id] = text
    save_text_db(db)

# --- CORE FUNCTIONS (VECTOR DB ONLY) ---
def get_vector(text):
    return embedding_model.encode(text).tolist()

def search_endee(query):
    print(f"🔎 Searching Index '{INDEX_NAME}' for: {query}")
    vector = get_vector(query)
    try:
        search_url = f"{ENDEE_BASE}/index/{INDEX_NAME}/search"
        payload = {"vector": vector, "k": 3}
        
        response = requests.post(search_url, json=payload)
        
        # FIX: Parse properly and preserve order!
        import re
        raw_text = response.text
        
        # 1. Find all matches (which are in order of relevance)
        all_matches = re.findall(r'(mov_[a-zA-Z0-9]+)', raw_text)
        
        # 2. Remove duplicates while keeping order (The "Ordered Set" trick)
        found_ids = []
        seen = set()
        for mid in all_matches:
            if mid not in seen:
                found_ids.append(mid)
                seen.add(mid)
                
        print(f"   Found IDs (Ranked): {found_ids}")

        db = load_text_db()
        results = []
        for mid in found_ids:
            if mid in db:
                results.append(db[mid])
            else:
                print(f"      ⚠️ ID {mid} found in Endee but missing from JSON.")
                
        return results

    except Exception as e:
        print(f"⚠️ Search Error: {e}")
        return []

# --- AGENT ENDPOINT ---
class UserRequest(BaseModel):
    message: str

@app.post("/agent")
async def agent_endpoint(request: UserRequest):
    try:
        user_message = request.message
        
        # --- STRICT ROUTER LOGIC ---
        # This prompt ensures we align with the RAG objective.
        router_prompt = """
        You are a Router. Output JSON only.
        
        Decide which tool to use:
        - "RAG": Use this for specific questions about characters, plot details, or facts within a movie (e.g., "Who cooks?", "What happens at the end?").
        - "RECOMMEND": Use this for general requests asking for movie suggestions (e.g., "Give me a scary movie").
        - "SEARCH": Use this when the user searches for a title directly OR provides simple keywords (e.g., "Inception", "rat", "dreams", "sinking ship").
        - "NONE": Use this ONLY if the input is random gibberish (e.g., "asdfjkl") or completely unrelated to movies/entertainment.
        
        Output format: {"tool": "TOOL_NAME", "query": "search query"}
        """
        
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": router_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile", 
            response_format={"type": "json_object"}
        )
        
        decision = clean_and_parse_json(completion.choices[0].message.content)
        tool = decision.get("tool")
        query = decision.get("query")
        print(f"🤖 Tool: {tool} | Query: {query}")

        # Handle Unknown Queries politely
        if tool == "NONE":
            return {
                "response": "I'm sorry, I couldn't find any information on that.",
                "tool_used": "NONE"
            }

        # 2. Vector DB Search (Always used for RAG/Recommend)
        results = search_endee(query)

        if not results:
             final_response = "I searched the database but found nothing matching that."
        else:
            context = "\n".join([f"- {r}" for r in results])
            
            if tool == "RAG":
                # Strict RAG: Use context to answer
                rag_reply = client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Context: {context}\nQuestion: {user_message}\nAnswer:"}],
                    model="llama-3.3-70b-versatile"
                )
                final_response = rag_reply.choices[0].message.content
            else:
                # Recommendation/Search: Just list findings
                final_response = f"Found these movies:\n\n{context}"

        return {"response": final_response, "tool_used": tool}

    except Exception as e:
        traceback.print_exc() 
        return {"response": f"Server Error: {str(e)}", "tool_used": "ERROR"}

@app.on_event("startup")
async def startup():
    print("🚀 Server Starting...")
    initial_movies = [
        {"id": "mov_1", "text": "Inception: A thief enters dreams to steal secrets."},
        {"id": "mov_2", "text": "The Matrix: A hacker discovers reality is a simulation."},
        {"id": "mov_3", "text": "Interstellar: Explorers travel through wormholes."},
        {"id": "mov_4", "text": "Ratatouille: A rat who can cook in Paris."},
        {"id": "mov_5", "text": "Titanic: A romance disaster film about a sinking ship."} 
    ]
    for m in initial_movies:
        add_movie_to_system(m["id"], m["text"])
    print("✅ Startup Complete!")