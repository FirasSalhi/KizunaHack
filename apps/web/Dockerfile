FROM node:22-alpine AS base

WORKDIR /app

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY packages/contracts/package.json ./packages/contracts/

RUN pnpm install --frozen-lockfile

COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
# Post-Harvest section: app/embed/post-harvest serves this page from the repo
COPY research/post-harvest-model/dashboard/farmer_dashboard.html ./research/post-harvest-model/dashboard/

WORKDIR /app/apps/web
RUN pnpm build

EXPOSE 3000

ENV PORT=3000
ENV NODE_ENV=production

CMD ["pnpm", "start"]
