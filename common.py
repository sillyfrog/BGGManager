import pathlib
import postgres
import os
import psycopg2
import datetime
import requests
import json

DIR_BASE = pathlib.Path(
    os.environ.get("BASEDIR", pathlib.Path(__file__).resolve().parent)
)
CONFIG = json.load(open(DIR_BASE / "config.json"))

BGG_URL = "https://www.boardgamegeek.com/xmlapi/collection/{}".format(
    CONFIG["username"]
)
PLAYS_URL = "https://www.boardgamegeek.com/xmlapi2/plays"

DB_RETRIES = CONFIG.get("db_retries", 3)


IMAGES_PATH = DIR_BASE / "static" / "images"
THUMBS_PATH = IMAGES_PATH / "thumbs"
IMAGES_URL = "/static/images/{}.jpg"
THUMBS_URL = "/static/images/thumbs/{}.jpg"

MINI_THUMB_SIZE = 60
SPRITE_WIDTH = 10
SPRITE_SPACING = 5
SPRITE_SCALE = 2  # For Retina displays, set to 1 for normal displays

DATA_PATH = DIR_BASE / "allgames.xml"
GAMES_CACHE_PATH = DIR_BASE / "games"

_dbconnection = None
_dbdirectconnection = None

# Make sure the directories exist at startup, so do not run in a main function
THUMBS_PATH.mkdir(parents=True, exist_ok=True)


def spritecoord(imgid, scale=True):
    y = imgid // SPRITE_WIDTH
    x = imgid % SPRITE_WIDTH
    x = (MINI_THUMB_SIZE + SPRITE_SPACING) * x + SPRITE_SPACING
    y = (MINI_THUMB_SIZE + SPRITE_SPACING) * y + SPRITE_SPACING
    if scale:
        x = x * SPRITE_SCALE
        y = y * SPRITE_SCALE
    return x, y


