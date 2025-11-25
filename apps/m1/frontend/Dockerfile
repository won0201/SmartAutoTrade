FROM node:18

WORKDIR /app

# 패키지 파일만 먼저 복사
COPY package.json package-lock.json ./

# npm 버그 방지를 위해 lockfile과 캐시 먼저 정리
RUN rm -rf node_modules package-lock.json && npm install

# 나머지 소스 복사
COPY . .

EXPOSE 7001

CMD ["npm", "run", "dev", "--", "--host"]

