FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY app ./app
COPY tsconfig.json next-env.d.ts ./
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
