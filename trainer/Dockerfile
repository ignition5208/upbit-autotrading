FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/pyproject.toml
RUN pip install -U pip && pip install -e .

COPY trainer /app/trainer

CMD ["python", "-m", "trainer.main"]
