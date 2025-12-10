FROM ubuntu:22.04

ARG RUNNER_VERSION="2.321.0"
ARG TARGETPLATFORM

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    git \
    sudo \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

# Create runner user with docker group access
RUN useradd -m docker && \
    usermod -aG docker docker && \
    echo "docker ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /home/docker

# Download and extract runner
RUN ARCH=$(echo ${TARGETPLATFORM} | cut -d'/' -f2) && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "x86_64" ]; then ARCH="x64"; fi && \
    mkdir actions-runner && cd actions-runner && \
    curl -o actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz -L \
    https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz && \
    tar xzf ./actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz && \
    rm actions-runner-linux-${ARCH}-${RUNNER_VERSION}.tar.gz

# Install runner dependencies
RUN /home/docker/actions-runner/bin/installdependencies.sh

# Set ownership
RUN chown -R docker:docker /home/docker

COPY start.sh /start.sh
RUN chmod +x /start.sh

USER docker
ENTRYPOINT ["/start.sh"]
