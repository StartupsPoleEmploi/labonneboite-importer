documentation:
	pip3 install mkdocs mkdocs-material
	python3 -m mkdocs serve --dev-addr '127.0.0.1:9999'

develop: 
	docker-compose -f docker-compose.dev.yml down \
	&& docker-compose -f docker-compose.dev.yml up --build

test:
	docker volume create --name=testResults
	docker-compose -f docker-compose.testing.yml up --build --abort-on-container-exit
	docker run --rm -v testResults:/testResults -v $$(pwd):/backup busybox tar -zcvf /backup/testResults.tar.gz /testResults
