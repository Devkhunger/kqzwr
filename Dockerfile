FROM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY data /app/data
COPY --from=frontend /src/frontend/dist /app/frontend/dist
ENV PORT=8000
EXPOSE 8000
CMD ["sh","-c","uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
