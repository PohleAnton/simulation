FROM python:3.10-slim


WORKDIR /usr/src/app


RUN apt-get update && \
    apt-get install -y libmariadb-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY BiggerChatBot.py .
COPY requirements.txt .
COPY config.yml .
COPY FilesForDocker/ ./FilesForDocker/
#COPY config.toml /root/.streamlit/config.toml


RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8501


CMD ["streamlit", "run", "BiggerChatBot.py"]
