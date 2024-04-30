.PHONY: all install kill

all: kill
	json-server --watch ./data/data.json --host 0.0.0.0 --port 5001 &
	python -m uvicorn fastapi-server.app.app:app --host 0.0.0.0 --port 3000 --reload &
	cd node-js && npm start &

install:
	npm install -g json-server

kill:
	-@kill -9 $(shell lsof -ti:3000)
	-@kill -9 $(shell lsof -ti:5001)
	-@kill -9 $(shell lsof -ti:8000)

