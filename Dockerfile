FROM gcc:latest

# Install necessary tools
RUN apt-get update && apt-get install -y \
    time \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Set up a non-root user for security
RUN useradd -m -s /bin/bash cppuser
RUN chown -R cppuser:cppuser /workspace
USER cppuser

# Set default command
CMD ["/bin/bash"] 