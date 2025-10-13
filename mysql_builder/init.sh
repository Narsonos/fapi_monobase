#!/bin/bash
# /mysql_builder_final/init.sh
set -e

/usr/local/bin/docker-entrypoint.sh mysqld --default-authentication-plugin=caching_sha2_password &

echo "Waiting for MySQL to become ready..."
until mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; do
  sleep 1
done


echo "MySQL is ready. Creating user and database...${MYSQL_ROOT_PASSWORD}"
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`; CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}'; GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';"
echo "MySQL is ready! Shutting down..."

mysqladmin -u root -p"${MYSQL_ROOT_PASSWORD}" shutdown
