ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-flask py3-requests
COPY app.py /app.py
CMD ["python3", "/app.py"]
