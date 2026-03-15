from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
print("/health ->", client.get("/health").json())
print("/models/status ->", client.get("/models/status").json())
