# Board Game Geek / BoxThrone game locator

Provides an interface to allow searching for games in your Board Game Geek (BGG) collection and locating them on your BoxThrone.

It will sync with BGG, and is designed to be used with https://github.com/sillyfrog/BGGManagerLEDLocator to highlight your desired game.

*Note:* This update includes a breaking change to configuration for the LED strips. See below for the updated format.

# Setup

This has been designed to run in Docker, however it should be OK outside Docker, however it's untested. Containers that are required (to get the full system) are:

- PostgreSQL server
- MQTT/Mosquito server (if using RGB LEDs)
- Reverse proxy if running outside the local network (I use this https://github.com/sillyfrog/magicreverseproxy )

The "build-run-image.sh" shows an example of how to build and run the Docker image. Update the paths for your environment. The "/app/static/images/" and "/app/games/" volumes start empty, and are populated when run. This is a cache, but to prevent hammering BGG, please ensure this is not a persistent volume.

## Postgres

I'm using the Docker Hub Postgres image, and have a basic setup. See the docs at https://hub.docker.com/_/postgres/ for how to do this.

Once you have Postgres up and running, connect to the DB and run the SQL in `setup.sql`. This will create all of the required tables etc.

## MQTT

If you want the LED's up and running, the updates are sent via MQTT. I'm using the https://docs.docker.com/samples/library/eclipse-mosquitto/ image, running on the standard port.

## Configuration

There is a sample `config.json`, I would suggest starting with this for your environment. The options are as follows:

- _username_/_password_: This is your login to BGG to sync all of your games.
- _dburl_: The URL to connect to the Postgres server, update for what you have configured for your DB.
- _ledscommand_: this is the command to call when you want to highlight your game - currently all that's included is `homieleds`. The program will be called with each argument in the list, and to the end will be appended the `<col>,<led>` for each LED to highlight.
- _columns_: This outlines how each column of games is configure (for example, in your BoxThrone), a list of JSON objects. Each element has the follow attributes:
  - _id_: The numeric id of the column.
  - _name_: The name of the column you want to display in the web interface, I have just used the ID's, but it's designed to be flexible.
  - _sections_: This is each section in the column, a list of objects. For example, in the sample JSON the sections are a topper, then two full height BoxThrones. This is done in the order top to bottom. The attributes of each section are:
     - _name_: The name of the section, to display in the web interface.
     - _start_: The row that the sections starts at in the column, this is the count of holes in the BoxThrone (including the base). It's every potential location you could put a game.
     - _end_: The last row of the section.
     - _ledstrips_: Optional, an object whose key is the strip ID (pole), this is a string of the integer, and value is a list with 2 elements of _ledstart_ and _ledend_ that should be included - you can for example highlight the poles on either side of the game that's highlighted, so may include more than one strip.
          - _ledstart_: The count (from zero) of the LED's that are included in this section - the program will extrapolate which LED's to highlight.
          - _ledend_: The last count of the LED in this section. If the LED's are starting at the bottom, the _ledend_ should be greater than the _ledstart_.

## Synchronizing with BGG

Once everything is up and running, you should run the `updategames.py` script. This will synchronize with BGG, including filling the local cache, and downloading images etc. If running in docker, do the following:
- Connect to the running container: `docker run -it boardgamegeek bash`
- Then run the script: `/app/updategames.py`

You can also run this in the Web interface by connecting to the interface (on whatever port you have configured in the `docker run` command, in my example it's on `5001`), and click on `Force Sync`.

You can also setup a daily cron job on the _host_ (not in the container), to regularly sync with BGG - see the `update-boardgamegeek-stats.cron` file for what I have in my cron.daily.

## LED's 

To highlight the LED's, see the https://github.com/sillyfrog/BGGManagerLEDLocator project for details.
