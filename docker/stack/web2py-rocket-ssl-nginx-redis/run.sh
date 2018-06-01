docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-rocket-ssl --format="{{.ID}}"))
docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-nginx --format="{{.ID}}"))
docker rm $(docker stop $(docker ps -a -q --filter ancestor=web2py-redis --format="{{.ID}}"))

docker network rm web2py-net
#docker network create web2py-net
docker network create --subnet=172.25.0.0/16 web2py-net

docker build -t web2py-rocket-ssl -f web2py-rocket-ssl .
docker build -t web2py-nginx -f web2py-nginx .
docker build -t web2py-redis -f web2py-redis .

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

docker run -d --net web2py-net --name web2py-redis --ip 172.25.0.24 web2py-redis
# docker exec -it web2py-redis  bash

sleep 2
ping -c1 -n 172.25.0.24
docker run --net web2py-net busybox ping -c1 -n web2py-redis
echo "------------------------------------------------------------------"
curl -I 172.25.0.24

docker network ls
docker network inspect web2py-net
docker volume ls
docker volume inspect applications
docker ps -a
docker ps
