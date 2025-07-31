FROM nginx:latest

RUN rm /etc/nginx/conf.d/default.conf

COPY ../index.html /usr/share/nginx/html/index.html
COPY ../dashboard.html /usr/share/nginx/html/dashboard.html

EXPOSE 9100

CMD ["nginx", "-g", "daemon off;"]