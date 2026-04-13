FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN find connectors -name requirements.txt -exec pip install --no-cache-dir -r {} \;

ENTRYPOINT ["pytest"]
