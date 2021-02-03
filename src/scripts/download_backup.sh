heroku pg:backups:capture
heroku pg:backups:download
now=`date +"%Y-%m-%d-%H-%M"`
mv latest.dump backups/$now.dump