from fastapi import FastAPI

from app.src.api.cv_generator.cv_generator.cv_generator import router as cv_generator_router

app = FastAPI()
app.include_router(cv_generator_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "cv-generator-be is running"}