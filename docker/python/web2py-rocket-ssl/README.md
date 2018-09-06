# Start Service
	systemctl start docker

# Docker
	cd /Docker/App/web2py-rocket-ssl
	docker build -t your_username/app-web2py-rocket-ssl .
	docker run -d -v applications:/web2py/applications -p 443:443 --name app-web2py-rocket-ssl your_username/app-web2py-rocket-ssl
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/App/web2py-rocket-ssl
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/App/web2py-rocket-ssl
	docker login -u your_username
	docker build -t your_username/app-web2py-rocket-ssl .
	docker push your_username/app-web2py-rocket-ssl

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t your_username/app-web2py-rocket-ssl .
docker run -d -v applications:/web2py/applications -p 443:443 --name app-web2py-rocket-ssl your_username/app-web2py-rocket-ssl

docker-compose up -d
docker-compose ps
