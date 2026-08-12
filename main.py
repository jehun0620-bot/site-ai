from fastapi import FastAPI

app = FastAPI()

@app.get("/")

def root():
        return {
                "message": "SITE-AI 서버가 정상적으로 작동합니다."
        }