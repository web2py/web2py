# Start Service
	systemctl start docker

# Docker
	cd /Docker/Centos/web2py-gunicorn
	docker build -t username/centos-web2py-gunicorn .
	docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name centos-web2py-gunicorn username/centos-web2py-gunicorn
	docker ps 
	docker volume ls
	docker volume inspect applications

# Docker Compose
	pip install docker-compose
	cd /Docker/Centos/web2py-gunicorn
	docker-compose up -d
	docker-compose ps
	docker volume ls
	docker volume inspect root_applications

# Docker Cloud
	cd /Docker/Centos/web2py-gunicorn
	docker login -u username
	docker build -t username/centos-web2py-gunicorn .
	docker push username/centos-web2py-gunicorn

# Shell (Copy the content of the file into this scaffolding shell and replace the variable text $ with \$ )
cat << EOF > docker-compose.yml

EOF
cat docker-compose.yml

cat << EOF > Dockerfile

EOF
cat Dockerfile

docker build -t username/centos-web2py-gunicorn .
docker run -d -v applications:/home/web2py/web2py/applications -p 8000:8000 --name centos-web2py-gunicorn username/centos-web2py-gunicorn

docker-compose up -d
docker-compose ps
