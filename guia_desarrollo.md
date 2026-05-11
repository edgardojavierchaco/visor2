python3 manage.py runserver --settings=config.settings.local

python manage.py shell --settings=config.settings.local

python manage.py importarusuarios --settings=config.settings.local

docker compose -f local.yml exec django python manage.py shell

git stash -u
git pull --rebase
git stash pop
git add .
git rebase --continue


python manage.py makemigrations --settings=config.settings.local
python manage.py migrate --settings=config.settings.local


sudo docker compose -f local.yml down -v --remove-orphans
sudo docker compose -f local.yml build --no-cache
sudo docker compose -f local.yml up