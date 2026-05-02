FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PEXELS_API_KEY="9yRxTJWwJ8dHkdKvXCmBRXbargz6k4nC8BvlEyTphU5nbcL2cIBnKrUs"
ENV GENAI_API_KEY="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"
ENV GOOGLE_MAPS_KEY="AIzaSyBPGVK7Z-ulHftNhof8PYBowA5LK3oL87k"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]