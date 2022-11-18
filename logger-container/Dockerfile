FROM python:3

COPY app /app

WORKDIR /app

RUN mkdir -p /var/lib/registry/ && \
    pip3 install -U -r requirements.txt

EXPOSE 8000

CMD ["python3", "app.py", "8000"]
