python3 manage.py runserver --settings=config.settings.local

python manage.py shell --settings=config.settings.local

python manage.py check --settings=config.settings.local

python manage.py importarusuarios --settings=config.settings.local

docker compose -f local.yml exec django python manage.py shell

git stash -u
git pull --rebase
git stash pop
git add .
git rebase --continue

python manage.py collectstatic --noinput 

python manage.py makemigrations --settings=config.settings.local
python manage.py migrate --settings=config.settings.local 


sudo docker compose -f local.yml down -v --remove-orphans
sudo docker compose -f local.yml build --no-cache
sudo docker compose -f local.yml up

REFRESH MATERIALIZED VIEW CONCURRENTLY
    bnh.mv_total_cargos_ra_2026;

REFRESH MATERIALIZED VIEW CONCURRENTLY
    bnh.mv_total_horas_ra_2026;


bnhpersonas:inicio


python -m dotenv -f .env.local run -- \
python manage.py refrescar_asistencia \
    --anio 2026 \
    --mes 10 \
    --settings=config.settings.local


python manage.py configurar_mantenimiento_asistencia --hora 05:30 --hora-semanal 06:30
python manage.py estado_mantenimiento_asistencia