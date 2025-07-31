FROM nginx:latest

COPY ./nginx-web/ /usr/share/nginx/html/

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 9100

CMD ["nginx", "-g", "daemon off;"]