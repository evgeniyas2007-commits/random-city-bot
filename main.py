import os
import random
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import edge_tts
import aiohttp
import aiofiles

app = FastAPI()

# Ключі (ваші)
PEXELS_API_KEY = "9yRxTJWwJ8dHkdKvXCmBRXbargz6k4nC8BvlEyTphU5nbcL2cIBnKrUs"

# Список міст
CITIES = ["Львів", "Одеса", "Київ", "Чернівці", "Ужгород", "Кам'янець-Подільський", "Харків", "Дніпро"]

class GenerateRequest(BaseModel):
    city: Optional[str] = None
    include_shorts: bool = True
    include_thumbnail: bool = True

async def text_to_audio(text: str, path: str):
    """Перетворює текст на аудіо через Edge-TTS"""
    communicate = edge_tts.Communicate(text, "uk-UA-PolinaNeural")
    await communicate.save(path)

async def search_video(keyword: str) -> Optional[str]:
    """Шукає відео на Pexels"""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "per_page": 1}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                data = await resp.json()
        if data.get("videos"):
            for video in data["videos"]:
                for file in video.get("video_files", []):
                    if file.get("quality") == "hd":
                        return file["link"]
        return None
    except:
        return None

def get_fallback_script(city: str) -> dict:
    """Простий сценарій без використання Gemini"""
    facts = {
        "Львів": ["Львівська кава", "Високий замок", "Оперний театр", "Підземелля", "Личаківське кладовище"],
        "Одеса": ["Потьомкінські сходи", "Дерибасівська", "Одеський дворик", "Катакомби", "Морський порт"],
        "Київ": ["Софійський собор", "Андріївський узвіз", "Золоті ворота", "Володимирська гірка", "Печерська лавра"],
    }
    city_facts = facts.get(city, ["цікава історія", "унікальна архітектура", "смачна кухня", "красиві парки", "дружні люди"])
    
    scenes = []
    scenes.append({"text": f"Привіт! Сьогодні поговоримо про місто {city}. Це неймовірне місце, яке варто побачити!", "keywords": f"{city} aerial view"})
    for i, fact in enumerate(city_facts[:4]):
        scenes.append({"text": f"Факт {i+1}: {fact}. Це дуже цікаво!", "keywords": f"{city} {fact}"})
    scenes.append({"text": f"Ось таке чудове місто {city}. Підписуйтесь на канал, щоб дізнатися більше!", "keywords": f"{city} travel"})
    
    return {
        "title": f"{city} — неймовірне місто | ТОП-5 фактів",
        "description": f"Відео про місто {city}. Дивіться та дізнавайтесь нове!",
        "tags": [city, "подорожі", "Україна", "факти"],
        "scenes": scenes
    }

@app.post("/generate")
async def generate(request: GenerateRequest):
    city = request.city if request.city else random.choice(CITIES)
    
    # Отримуємо сценарій
    script = get_fallback_script(city)
    scenes = script["scenes"]
    
    # Створюємо аудіо файли для кожної сцени
    audio_files = []
    for i, scene in enumerate(scenes):
        audio_path = f"audio_{i}.mp3"
        await text_to_audio(scene["text"], audio_path)
        audio_files.append(audio_path)
    
    # Повертаємо результат (без відео, тільки аудіо для тесту)
    return {
        "status": "completed",
        "city": city,
        "long_video": "audio_files_created",
        "shorts": [],
        "seo": {
            "title": script["title"],
            "description": script["description"],
            "tags": script["tags"]
        },
        "message": f"Створено {len(audio_files)} аудіофайлів для міста {city}. Наступний крок: додати відео."
    }

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Сервер працює!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
