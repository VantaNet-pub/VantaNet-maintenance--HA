ARG BUILD_FROM
FROM ${BUILD_FROM}
ENV TZ=Europe/Berlin
RUN apk add --no-cache python3 py3-flask py3-requests py3-reportlab py3-websocket-client tzdata
WORKDIR /app
COPY app.py maintenance_v130.py reports.py pdf_reports.py licensing.py berlin_time.py /app/
COPY assets /app/assets
CMD ["/command/with-contenv", "python3", "/app/app.py"]
