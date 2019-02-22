cd /var/share/boardgamegeek
docker build . -t boardgamegeek
docker kill boardgamegeek
docker rm boardgamegeek
docker run -d \
    -v /var/share/store/boardgamegeek/images/:/app/static/images/ \
    -v /var/share/store/boardgamegeek/games/:/app/games/ \
    -v /var/share/store/boardgamegeek/config.json:/app/config.json \
    -v /etc/localtime:/etc/localtime:ro \
    -p 5001:80 \
    --name boardgamegeek boardgamegeek