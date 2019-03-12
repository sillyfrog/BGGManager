FROM python:3

RUN pip install --upgrade pip && \
    pip install flask postgres requests paho-mqtt

COPY * /app/
COPY static/ /app/static/
COPY templates/ /app/templates/

WORKDIR /app

ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
CMD ["flask", "run", "-h", "0.0.0.0", "-p", "80"]