# keepalive.py
import os, threading, subprocess
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/healthz")
def health():
    return "ok"

def run_bot():
    print("🔧 Spawning bot.py …")
    # show bot stdout/stderr in Render logs:
    subprocess.Popen(["python", "bot.py"])

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
