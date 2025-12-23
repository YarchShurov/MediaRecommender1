from fastapi import FastAPI
import uvicorn

app = FastAPI(title="MediaRecommender Test")

@app.get("/")
def read_root():
    return {"message": "Server is working!", "status": "OK"}

@app.get("/test")
def test_endpoint():
    return {"test": "This is a test endpoint"}

if __name__ == "__main__":
    print("Starting test server...")
    print("Open in browser: http://localhost:8001")
    print("API docs: http://localhost:8001/docs")
    # В конце файла измените:
    uvicorn.run(app, host="127.0.0.1", port=8001)  # Используем порт 8001