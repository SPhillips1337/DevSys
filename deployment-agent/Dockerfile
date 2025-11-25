FROM python:3.11-slim
WORKDIR /app

# Install ssh client and rsync for remote-ssh runner
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client rsync && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py ./
CMD ["python", "worker.py"]
