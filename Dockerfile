FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt --no-cache-dir
RUN playwright install

COPY . /app

EXPOSE 7860

CMD ["python", "-u", "app.py"]