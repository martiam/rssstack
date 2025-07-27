FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy
WORKDIR /app
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    docker.io \
    git \
    ca-certificates \
    lsb-release \
    gnupg \
    unzip

# Add Docker's official GPG key:
RUN apt-get update
RUN apt-get install ca-certificates curl
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
RUN chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update
RUN apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install firefox
COPY fetch_cookie.py .
#ENTRYPOINT ["bash","-c","while true; do python fetch_cookie.py && sleep 86400; done"]
CMD ["python", "fetch_cookie.py"]
