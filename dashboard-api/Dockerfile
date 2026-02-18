FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir     fastapi==0.110.0     uvicorn[standard]==0.27.1     sqlalchemy==2.0.25     pymysql==1.1.0     cryptography==42.0.5     docker==7.1.0     pydantic==2.6.1

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
