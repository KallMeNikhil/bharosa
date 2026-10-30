# The web console, run as a Vite dev server.
#
# This is a development image on purpose. The console exists to exercise the
# API by hand, so hot reload and readable stack traces are worth more here than
# a minified bundle behind a static server.

FROM node:20-alpine

WORKDIR /app

# Dependencies install from the lockfile alone, so editing a component does not
# reinstall the tree.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Compose keeps node_modules in a named volume, which outlives image rebuilds,
# so a dependency added to package.json would otherwise never reach it. Syncing
# against the mounted lockfile on start is a no-op when nothing has changed.
#
# --host binds beyond the container's loopback, without which the published
# port accepts a connection and then answers nothing.
CMD ["sh", "-c", "npm install --no-audit --no-fund && exec npm run dev -- --host 0.0.0.0"]
