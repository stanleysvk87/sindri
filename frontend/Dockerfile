FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

# nginx:1.27-alpine ships wget (busybox) already -- no extra package needed.
# 127.0.0.1, not localhost: nginx.conf only has "listen 80" (IPv4), but the
# container's /etc/hosts resolves localhost to ::1 first -- busybox wget
# doesn't fall back to the next address like a real client would, so it
# reports the healthcheck as failing even though nginx is up and fine.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1
