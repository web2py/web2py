# Start Service
	systemctl start docker

# Docker
	cd /Docker/Fedora/web2py-tornado
	docker build -t username/fedora-web2py-tornado .
	docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name fedora-web2py-tornado username/fedora-web2py-tornado
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/Fedora/web2py-tornado
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/Fedora/web2py-tornado
	docker login -u username
	docker build -t username/fedora-web2py-tornado .
	docker push username/fedora-web2py-tornado

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t username/fedora-web2py-tornado .
docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name fedora-web2py-tornado username/fedora-web2py-tornado

docker-compose up -d
docker-compose ps
