FROM python:3.11
ENV LANG=C.UTF-8
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "-m", "matebot_telegram"]
