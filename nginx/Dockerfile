# Builds Vue frontend and serves it via nginx alongside API proxy config
# Context must be the project root (docker-compose build context: .)

# Stage 1: build Vue app
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: nginx + static files + proxy config
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80 443
