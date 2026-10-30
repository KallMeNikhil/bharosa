FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["sh", "-c", "npm install --no-audit --no-fund && exec npm run dev -- --host 0.0.0.0"]
