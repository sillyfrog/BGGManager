#!/usr/bin/env python3

import xml.etree.ElementTree
import requests
import pathlib
import time
import sys
import datetime

from common import (
    dbconn,
    IMAGES_PATH,
    THUMBS_PATH,
    BGG_URL,
    DATA_PATH,
    GAMES_CACHE_PATH,
)
import common

logfh = None


def getallwithid(items):
    ret = []
    for item in items:
        this = {"id": int(item.attrib.get("id")), "text": item.attrib.get("value")}
        ret.append(this)
    return ret


XML_TEXT_ELEMENTS = ["description", "image", "thumbnail"]

XML_INT_ELEMENTS = [
    "playingtime",
    "minplayers",
    "maxplayers",
    "yearpublished",
    "minage",
]


def extractgamedata(fh, gameinfo):
    tree = xml.etree.ElementTree.parse(fh)
    root = tree.getroot()
    ret = []
    for game in root:
        if game.tag != "item":
            continue
        data = {
            "name": gameinfo["name"],
            "bggid": int(game.attrib["id"]),
            "status": gameinfo["status"],
            "lastmodified": gameinfo["lastmodified"],
            "complexity": float(game.find(".//ratings/averageweight").attrib["value"]),
        }
        rating = game.find(".//ratings/average")
        if rating is None:
            log("**** No rating *** {}".format(data))
        else:
            data["rating"] = float(rating.attrib["value"])
        for elem in XML_TEXT_ELEMENTS:
            data[elem] = game.find(".//{}".format(elem)).text
        for elem in XML_INT_ELEMENTS:
            data[elem] = int(game.find(".//{}".format(elem)).attrib["value"])

        data["mechanics"] = getallwithid(
            game.findall('.//link[@type="boardgamemechanic"]')
        )
        data["categories"] = getallwithid(
            game.findall('.//link[@type="boardgamecategory"]')
        )
        expansions = game.findall('.//link[@type="boardgameexpansion"]')
        for expansion in expansions:
            if expansion.attrib.get("inbound") == "true":
                data["expansion"] = {
                    "id": int(expansion.attrib.get("id")),
                    "text": expansion.attrib.get("value"),
                }
                break
        ret.append(data)
        # Download the images
        download(data["image"], IMAGES_PATH / "{}.jpg".format(data["bggid"]))
        download(data["thumbnail"], THUMBS_PATH / "{}.jpg".format(data["bggid"]))
    return ret


def download(url, path):
    if path.is_file():
        if path.stat().st_size > 10:
            return
    log("Downloading: {}".format(url))
    r = requests.get(url)
    fh = path.open("wb")
    fh.write(r.content)
    fh.close


def getwithretry(url, params=None):
    for i in range(60):
        r = requests.get(url, params)
        if r.status_code == 200:
            return r.text
        log("Got back status {}, waiting...".format(r.status_code))
        time.sleep(5)
    raise Exception("Didn't get back a valid answer for: {}".format(url))


def allgamedata():
    data = getwithretry(BGG_URL)
    fh = DATA_PATH.open("w")
    fh.write(data)
    fh.close
    fh = DATA_PATH.open()
    tree = xml.etree.ElementTree.parse(fh)
    root = tree.getroot()
    ret = []
    for thing in root:
        name = thing.find("./name").text
        statusattrib = thing.find(".//status").attrib
        retstatus = "???"
        for status, state in statusattrib.items():
            if state == "1":
                retstatus = status
                break
        lastmodified = datetime.datetime.strptime(
            statusattrib["lastmodified"], "%Y-%m-%d %H:%M:%S"
        )
        # if thing.attrib["objectid"] == "155426":  # XXX hack for just one record
        ret.append((int(thing.attrib["objectid"]), retstatus, lastmodified, name))
    return ret


def updategameslist():
    count = 0
    gamedata = {}
    latestmod = dbconn().one("SELECT MAX(lastmodified) FROM games;")
    # Strip the timezone so it's the same as the incoming data
    latestmod = latestmod.replace(tzinfo=None)
    if not latestmod:
        latestmod = datetime.datetime.fromtimestamp(0)
    for gameid, status, lastmodified, name in allgamedata():
        fn = pathlib.Path("games/{}.xml".format(gameid))
        if lastmodified <= latestmod and fn.is_file():
            continue
        gamedata[gameid] = {
            "status": status,
            "lastmodified": lastmodified,
            "name": name,
        }
        count += 1
        log("Game count: {}, Getting id: {}".format(count, gameid))
        text = getwithretry(
            "https://www.boardgamegeek.com/xmlapi2/thing?id={}&stats=1".format(gameid)
        )
        fh = fn.open("w")
        fh.write(text)
        fh.close()
    return gamedata


