# Start Service
	systemctl start docker

# Docker
	cd /Docker/Alpine/web2py-rocket
	docker build -t username/alpine-web2py-rocket .
	docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name alpine-web2py-rocket username/alpine-web2py-rocket
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/Alpine/web2py-rocket
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/Alpine/web2py-rocket
	docker login -u username
	docker build -t username/alpine-web2py-rocket .
	docker push username/alpine-web2py-rocket

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t username/alpine-web2py-rocket .
docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name alpine-web2py-rocket username/

docker-compose up -d
docker-compose ps
