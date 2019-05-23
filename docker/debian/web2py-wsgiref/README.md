# Start Service
	systemctl start docker

# Docker
	cd /Docker/Debian/web2py-wsgiref
	docker build -t your_username/debian-web2py-wsgiref .
	docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name debian-web2py-wsgiref your_username/debian-web2py-wsgiref
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/Debian/web2py-wsgiref
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/Debian/web2py-wsgiref
	docker login -u your_username
	docker build -t your_username/debian-web2py-wsgiref .
	docker push your_username/debian-web2py-wsgiref

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t your_username/debian-web2py-wsgiref .
docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name debian-web2py-wsgiref your_username/debian-web2py-wsgiref

docker-compose up -d
docker-compose ps
