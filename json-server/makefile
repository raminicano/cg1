.PHONY: all install kill

all:
	json-server --watch ./data.json --host 0.0.0.0 --port 5000 &

install:
	npm install -g json-server

kill:
	kill -9 $(shell pgrep -f "json-server --watch ./data.json")

