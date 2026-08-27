FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn==0.32.0

COPY serving ./serving

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "serving.main:app", "--host", "0.0.0.0", "--port", "8000"]