class PostgresRetry(postgres.Postgres):
    def doretries(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if self.ignoreerror:
                print("Ignoring error! {!r} ({})".format(e, e))
            else:
                print("Got error, exiting! {!r} ({})".format(e, e))
                import traceback

                traceback.print_exc()
                os._exit(1)

    def run(self, *args, **kwargs):
        return self.doretries(super().run, *args, **kwargs)

    def one(self, *args, **kwargs):
        return self.doretries(super().one, *args, **kwargs)

    def all(self, *args, **kwargs):
        return self.doretries(super().all, *args, **kwargs)


def dbconn(ignoreerror=False):
    global _dbconnection, _dbdirectconnection
    if ignoreerror:
        if not _dbdirectconnection:
            _dbdirectconnection = PostgresRetry(CONFIG["dburl"])
            _dbdirectconnection.ignoreerror = True
        return _dbdirectconnection
    else:
        if not _dbconnection:
            _dbconnection = PostgresRetry(CONFIG["dburl"])
            _dbconnection.ignoreerror = False
        return _dbconnection


STATUS = {"own": "Own", "preordered": "Pre-Ordered", "wishlist": "Wish List"}
KEYS_TXT = {
    "id": "DB ID",
    "bggid": "BGG ID",
    "name": "Name",
    "description": "Description",
    "status": "Status",
    "rating": "BGG Rating",
    "complexity": "Complexity",
    "playingtime": "Playing Time",
    "minplayers": "Min Players",
    "maxplayers": "Max Players",
    "yearpublished": "Year Published",
    "minage": "Min Recommended Age",
    "expansionbggid": "Expansion BGG ID",
    "col": "Column",
    "row": "Row",
    "mechanics": "Game Mechanics",
    "categories": "Game Categories",
    "expansionname": "Expansion Name",
    "lastplay": "Last Play",
    "groupid": "Group ID",
    "groupname": "Group Name",
    "rowcol": "Location",
}


def formatgamevals(game):
    game["statustxt"] = STATUS.get(game["status"], game["status"])
    game["ratingtxt"] = "{0:.1f}".format(game["rating"])
    game["complexitytxt"] = "{0:.1f}".format(game["complexity"])
    game["playingtimetxt"] = "{} mins".format(game["playingtime"])
    if game["lastplay"]:
        game["lastplaytxt"] = isodate(game["lastplay"])
    else:
        game["lastplaytxt"] = "None recorded"
    game["imageurl"] = IMAGES_URL.format(game["bggid"])
    game["thumburl"] = THUMBS_URL.format(game["bggid"])
    if "mechanics" in game:
        game["mechanicstxt"] = ", ".join(game["mechanics"])
        game["categoriestxt"] = ", ".join(game["categories"])
    game["description"] = game["description"].replace("&#10;", "<br />")
    game["rowtxt"] = str(game["row"])
    column = getcolumnbyid(game["col"])
    if column is not None:
        game["coltxt"] = column["name"]
        game["rowcoltxt"] = "{},{}".format(game["coltxt"], game["rowtxt"])
    else:
        game["coltxt"] = "none"
        game["rowcoltxt"] = "none"
    while game["description"].endswith("<br />"):
        game["description"] = game["description"][:-6]
    if game["imgid"]:
        x, y = spritecoord(game["imgid"], False)
        game["spritex"] = x
        game["spritey"] = y
    # if "&" in game["description"]:
    #    print("Found &:", game)
    return game


def formatgamekey(key):
    if key.endswith("txt"):
        key = key[:-3]
    return KEYS_TXT[key]


def querygames(
    bggid=None,
    id=None,
    asdict=True,
    formatvals=True,
    includeexpansions=False,
    extendedlocation=False,
):
    if bggid is not None:
        where = "WHERE g.bggid=%s"
        args = [bggid]
    elif id is not None:
        where = "WHERE g.id=%s"
        args = [id]
    else:
        where = ""
        args = []
    if asdict:
        back_as = dict
    else:
        back_as = None
    games = dbconn().all(
        """
        SELECT g.*, i.*, groups.name AS groupname,
            ARRAY(SELECT text FROM mechanics, gamemechanic 
                WHERE gamemechanic.gameid = g.id AND 
                    gamemechanic.bggmechanicid = mechanics.bggmechanicid
                ORDER BY text
            ) AS mechanics, 
            ARRAY(SELECT text FROM categories, gamecategory 
                WHERE gamecategory.gameid = g.id AND 
                    gamecategory.bggcategoryid = categories.bggcategoryid
                ORDER BY text
            ) AS categories,
            e.name AS expansionname,
            (SELECT MAX(date) FROM plays WHERE g.bggid = plays.gamebggid) AS lastplay,
            ARRAY(SELECT barcode FROM barcodes WHERE barcodes.bggid = g.bggid) as barcodes
            FROM games g 
                LEFT OUTER JOIN games e ON g.expansionbggid = e.bggid 
                LEFT OUTER JOIN gamesinfo i ON g.id = i.gamesid
                LEFT OUTER JOIN groups ON i.groupid = groups.id
            """
        + where,
        args,
        back_as=back_as,
    )
    if includeexpansions:
        for game in games:
            expansions = dbconn().all(
                """SELECT id, bggid, name
                FROM games
                WHERE expansionbggid = %s
                ORDER BY name;""",
                [game["bggid"]],
                back_as=dict,
            )
            game["expansions"] = expansions
    if formatvals:
        games = [formatgamevals(game) for game in games]
    if extendedlocation:
        for game in games:
            locationinfo(game)

    if bggid is not None or id is not None:
        return games[0]
    else:
        return games


def getcolumnbyid(colid):
    if colid is None:
        return None
    for col in CONFIG["columns"]:
        if col["id"] == colid:
            return col
    return None


def locationinfo(game):
    """Updates the passed game INPLACE with location information"""
    game["distancetxt"] = ""
    if game["col"] and game["row"]:
        filledrows = dbconn().all(
            """
            SELECT DISTINCT row
            FROM gamesinfo
            WHERE col = %s
            ORDER BY row
            """,
            [game["col"]],
        )
        # Figure out the section in the column
        column = getcolumnbyid(game["col"])

        msg = "Column {}, ".format(column["name"])
        # Find section in the column
        for section in column["sections"]:
            if game["row"] >= section["start"] and game["row"] <= section["end"]:
                break
        game["sectionconfig"] = section
        # Get the filled section rows
        sectionrows = []
        rowstaken = game["row"]
        for row in filledrows:
            if row >= section["start"] and row <= section["end"]:
                sectionrows.append(row)
            if row < game["row"]:
                spacing = game["row"] - row
                if spacing < rowstaken:
                    rowstaken = spacing
        game["rowstaken"] = rowstaken
        # Now count other games above and below this game in the sect
        beforecount = sectionrows.index(game["row"])
        if beforecount == 0:
            game["topofsection"] = True
        aftercount = len(sectionrows) - beforecount - 1
        if aftercount == 0:
            game["bottomofsection"] = True
        if beforecount < aftercount:
            distance = beforecount
            txt = "top"
        else:
            distance = aftercount
            txt = "bottom"
        if distance == 0:
            msg += "at {}".format(txt)
        else:
            distance += 1
            msg += "{}{} from {}".format(distance, thnumber(distance), txt)
        if len(column["sections"]) > 1:
            msg += " of {} section".format(section["name"])
        game["distancetxt"] = msg


def thnumber(num):
    lastdigit = int(str(num)[-1])
    if num > 10:
        secondlastdigit = int(str(num)[-2])
    else:
        secondlastdigit = 0
    if secondlastdigit != 1:
        if lastdigit == 1:
            return "st"
        elif lastdigit == 2:
            return "nd"
        elif lastdigit == 3:
            return "rd"
    return "th"


def getstate(key, default=None):
    res = dbconn().all("SELECT value FROM state WHERE item = %s;", [key])
    if len(res) == 1:
        return res[0]
    else:
        return default


def setstate(key, value):
    dbconn().run(
        """
        INSERT INTO state (item, value)
        VALUES (%s, %s)
        ON CONFLICT ON CONSTRAINT state_item_key
        DO UPDATE SET value=%s;
        """,
        [key, value, value],
    )


def updateinfo(bggid=None, gameid=None, col=None, row=None, groupid=None):
    if not gameid:
        gameid = dbconn().one("SELECT id FROM games WHERE bggid = %s;", [bggid])
    # Ensure we have a record to update
    dbconn().run(
        "INSERT INTO gamesinfo (gamesid) VALUES (%s) ON CONFLICT DO NOTHING;", [gameid]
    )
    sets = []
    args = []
    for data in ["col", "row", "groupid"]:
        val = eval(data)
        if val is not None:
            sets.append("{} = %s".format(data))
            args.append(val)
    if not sets:
        # Nothing to update
        return
    args.append(gameid)
    dbconn().run(
        "UPDATE gamesinfo SET {} WHERE gamesid = %s".format(", ".join(sets)), args
    )

    if bggid:
        # Propogate this info to the expansions
        expansions = dbconn().all(
            "SELECT id, name, groupid FROM games LEFT OUTER JOIN gamesinfo ON games.id = gamesinfo.gamesid WHERE expansionbggid = %s"
            % (bggid)
        )
        for expansion in expansions:
            if expansion.groupid is None:
                print("To propogate to:", expansion.id, expansion.name)
                updateinfo(gameid=expansion.id, groupid=groupid)


EXCLUDE_NAMES = CONFIG.get("excludednames", []) + [""]
PRIORITY_NAMES = CONFIG.get("prioritynames", [])


def getplayernames():
    """Returns a list of all player names.

    This list is cleaned up slightly.
    """
    names = dbconn().all(
        """
        SELECT DISTINCT name FROM players ORDER BY name;
        """
    )
    names = set(names)
    names = names - set(EXCLUDE_NAMES)
    names = names - set(PRIORITY_NAMES)
    names = list(names)
    names.sort()
    firstnames = PRIORITY_NAMES
    names = firstnames + names
    return names


ALL = 1
TO_UPLOAD = 2
UPLOADED = 3


def getplays(bgggameid=None, status=ALL):
    where = []
    args = []
    if status == TO_UPLOAD:
        where.append("plays.bggid IS NULL")
    elif status == UPLOADED:
        where.append("plays.bggid IS NOT NULL")

    if bgggameid is not None:
        where.append("plays.gamebggid = %s")
        args.append(bgggameid)
    res = dbconn().all(
        """
        SELECT plays.id AS playid, plays.bggid AS bggplayid, gamebggid, date, comments, name, color, score, new, win
            FROM plays LEFT OUTER JOIN players ON 
                (plays.id = players.playsid)
            WHERE {}
            ORDER BY date DESC, plays.id DESC, score DESC""".format(
            " AND ".join(where)
        ),
        args,
    )
    ret = []
    currentplayid = None
    for rec in res:
        if rec.playid != currentplayid:
            if rec.date:
                date = rec.date.date().isoformat()
            else:
                rec.date = None
            play = {
                "playid": rec.playid,
                "gamebggid": rec.gamebggid,
                "bggplayid": rec.bggplayid,
                "date": date,
                "comments": rec.comments,
                "players": [],
            }
            ret.append(play)
            currentplayid = rec.playid
        if rec.name:
            play["players"].append(
                {
                    "name": rec.name,
                    "color": rec.color,
                    "score": rec.score,
                    "new": rec.new,
                    "win": rec.win,
                }
            )
    return ret


def recordplay(playdata):
    """Records a given play to the DB

    If bggid is not supplied, it's assumed it needs to be uploaded to get
    an ID.
    """
    # Create a raw connecttion to ensure we get the correct row insert counts etc.
    conn = psycopg2.connect(CONFIG["dburl"])
    cur = conn.cursor()
    if "bggid" in playdata:
        statement = """INSERT INTO plays (bggid, date, gamebggid, comments)
        VALUES (%(bggid)s, %(date)s, %(gamebggid)s, %(comments)s)
        ON CONFLICT DO NOTHING;
        """
    else:
        statement = """INSERT INTO plays (date, gamebggid, comments)
        VALUES (%(date)s, %(gamebggid)s, %(comments)s)
        """
    cur.execute(statement, playdata)
    if cur.rowcount == 0:
        # Nothing was inserted, so this play must already be recorded, return
        return
    cur.execute("SELECT LASTVAL();")
    playsid = cur.fetchone()[0]
    for player in playdata["players"]:
        player.update(playdata)
        player["playsid"] = playsid
        cur.execute(
            """INSERT INTO players (playsid, name, color, score, new, win)
            VALUES (%(playsid)s, %(name)s, %(color)s, %(score)s, %(new)s, %(win)s)
            ON CONFLICT DO NOTHING;
            """,
            player,
        )
    conn.commit()


def isodate(date):
    if type(date) == str:
        return date
    return date.date().isoformat()


def postplay(playdata):
    date = datetime.datetime.now().isoformat()[:14] + "00:00.000Z"
    postdata = {
        "quantity": 1,
        "date": date,
        "twitter": False,
        "objecttype": "thing",
        "length": 0,
        "ajax": 1,
        "action": "save",
    }
    postdata["objectid"] = str(playdata.get("gamebggid"))
    postdata["comments"] = playdata.get("comments")
    postdata["playdate"] = isodate(playdata.get("date"))

    postdata["players"] = []

    for player in playdata["players"]:
        playerrec = {
            "name": player.get("name"),
            "color": player.get("color"),
            "score": str(player.get("score")),
            "repeat": True,
            "selected": False,
            "userid": 0,
            "username": "",
        }
        if player.get("win"):
            playerrec["win"] = True
        if player.get("new"):
            playerrec["new"] = True
        postdata["players"].append(playerrec)

    # Now get a session cookie, and post the data
    s = requests.Session()
    r = s.post(
        "https://boardgamegeek.com/login",
        {"username": CONFIG["username"], "password": CONFIG["password"]},
    )
    if r.status_code != 200:
        raise Exception("Error logging in ({}): {}".format(r.status_code, r.text))
    r = s.post("https://boardgamegeek.com/geekplay.php", json=postdata)
    if r.status_code != 200:
        raise Exception("Error posting data ({}): {}".format(r.status_code, r.text))
    return int(r.json()["playid"])


def getgroups():
    return dbconn().all("SELECT id, name FROM groups ORDER BY name;", back_as=dict)


def updategroups(groups):
    for group in groups:
        if group["id"] == "new":
            if group["name"]:
                dbconn().run("INSERT INTO groups (name) VALUES (%s);", [group["name"]])
        else:
            group["id"] = int(group["id"])
            dbconn().run("UPDATE groups SET name = %(name)s WHERE id = %(id)s;", group)


if __name__ == "__main__":
    data = """{"gamebggid":3990,"date":"2019-01-18","comments":"A comment via common post again!","players":[{"name":"Smurf","color":"Blue","score":234,"win":true,"new":false},{"name":"Hermione","color":"","score":null,"win":false,"new":false}]}"""
    data = json.loads(data)
    # print(getplays(status=TO_UPLOAD))
    # recordplay(data)
    # print("play id:", postplay(data))
    print(querygames(3990))

# {
#    "date": "2019-01-18",
#    "comments": "omment",
#    "players": [
#        {"name": "Smurf", "color": "Blue", "score": 123, "win": true, "new": false},
#        {"name": "Hermione", "color": "", "score": null, "win": false, "new": false},
#    ],
# }

