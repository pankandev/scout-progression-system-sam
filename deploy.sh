sam deploy --no-confirm-changeset
cd ./web/dist/scout-personal-progression-webapp/
aws s3 cp ./* s3://pps-webpage.com --acl public-read
