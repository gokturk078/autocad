FROM python:3.13-slim

WORKDIR /app

# System deps for ezdxf
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway provides PORT env var
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8765

EXPOSE 8765

CMD ["python", "main.py"]
