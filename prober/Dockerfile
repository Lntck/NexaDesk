# Runtime stage
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN addgroup --system --gid 1000 prober && \
    adduser --system --uid 1000 --ingroup prober prober

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R prober:prober /app

USER prober

EXPOSE 9102

CMD ["python", "-m", "prober.main"]
