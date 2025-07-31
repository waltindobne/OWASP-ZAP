FROM nginx:latest

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 9100

CMD ["nginx", "-g", "daemon off;"]