# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install MariaDB Connector/C
RUN apt-get update && \
    apt-get install -y libmariadb-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy the Python script and requirements file into the container
COPY BiggerChatBot.py .
COPY requirements.txt .
COPY config.yml .
COPY FilesForDocker/ ./FilesForDocker/
#COPY config.toml /root/.streamlit/config.toml

# Install the necessary Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run streamlit when the container launches
CMD ["streamlit", "run", "BiggerChatBot.py"]
