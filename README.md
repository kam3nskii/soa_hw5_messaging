У меня в последний момент стал похо работать сам поиск ссылок, но с очередью сообщений всё в порядке. Я использовал rabbitmq.

Чтобы запустить всё достаточно сделать `docker-compose up --scale worker=2 rabbitmq web worker`

После чего можно будет посылать запросы через REST API. 

Пусть основной сервер запустился на `172.22.0.4:5000`

Для создания задачи нужно в отдельном окне прописать:
```
curl -X POST 172.22.0.4:5000/api/v1.0/wiki -d '{"url1": "https://en.wikipedia.org/wiki/2019_Hungarian_Grand_Prix", "url2": "https://en.wikipedia.org/wiki/Pole_position"}'

```

Так мы создадим запрос и получим его id, он поступит в очередь, затем попадёт к одному из воркеров, воркеры после обработки запроса сохранят результат в файл с именем как у id запроса

Запросом:
```
curl -X GET 172.22.0.4:5000/api/v1.0/wiki
```
Можно получить все id уже обработанных задач.

А так смотрим результат запроса c id 2:
```
curl -X GET 172.22.0.4:5000/api/v1.0/wiki/2
```


![](img/Screenshot%202022-04-10%20232141.png)

Ещё можно не собирать всё самому, а запуллить образы, достаточно заменить docker-compose.yml на такой:
```
version: "3"

services:
    rabbitmq:
        image: rabbitmq:3.9-management
        hostname: "rabbitmq"
        ports:
            - "15672:15672"
            - "5672:5672"
    web:
        image: kam3nskii/hw5_messaging_server
        volumes:
            - data-volume:/data
    worker:
        image: kam3nskii/hw5_messaging_worker
        volumes:
            - data-volume:/data

volumes:
    data-volume: 
```

Ссылки на докерхаб: [вот](https://hub.docker.com/r/kam3nskii/hw5_messaging_server) и [вот](https://hub.docker.com/r/kam3nskii/hw5_messaging_worker)