FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

ENV PYTHONUNBUFFERED=1
# ENV PLAYWRIGHT_BROWSERS_PATH=0
# ENV DATABASE_URL=postgresql://mark_exec_1_user:SyVLk46k6NOLNSLrLcY2UNZsGyjVsXMd@dpg-d59nd975r7bs739cg22g-a.oregon-postgres.render.com/mark_exec_1

ENV ALLOWED_HOSTS=lang-q.com,www.lang-q.com,arunet007.pythonanywhere.com,mark-exec-2.onrender.com,exec-mark-1.netlify.app,exec-mark-1.netlify.app/subscription,https://exec-mark-1.netlify.app,https://exec-mark-1.netlify.app/subscription,exec-mark-2.netlify.app,exec-mark-2.netlify.app/subscription,https://exec-mark-2.netlify.app,https://exec-mark-2.netlify.app/subscription,api.imagekit.io,ik.imagekit.io
ENV CORS_ALLOWED_ORIGINS=https://lang-q.com,https://www.lang-q.com,https://arunet007.pythonanywhere.com,https://www.arunet007.pythonanywhere.com,https://exec-mark-1.netlify.app,https://exec-mark-2.netlify.app,https://api.imagekit.io,https://ik.imagekit.io
ENV CORS_ALLOW_HEADERS=accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-csrftoken,x-requested-with,accountId
ENV CORS_ALLOW_METHODS=DELETE,GET,OPTIONS,PATCH,POST,PUT
ENV CSRF_TRUSTED_ORIGINS=https://lang-q.com,https://www.lang-q.com,https://arunet007.pythonanywhere.com,https://exec-mark-1.netlify.app,https://exec-mark-1.netlify.app/subscription,https://exec-mark-2.netlify.app,https://exec-mark-2.netlify.app/subscription,https://api.imagekit.io,https://ik.imagekit.io
ENV DATABASE_URL=postgresql://mark_exec_1_user:SyVLk46k6NOLNSLrLcY2UNZsGyjVsXMd@dpg-d59nd975r7bs739cg22g-a.oregon-postgres.render.com/mark_exec_1
ENV DEBUG=False
ENV DEFAULT_FROM_EMAIL=team@lang-q.com
ENV EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
ENV EMAIL_HOST=smtp.zoho.in
ENV EMAIL_HOST_PASSWORD=PHrT2NqBFwy1
ENV EMAIL_HOST_USER=team@lang-q.com
ENV EMAIL_PORT=587
ENV EMAIL_USE_TLS=True
ENV GEMINI_API_KEY=AIzaSyDBTuO-lck7FGoWurf9GK8AWIjXu3NsLvc
ENV PLAYWRIGHT_BROWSERS_PATH=0
ENV SECRET_KEY=django-insecure--rqp*!%oho!4yv^x_xkj%5u0ky+moq!_q(v7!pq
ENV SECURE_HSTS_INCLUDE_SUBDOMAINS=True
ENV SECURE_HSTS_PRELOAD=True
ENV SECURE_HSTS_SECONDS=31536000
ENV SECURE_SSL_REDIRECT=True

CMD gunicorn newsletter_project.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --timeout 180
