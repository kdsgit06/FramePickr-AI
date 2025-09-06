# backend/Dockerfile
FROM python:3.11-slim

# install system deps (added libgl1)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# somewhere after WORKDIR /app
COPY backend/model /app/model


# copy requirements first for better cache (relative to backend/ build context)
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# copy app code from the backend/ directory (context)
COPY . /app

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
