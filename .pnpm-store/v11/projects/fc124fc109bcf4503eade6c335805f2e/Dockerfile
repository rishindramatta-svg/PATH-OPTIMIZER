FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
