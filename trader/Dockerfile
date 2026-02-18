FROM python:3.11-slim
WORKDIR /app

# runtime deps
RUN pip install --no-cache-dir sqlalchemy pymysql requests

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["python","-u","trader.py"]
