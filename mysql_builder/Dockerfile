# /mysql_builder_final/Dockerfile

# Используем официальный образ как основу
FROM mysql:8.0

ARG MYSQL_ROOT_PASSWORD_ARG
ARG MYSQL_USER_ARG
ARG MYSQL_PASSWORD_ARG
ARG MYSQL_DATABASE_ARG

ENV MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD_ARG
ENV MYSQL_USER=$MYSQL_USER_ARG
ENV MYSQL_PASSWORD=$MYSQL_PASSWORD_ARG
ENV MYSQL_DATABASE=$MYSQL_DATABASE_ARG


# Копируем и запускаем наш упрощённый скрипт
COPY init.sh /init.sh
RUN chmod +x /init.sh
RUN /init.sh