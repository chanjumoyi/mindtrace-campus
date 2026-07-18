FROM python:3.11-slim
WORKDIR /app
COPY scripts/extract_handwriting_features.py /app/scripts/extract_handwriting_features.py
COPY local/ai-lab/handwriting/service /app/local/ai-lab/handwriting/service
EXPOSE 8091
CMD ["python", "local/ai-lab/handwriting/service/server.py", "--host", "0.0.0.0", "--port", "8091"]
