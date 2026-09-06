import os, csv, io, uuid
from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai.types import GenerateContentConfig
from google.cloud import firestore

app = Flask(__name__)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")

ai = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client()

RULES = []

def load_rules():
    global RULES
    path = os.path.join(os.path.dirname(__file__), "..", "data", "historical_rules.csv")
    try:
        with open(path, newline="", encoding="utf-8") as f:
            RULES = list(csv.DictReader(f))
    except FileNotFoundError:
        RULES = []

load_rules()

def review_code(code, language):
    rules = "\n".join(
        f"- {r['type']}: {r['description']}" for r in RULES
    )
    prompt = f"""You are a senior multi-language code reviewer.
Review this {language} code.

Historical rules to use as grounding:
{rules}

Return ONLY a standardized report with:
1. Overall Summary
2. Quality Rating: X/10
3. Bugs
4. Security Issues
5. Performance & Optimization
6. Architecture & Best Practices
7. Historical Rules Applied
8. Actionable Fixes
9. Improved Code (only if useful)

Use severity LOW, MEDIUM, HIGH, CRITICAL.
Do not invent that historical rules were applied if they are irrelevant.

CODE:
```{language}
{code}
```"""
    response = ai.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=GenerateContentConfig(temperature=0.1, max_output_tokens=5000)
    )
    return response.text

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/health")
def health():
    return jsonify(status="healthy", service="24/7 Intelligent Code Reviewer")

@app.route("/review", methods=["POST"])
def review():
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    language = str(data.get("language", "python")).lower().strip()
    user_id = str(data.get("user_id", "demo-user")).strip()

    if not code:
        return jsonify(success=False, error="Code is required"), 400
    if len(code) > 50000:
        return jsonify(success=False, error="Maximum 50,000 characters"), 400

    review_id = str(uuid.uuid4())
    try:
        result = review_code(code, language)
        db.collection("users").document(user_id).collection("reviews").document(review_id).set({
            "review_id": review_id,
            "language": language,
            "code_length": len(code),
            "review": result,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return jsonify(success=True, review_id=review_id, review=result)
    except Exception as e:
        print(e)
        return jsonify(success=False, error="Review failed"), 500

@app.route("/history/<user_id>")
def history(user_id):
    docs = db.collection("users").document(user_id).collection("reviews").order_by(
        "created_at", direction=firestore.Query.DESCENDING
    ).limit(20).stream()
    return jsonify(success=True, reviews=[d.to_dict() for d in docs])

HTML = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>24/7 Intelligent Code Reviewer</title>
<style>
body{font-family:Arial;margin:0;background:#f3f4f6;color:#111827}header{background:#111827;color:white;padding:28px;text-align:center}
main{max-width:1000px;margin:auto;padding:20px}.card{background:white;padding:22px;margin:18px 0;border-radius:12px;box-shadow:0 3px 12px #ddd}
select,input,textarea,button{width:100%;padding:12px;margin:7px 0;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}
textarea{height:320px;font-family:monospace}button{background:#2563eb;color:white;border:0;font-weight:bold;cursor:pointer}.result{white-space:pre-wrap;background:#111827;color:white;padding:18px;border-radius:8px;min-height:180px}
</style></head><body><header><h1>🤖 24/7 Intelligent Code Reviewer</h1><p>Multi-language reviews • Quality rating • Historical learning</p></header>
<main><div class="card"><label>User ID</label><input id="user" value="demo-user">
<label>Language</label><select id="lang"><option>python</option><option>javascript</option><option>java</option><option>c</option><option>cpp</option><option>go</option></select>
<label>Source Code</label><textarea id="code" placeholder="Paste code here..."></textarea><button onclick="review()">🔍 Review Code</button></div>
<div class="card"><h2>AI Review</h2><div id="result" class="result">Your review appears here.</div></div>
<div class="card"><h2>History</h2><button onclick="history()">Load Review History</button><div id="history"></div></div></main>
<script>
async function review(){let r=document.getElementById("result");r.textContent="Analyzing...";
try{let x=await fetch("/review",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_id:user.value,language:lang.value,code:code.value})});let d=await x.json();r.textContent=d.success?d.review:"Error: "+d.error}catch(e){r.textContent=e.message}}
async function history(){let x=await fetch("/history/"+encodeURIComponent(user.value));let d=await x.json();document.getElementById("history").innerHTML=d.reviews.map(r=>"<p><b>"+r.language+"</b> — "+r.review_id+"</p>").join("")||"No reviews yet."}
</script></body></html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
