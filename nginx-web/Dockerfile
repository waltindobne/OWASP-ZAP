# nginx-web/Dockerfile
FROM nginx:latest

# Remove a configuração padrão do Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia seu arquivo de configuração customizado para o local correto
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80