from fastapi import FastAPI

app = FastAPI(title="Lean Auth API")

@app.get("/")
def read_root():
    return {"status": "Auth API is running"}