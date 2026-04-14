python3 manage.py runserver --settings=config.settings.local

python manage.py shell --settings=config.settings.local

python manage.py importarusuarios --settings=config.settings.local

docker compose -f local.yml exec django python manage.py shell

git stash -u
git pull --rebase
git stash pop
git add .
git rebase --continue
