#! /usr/bin/env bash
# This is used by the docker image. You can ignore this for regular use

# Let the DB start
sleep 10

# Create the DB, ignoring errors, such as if the database already exists
ultraqc initdb || true

# Run migrations
cd ultraqc
export FLASK_APP=wsgi.py
flask db upgrade
