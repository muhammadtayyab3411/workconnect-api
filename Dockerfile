# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIPENV_VENV_IN_PROJECT=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --upgrade pip
RUN pip install pipenv

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Install Python dependencies
RUN pipenv install --system --deploy

# Copy project
COPY . .

# Create media directory
RUN mkdir -p media

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput --clear || true

# Expose port
EXPOSE 8001

# Run the application using daphne
CMD ["daphne", "-p", "8001", "-b", "0.0.0.0", "workconnect.asgi:application"] 