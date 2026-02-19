# MariaDB healthcheck (fixed)

v1.8-0001 고정:

test ["CMD","mariadb-admin","ping","-h","127.0.0.1","-uroot","-p${MYSQL_ROOT_PASSWORD}"]
interval 5s
timeout 3s
retries 30
