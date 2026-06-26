# Step 1: Build static assets
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source and build
COPY . ./
RUN npm run build

# Step 2: Serve using Nginx
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy default nginx configuration if customization is needed, otherwise default is fine
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
