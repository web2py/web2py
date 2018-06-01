docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-rocket-ssl --format="{{.ID}}"))
docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-nginx --format="{{.ID}}"))
docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-db --format="{{.ID}}"))
docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-adminer --format="{{.ID}}"))

docker network rm web2py-net
#docker network create web2py-net
docker network create --subnet=172.25.0.0/16 web2py-net

docker build -t web2py-rocket-ssl -f web2py-rocket-ssl .
docker build -t web2py-nginx -f web2py-nginx .
docker build -t web2py-db -f web2py-db .
docker build -t web2py-adminer -f web2py-adminer .

docker run -d --net web2py-net -v applications:/home/web2py/web2py/applications -p 443:443 --name web2py-rocket-ssl --ip 172.25.0.22 web2py-rocket-ssl
# docker exec -it web2py-rocket-ssl  bash

sleep 2
ping -c1 -n 172.25.0.22
docker run --net web2py-net busybox ping -c1 -n web2py-rocket-ssl
echo "------------------------------------------------------------------"
curl -I 172.25.0.22:443

docker run -d --net web2py-net --name web2py-nginx --ip 172.25.0.23 web2py-nginx
# docker exec -it web2py-nginx  bash

sleep 2
ping -c1 -n 172.25.0.23
docker run --net web2py-net busybox ping -c1 -n web2py-nginx
echo "------------------------------------------------------------------"
curl -I 172.25.0.23

docker run -d --net web2py-net --name web2py-db --ip 172.25.0.24 web2py-db
# docker exec -it web2py-db  bash

sleep 2
ping -c1 -n 172.25.0.24
docker run --net web2py-net busybox ping -c1 -n web2py-db
echo "------------------------------------------------------------------"
curl -I 172.25.0.24

docker run -d --net web2py-net -p 8080:8080 --name web2py-adminer --ip 172.25.0.25 web2py-adminer
# docker exec -it web2py-adminer  bash

sleep 2
ping -c1 -n 172.25.0.25
docker run --net web2py-net busybox ping -c1 -n web2py-adminer
echo "------------------------------------------------------------------"
curl -I 172.25.0.25

docker network ls
docker network inspect web2py-net
docker volume ls
docker volume inspect applications
docker ps -a
docker ps
