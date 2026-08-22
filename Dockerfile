FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads logs

EXPOSE 5000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]