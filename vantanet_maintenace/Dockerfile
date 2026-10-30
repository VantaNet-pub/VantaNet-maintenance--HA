ARG BUILD_FROM
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-flask py3-requests py3-reportlab py3-websocket-client tzdata
WORKDIR /app
COPY app.py maintenance_v130.py reports.py pdf_reports.py /app/
COPY assets /app/assets
CMD ["python3", "/app/app.py"]
