
from fastapi import FastAPI
from app.connectors.postgres import harvest_postgres

app = FastAPI(title="Connector API")

@app.post("/run/postgres")
def run_postgres():
    return harvest_postgres()
