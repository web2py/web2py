# Start Service
	systemctl start docker

# Docker
	cd /Docker/App/web2py-twisted
	docker build -t your_username/app-web2py-twisted .
	docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name app-web2py-twisted your_username/app-web2py-twisted
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/App/web2py-twisted
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/App/web2py-twisted
	docker login -u your_username
	docker build -t your_username/app-web2py-twisted .
	docker push your_username/app-web2py-twisted

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t your_username/app-web2py-twisted .
docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name app-web2py-twisted your_username/app-web2py-twisted

docker-compose up -d
docker-compose ps
