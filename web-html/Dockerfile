FROM nginx:latest

COPY index.html /usr/share/nginx/html/index.html
COPY dashboard.html /usr/share/nginx/html/dashboard.html

COPY reports/ /usr/share/nginx/html/reports/

EXPOSE 9100

CMD ["nginx", "-g", "daemon off;"]