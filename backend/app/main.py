from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Sprint Works AI esta rodando"}
