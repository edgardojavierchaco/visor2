echo 'corriendo collectstatic...'
python3 manage.py collectstatic --no-input --settings=config.settings.production

python3 manage.py migrate --settings=config.settings.production

gunicorn --env DJANGO_SETTINGS_MODULE=config.settings.production config.wsgi:application --bind 0.0.0.0:5000

########################
docker ps

docker exec -it NOMBRE_DEL_CONTENEDOR bash

docker compose exec web bash

docker inspect NOMBRE_DEL_CONTENEDOR | grep -A 5 '"Mounts"'


#######################
docker volume ls

docker volume inspect NOMBRE_DEL_VOLUMEN

docker exec -it NOMBRE_DEL_CONTENEDOR bash


cd /app/data
ls -lah


docker compose exec NOMBRE_DEL_SERVICIO bash


######################################
imagenes huérfanas
docker image prune -a

docker rmi $(docker images -f "dangling=true" -q)

docker compose -f production.yml up --build


##########################
pwd

sudo find / -type d -name "productionfiles"

sudo chown -R usuario:grupo /ruta/a/productionfiles
sudo chmod -R 775 /ruta/a/productionfiles

cp -r ./productionfiles ./productionfiles_backup


#######################################
reentrenar modelo de Machine Learning

docker exec visor_local_django python manage.py reentrenar_modelo
docker exec visor_production_django python manage.py reentrenar_modelo

