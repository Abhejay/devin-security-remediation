FROM python:3.12-slim

WORKDIR /app

COPY pipeline.py .

CMD ["python", "pipeline.py"]
