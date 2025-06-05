FROM python:3.11-slim


# Установить netcat-openbsd
RUN apt-get update && apt-get install -y netcat-openbsd && apt-get clean

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download ru_core_news_sm
RUN python -m spacy download en_core_web_sm
COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

# Сделать entrypoint сценарий исполняемым
RUN chmod +x /app/entrypoint.sh

# Использовать entrypoint сценарий
ENTRYPOINT ["/app/entrypoint.sh"]