# DEADMAN API SERVER - Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for caching
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Create build directory for serving dashboard
RUN mkdir -p build

EXPOSE 8080

CMD ["npm", "start"]
