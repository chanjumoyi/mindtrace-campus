FROM node:22-alpine
WORKDIR /app
COPY package.json server.js crisisScanner.js sanitizeInput.js ./
USER node
EXPOSE 8090
CMD ["node", "server.js"]
