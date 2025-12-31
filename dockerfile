FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/New_York

# Update package lists and install tzdata
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=0
ENV DATABASE_URL=postgresql://mark_exec_1_user:SyVLk46k6NOLNSLrLcY2UNZsGyjVsXMd@dpg-d59nd975r7bs739cg22g-a.oregon-postgres.render.com/mark_exec_1

RUN python manage.py collectstatic --noinput || true

# For Debian/Ubuntu-based images
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# For Alpine-based images
RUN apk add --no-cache tzdata


# CMD ["gunicorn", "newsletter_project.wsgi:application", "--bind", "0.0.0.0:10000", "--workers", "2", "--timeout", "180"]

CMD gunicorn newsletter_project.wsgi:application --bind 0.0.0.0:10000 --workers 2 --timeout 180