def linkdata(gameid, data, datatable, jointable, idcol):
    if not data:
        log("No incoming data, ignoring")
        return
    statements = []
    args = []
    for row in data:
        statements.append(
            "INSERT INTO {} ({}, text) VALUES (%s, %s) ON CONFLICT DO NOTHING;".format(
                datatable, idcol
            )
        )
        statements.append(
            "INSERT INTO {} (gameid, {}) VALUES (%s, %s) ON CONFLICT DO NOTHING;".format(
                jointable, idcol
            )
        )
        args += [row["id"], row["text"], gameid, row["id"]]
    dbconn().run(" ".join(statements), args)


def linkcategories(gameid, categories):
    linkdata(gameid, categories, "categories", "gamecategory", "bggcategoryid")


def linkmechanics(gameid, mechanics):
    linkdata(gameid, mechanics, "mechanics", "gamemechanic", "bggmechanicid")


def latestplays():
    latestplay = common.getstate("latestplaydownload")
    if latestplay:
        latestplay = datetime.datetime.fromisoformat(latestplay) - datetime.timedelta(
            days=1
        )
    else:
        latestplay = datetime.datetime(2000, 1, 1)

    ret = []
    page = 1
    while 1:  # Keep going through all pages
        args = {
            "username": common.CONFIG["username"],
            "page": page,
            "mindate": latestplay,
        }
        root = xml.etree.ElementTree.fromstring(getwithretry(common.PLAYS_URL, args))
        for play in root:
            bggid = play.attrib["id"]
            date = datetime.datetime.fromisoformat(play.attrib["date"])
            gamebggid = int(play.find(".//item").attrib["objectid"])
            comments = play.find(".//comments")
            if comments is not None:
                comments = comments.text
            eplayers = play.find(".//players")
            players = []
            if eplayers is not None:
                for player in eplayers:
                    score = player.attrib["score"]
                    if score == "None":
                        score = None
                    rec = {
                        "name": player.attrib["name"],
                        "color": player.attrib["color"],
                        "score": score,
                        "new": player.attrib["new"] == "1",
                        "win": player.attrib["win"] == "1",
                    }
                    players.append(rec)
            ret.append(
                {
                    "bggid": bggid,
                    "date": date,
                    "gamebggid": gamebggid,
                    "comments": comments,
                    "players": players,
                }
            )

        totalitems = int(root.attrib["total"])
        log("Total plays: {}, Page number: {}".format(totalitems, page))
        if (page * 100) > totalitems:
            break
        page += 1
    common.setstate("latestplaydownload", datetime.datetime.now().isoformat())
    return ret


GAME_UPDATE_COLS = [
    "name",
    "description",
    "status",
    "expansionbggid",
    "rating",
    "complexity",
    "minage",
    "playingtime",
    "minplayers",
    "maxplayers",
    "yearpublished",
    "lastmodified",
]


def log(msg):
    logfh.write(msg + "\n")


def main(logfile=sys.stdout):
    global logfh
    logfh = logfile

    gamesinfo = updategameslist()
    GAME_INSERT_COLS = ["bggid"] + GAME_UPDATE_COLS
    GAME_VAL_COLS = ["%({})s".format(i) for i in GAME_INSERT_COLS]
    GAME_SET_COLS = ["{} = %({})s".format(i, i) for i in GAME_UPDATE_COLS]
    for bggid in gamesinfo:
        fn = GAMES_CACHE_PATH / "{}.xml".format(bggid)
        data = extractgamedata(fn.open(), gamesinfo[bggid])
        for game in data:
            expansionid = None
            if "expansion" in game:
                expansionid = game["expansion"]["id"]
            game["expansionbggid"] = expansionid
            dbconn().run(
                """INSERT INTO games (
                    {}
                ) VALUES (
                    {}
                ) ON CONFLICT ON CONSTRAINT games_bggid_key DO
                UPDATE SET {}""".format(
                    ", ".join(GAME_INSERT_COLS),
                    ", ".join(GAME_VAL_COLS),
                    ", ".join(GAME_SET_COLS),
                ),
                game,
            )
            gameid = dbconn().one(
                "SELECT id FROM games WHERE bggid = %s;", [game["bggid"]]
            )
            log("Game DB ID: {}".format(gameid))
            linkcategories(gameid, game["categories"])
            linkmechanics(gameid, game["mechanics"])

    # Upload plays queued up
    newplays = common.getplays(status=common.TO_UPLOAD)
    log("Uploading to BGG {} plays".format(len(newplays)))
    for play in newplays:
        bggid = common.postplay(play)
        dbconn().run(
            "UPDATE plays SET bggid = %s WHERE id = %s", [bggid, play["playid"]]
        )

    plays = latestplays()
    log("Updating {} plays".format(len(plays)))
    for play in plays:
        # This entire section relies on the DB to remove duplicates
        # both plays and players
        common.recordplay(play)


if __name__ == "__main__":
    main()
