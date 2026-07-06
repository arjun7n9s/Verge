FROM node:20-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/console/package.json apps/console/
COPY packages/schema/js/package.json packages/schema/js/
RUN pnpm install --frozen-lockfile

COPY apps/console apps/console
COPY packages/schema/js packages/schema/js

ARG VITE_KEYCLOAK_URL=
ARG VITE_KEYCLOAK_REALM=verge
ARG VITE_KEYCLOAK_CLIENT_ID=verge-console
ENV VITE_KEYCLOAK_URL=$VITE_KEYCLOAK_URL \
    VITE_KEYCLOAK_REALM=$VITE_KEYCLOAK_REALM \
    VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID

RUN pnpm --filter @verge/console build

FROM nginx:alpine
COPY --from=build /app/apps/console/dist /usr/share/nginx/html
COPY apps/console/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
