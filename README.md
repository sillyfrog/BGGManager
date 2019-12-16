# Board Game Geek / BoxThrone game locator

Provides an interface to allow searching for games in your Board Game Geek (BGG) collection and locating them on your BoxThrone.

It will sync with BGG, and is designed to be used with https://github.com/sillyfrog/BGGManagerLEDLocator to highlight your desired game.

*Note:* This update includes a breaking change to configuration for the LED strips. See below for the updated format.

# Setup

This has been designed to run in Docker, however it should be OK outside Docker, however it's untested. Containers that are required (to get the full system) are:

- PostgreSQL server
- MQTT/Mosquito server (if using RGB LEDs)
- Reverse proxy if running outside the local network (I use this https://github.com/sillyfrog/magicreverseproxy )

The "build-run-image.sh" shows an example of how to build and run the Docker image. Update the paths for your environment. The "/app/static/images/" and "/app/games/" volumes start empty, and are populated when run. This is a cache, but to prevent hammering BGG, please ensure this is on a persistent volume of some kind.

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
- _excludednames_ (optional): a list of names that will be excluded from the Player list when logging players. Useful to exclude names with typo's that may have made it into the DB.
- _prioritynames_ (optional): names to always be at the top of the Player list when logging plays, in the same order (other names are sorted alphabetically). Ideal for frequent players so you can tap without typing. We list everyone in our household in this list.
- _columns_: This outlines how each column of games is configure (for example, in your BoxThrone), a list of JSON objects. Each element has the follow attributes:
  - _id_: The numeric id of the column. Trailing characters (non-digits) maybe included that will be stripped to allow creating what would otherwise be duplicate keys.
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

# Barcode scanning

The latest release includes the (optional) ability to scan barcodes on the boxes to make putting games away much easier. If the `pillow` and `pyzbar` Python modules are installed, you will be able to take a photo of the barcode, and use this as part of the "Put Away" option. Initially you'll need to populate your database with all of your bar codes. On a specific game, right at the bottom there is an _Associate Barcode_ button, clicking on this will take you to the barcode scanning screen. After giving access to the camera on your device (phone or tablet recommended), you can select which camera to use (the rear is recommended, the image should not be mirrored), you can tap the image when you have the barcode lined up. The decoding is done using the [pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar) library, so it has the same limitations. Quality is better than size I have found (ie: sometimes it's better to have the image smaller to be sharper).     

Barcode and camera support requires the latest OS and Browser. I have tested with Firefox v66 and on iOS 12 with Safari (it does not work with iOS Firefox at the time of my testing). Additionally, in my reading, webcam access is only provided to HTTPS sites, so it needs to be running behind an HTTPS/SSL gateway (I use my [Magic Reverse Proxy](https://github.com/sillyfrog/magicreverseproxy)).

# Updating

The latest release requires some updates to the DB, and this data will need to be back filled. To do this, change to the updates directory `cd updates` and then run the `./v1-update.py` script.