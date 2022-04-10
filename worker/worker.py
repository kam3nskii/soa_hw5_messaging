from pathlib import Path
import pika
import time
import requests
from bs4 import BeautifulSoup
from functools import partial
from multiprocessing import Pool

def GetLinksFromPage(pageUrl):
    response = requests.get(pageUrl)
    soup = BeautifulSoup(response.content, 'html.parser')
    tags = soup.find_all('a')

    links = set()

    for tag in tags:
        if tag.has_attr('href'):
            link = tag['href']

            if link.startswith('#'):
                continue
            if link.startswith('/wiki/File:'):
                continue
            if link.startswith('//'):
                link = 'https:' + link
            if link.startswith('/'):
                link = 'https://en.wikipedia.org' + link
            if not link.startswith('https://en.wikipedia.org'):
                continue
            if link.find('/w/index.php?') != -1:
                continue

            found = link.find('#')
            if found != -1:
                link = link[:found]

            links.add(link)

    return links


def ProcessNewUrl(path, visited):
    newLink = path[-1]
    if not newLink in visited:
        visited[newLink] = GetLinksFromPage(newLink)
    links = visited[newLink]
    return set(map(lambda x: (*path, x), links))

def FindUrl(startUrl, endUrl):
    visited = dict()
    queue = [[startUrl]]

    MaxDepth = 2
    for i in range(MaxDepth):
        with Pool(9) as p:
            queue = set().union(*p.map(partial(ProcessNewUrl, visited=visited), queue))
        for item in queue:
            if item[-1] == endUrl:
                return f"True\n{len(item)}\n{' -> '.join(item)}\n"

    return 'False\n'


def callback(ch, method, properties, body):
    str = body.decode()
    id, url1, url2, dir = str.split()
    print(f" [x] Received {url1} and {url2} with id {id}", flush = True)
    caption = FindUrl(url1, url2)
    # print(caption, flush = True)
    file = Path(f"{dir}/{id}.txt")
    file.write_text(caption)
    print(" [x] Done", flush = True)
    ch.basic_ack(delivery_tag = method.delivery_tag)

while True:
    try:
        # connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost')) # for local tests
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq')) # for docker compose
        channel = connection.channel()
        channel.queue_declare(queue='task_queue', durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='task_queue', on_message_callback=callback)
        print(' [*] Waiting for messages. To exit press CTRL+C', flush = True)
        channel.start_consuming()
    except Exception as e:
        print(f'Error: {e}', flush = True)
        time.sleep(1)
