import os
import asyncio
import random
import json
import uuid
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import edge_tts
import requests
import aiofiles
import aiohttp
from moviepy.editor import *
import google.generativeai as genai

app = FastAPI()

# Ваші ключі (вже вбудовані)
PEXELS_API_KEY = "9yRxTJWwJ8dHkdKvXCmBRXbargz6k4nC8BvlEyTphU5nbcL2cIBnKrUs"
GENAI_API_KEY = "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"
genai.configure(api_key=GENAI_API_KEY)

CITIES = ["Львів", "Одеса", "Київ", "Чернівці", "Ужгород", "Кам'янець-Подільський"]

class GenerateRequest(BaseModel):
    city: Optional[str] = None
    include_shorts: bool = True
    include_thumbnail: bool = True

async def generate_script(city: str):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Напиши сценарій для 8-хвилинного YouTube відео про місто {city}.
    Формат JSON:
    {{
        "title": "клікбейтна назва",
        "description": "опис відео",
        "tags": ["тег1", "тег2"],
        "scenes": [
            {{"text": "текст сцени 1", "keywords": "{city} aerial view"}},
            {{"text": "текст сцени 2", "keywords": "{city} architecture"}}
        ]
    }}
    Мінімум 5 сцен. Тільки JSON без зайвого тексту."""
    
    response = model.generate_content(prompt)
    text = response.text
    start = text.find('{')
    end = text.rfind('}') + 1
    return json.loads(text[start:end])

async def text_to_audio(text: str, path: str):
    communicate = edge_tts.Communicate(text, "uk-UA-PolinaNeural")
    await communicate.save(path)

async def search_video(keyword: str) -> Optional[str]:
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keyword, "per_page": 3}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
    for video in data.get("videos", []):
        for file in video.get("video_files", []):
            if file.get("quality") == "hd":
                return file["link"]
    return None

async def create_long_video(city: str, script: dict) -> str:
    scenes = script["scenes"]
    clips = []
    
    for i, scene in enumerate(scenes):
        audio_path = f"audio_{i}.mp3"
        await text_to_audio(scene["text"], audio_path)
        
        video_url = await search_video(scene["keywords"])
        video_path = f"video_{i}.mp4"
        
        if video_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as resp:
                    data = await resp.read()
                    async with aiofiles.open(video_path, "wb") as f:
                        await f.write(data)
            clip = VideoFileClip(video_path)
        else:
            clip = ColorClip(size=(1920, 1080), color=(0, 0, 100), duration=5)
        
        audio_clip = AudioFileClip(audio_path)
        clip = clip.subclip(0, audio_clip.duration).set_audio(audio_clip)
        clips.append(clip)
    
    final = concatenate_videoclips(clips)
    output = f"{city}_final.mp4"
    final.write_videofile(output, fps=24, codec='libx264')
    
    # Очистка
    for i in range(len(scenes)):
        if os.path.exists(f"audio_{i}.mp3"): os.remove(f"audio_{i}.mp3")
        if os.path.exists(f"video_{i}.mp4"): os.remove(f"video_{i}.mp4")
    
    return output

@app.post("/generate")
async def generate(request: GenerateRequest):
    city = request.city if request.city else random.choice(CITIES)
    
    script = await generate_script(city)
    video_path = await create_long_video(city, script)
    
    return {
        "status": "completed",
        "city": city,
        "long_video": video_path,
        "shorts": [],
        "seo": {
            "title": script["title"],
            "description": script["description"],
            "tags": script.get("tags", [])
        }
    }

@app.get("/download/{filename}")
async def download(filename: str):
    return FileResponse(filename, media_type="video/mp4", filename=filename)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)