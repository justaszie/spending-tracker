# frontend-v2/Dockerfile
FROM node:22-alpine AS frontend

WORKDIR /usr/src/app

# Install deps (cached as long as package.json doesn't change)
COPY package.json package-lock.json* pnpm-lock.yaml* bun.lockb* ./
RUN npm install

# Copy source
COPY . .

EXPOSE 5173

# Vite dev server, accessible from host
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]