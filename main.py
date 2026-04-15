from fastapi import FastAPI
import models
from database import engine

# create the tables in the database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lean Auth API")

@app.get("/")
def read_root():
    return {"status": "Auth API is running"}  