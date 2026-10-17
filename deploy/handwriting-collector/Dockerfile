FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/handwriting-collector-mobile/package.json frontend/handwriting-collector-mobile/package-lock.json ./
RUN npm ci

COPY frontend/handwriting-collector-mobile/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/handwriting-collector/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/handwriting-collector/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /app/dist/client/ /usr/share/nginx/html/

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1
