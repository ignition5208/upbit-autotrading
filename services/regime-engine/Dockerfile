FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir httpx==0.27.2
COPY main.py /app/main.py
CMD ["python","/app/main.py"]
