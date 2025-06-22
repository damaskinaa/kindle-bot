# Use an official, lightweight Python version as a base
FROM python:3.11-slim

# Set an environment variable to ensure Poetry works correctly inside Docker
ENV POETRY_VIRTUALENVS_CREATE=false

# Set the working directory inside the container
WORKDIR /app

# Copy your dependency configuration files
COPY pyproject.toml poetry.lock* ./

# Install poetry and then use it to install your project's dependencies
RUN pip install poetry && poetry install --no-dev --no-interaction --no-ansi

# Copy the rest of your bot's code (main.py) into the container
COPY . .

# Set the command to run your bot when the container starts
CMD ["python", "main.py"]
