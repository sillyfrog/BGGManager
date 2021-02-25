# To run in debug/development mode:
#   FLASK_DEBUG=1 flask run -h 0.0.0.0 -p 80
from flask import Flask, render_template, request, redirect, Response, jsonify
import common
import copy
import threading
import subprocess
import time

from PIL import Image

app = Flask(__name__, static_folder=str(common.DIR_BASE / "static"))


@app.route("/")
def index():
    try:
        allthumbs = common.THUMBS_PATH / "allthumbs.jpg"
        sprite = Image.open(allthumbs)
        spritesize = {
            "width": sprite.width / common.SPRITE_SCALE,
            "height": sprite.height / common.SPRITE_SCALE,
        }
        thumbsurl = "{}?{}".format(
            common.THUMBS_URL.format("allthumbs"), allthumbs.stat().st_mtime
        )
    except Exception:
        spritesize = {}
        thumbsurl = "nothing"
    return render_template(
        "index.jinja",
        games=common.querygames(),
        ALL_THUMBS=thumbsurl,
        spritesize=spritesize,
    )


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


@app.route("/layout")
@app.route("/layout/usedshelves")
def gamelayout():
    usedshelves = request.path.endswith("/usedshelves")
    games = common.querygames(extendedlocation=True)
    # Generates a grid of each section, and what's in each section
    # List of columns, each column has a section, and each section has rows
    # and each row has a list of games. The section also includes the height
    # of the row.
    # This is built from the config of the columns
    table = copy.deepcopy(common.CONFIG["columns"])

    columns = []
    columnstext = []
    # Format for our purposes
    for col in table:
        columns.append(col["id"])
        columnstext.append(col["name"])
        for section in col.get("sections", []):
            section["height"] = abs(section.get("start", 0) - section.get("end", 0)) + 1
            section["games"] = {}

    layout = {}
    maxrow = 1
    minrow = None
    for game in games:
        if game["row"] is not None and game["col"] is not None:
            for col in table:
                if game["col"] == col["id"]:
                    break
            game["rowtop"] = game["row"] - game["rowstaken"] + 1
            shelf = layout.get((game["col"], game["rowtop"]), [])
            shelf.append(game)
            layout[(game["col"], game["rowtop"])] = shelf
            if game["row"] > maxrow:
                maxrow = game["row"]
            if minrow is None or game["row"] < minrow:
                minrow = game["row"]

    # Check every column has at least one game and goes from top to bottom
    # if not, insert blank game as required
    if minrow is None:
        return "No game locations configured"
    for col in columns:
        coltop = None
        colbottom = None
        for row in range(minrow, maxrow + 1, 1):
            shelf = layout.get((col, row))
            if not shelf:
                continue
            if coltop is None:
                coltop = shelf[0]["rowtop"]
            colbottom = shelf[0]["row"]
        if coltop is None:
            # Entire column is empty, so insert a full column
            layout[(col, minrow)] = [
                {
                    "rowstaken": maxrow,
                    "bggid": None,
                    "thumburl": None,
                    "topofsection": True,
                    "bottomofsection": True,
                }
            ]
        else:
            if coltop > minrow:
                layout[(col, minrow)] = [
                    {
                        "rowstaken": minrow - coltop,
                        "bggid": None,
                        "thumburl": None,
                        "topofsection": True,
                        "bottomofsection": True,
                    }
                ]
            if colbottom < maxrow:
                layout[(col, colbottom + 1)] = [
                    {
                        "rowstaken": maxrow - colbottom,
                        "bggid": None,
                        "thumburl": None,
                        "topofsection": True,
                        "bottomofsection": True,
                    }
                ]

    tbodyhtml = []
    for row in range(minrow, maxrow + 1, 1):
        rowhtml = "<tr>"
        for col in columns:
            shelf = layout.get((col, row))
            if shelf:
                style = "border: 2px solid black;"
                if not shelf[0].get("topofsection"):
                    style += "border-top: 1px solid #ddd;"
                if not shelf[0].get("bottomofsection"):
                    style += "border-bottom: 1px solid #ddd;"
                if shelf[0]["rowstaken"] > 1:
                    span = "rowspan={}".format(shelf[0]["rowstaken"])
                else:
                    span = ""
                shelfhtml = ""
                for game in shelf:
                    if game["bggid"] is None:
                        shelfhtml += "&nbsp;"
                    else:
                        if usedshelves:
                            shelfhtml += "<h3>{}</h3>".format(game["row"])
                            break
                        else:
                            shelfhtml += '<a href="/game/{}"><img src="{}"></a>'.format(
                                game["bggid"], game["thumburl"]
                            )

                rowhtml += '<td style="{}" {}>{}</td>'.format(style, span, shelfhtml)
        rowhtml += "</tr>"
        tbodyhtml.append(rowhtml)
    html = "\n".join(tbodyhtml)

    if usedshelves:
        about = (
            "Shows which shelves are used, ideal when setting up your BoxThrone "
            "(eg: after moving house), so you know which shelves to fill."
        )
    else:
        about = (
            "Shows the order and layout (using game images) of all of the games "
            "that have a location on the shelves."
        )

    return render_template(
        "gamelayout.html",
        games=table,
        columns=columnstext,
        html=html,
        layout=layout,
        about=about,
    )


@app.route("/game/<int(signed=True):bggid>")
def game(bggid):
    return render_template(
        "game.jinja",
        game=common.querygames(bggid=bggid, includeexpansions=True),
        formatkey=common.formatgamekey,
        groups=common.getgroups(),
    )


@app.route("/customgame/<int(signed=True):bggid>", methods=["GET", "POST"])
def customgame(bggid):
    if request.method == "POST":
        if request.form.get("delete") == "delete" and bggid < 0:
            common.dbconn().run("DELETE FROM games WHERE bggid = %s;", [bggid])
            return redirect("/")

        if bggid == 0:
            # This is a new record get an ID and go to work
            common.dbconn().run(
                """
                INSERT INTO games (bggid) VALUES (
                    (SELECT MIN(bggid) FROM (SELECT bggid FROM games UNION SELECT 0 AS bggid) bggids)-1
                    );
                """
            )
            dbid = common.dbconn().one("SELECT lastval();")
            bggid = common.dbconn().one(
                "SELECT bggid FROM games WHERE id = %s;", [dbid]
            )
        if "image" in request.files and request.files["image"].filename != "":
            # New image, save it
            # Get the image ID
            imgpath = common.IMAGES_PATH / "{}.jpg".format(bggid)
            request.files["image"].save(str(imgpath))
            # Need to also make a thumbnail, will just use the same file
            thumbpath = common.THUMBS_PATH / "{}.jpg".format(bggid)
            thumbpath.open("wb").write(imgpath.open("rb").read())

            # Update the master sprite image
            common.generatesprites()

        # Save the rest of the fields
        common.dbconn().run(
            "UPDATE games SET name = %s, description = %s, status = %s WHERE bggid = %s;",
            [
                request.form["name"],
                request.form["description"],
                request.form["status"],
                bggid,
            ],
        )

        return redirect("/customgame/{}".format(bggid))
    else:
        if bggid == 0:
            # New game, need to assign an ID on POST
            game = {"status": "own"}
        else:
            game = common.querygames(bggid=bggid)
        return render_template("customgame.jinja", game=game, time=time.time())


@app.route("/scanbarcode")
def scanbarcode():
    return render_template(
        "scanbarcode.jinja",
        bggid=request.args.get("bggid"),
        putaway=request.args.get("putaway"),
    )


@app.route("/processbarcode", methods=["GET", "POST"])
def processbarcode():
    ret = {"html": "<h1>Not Supported</h1>"}
    content = request.get_json()
    rethtml = "<h1>Error</h1>"
    code = content["barcode"]
    if content.get("bggid"):
        # Have a game ID, associate with the game, then redirect back
        common.dbconn(ignoreerror=True).run(
            """INSERT INTO barcodes (bggid, barcode) 
                VALUES (%(bggid)s, %(code)s)
            ON CONFLICT (barcode) DO UPDATE
                SET bggid = %(bggid)s;""",
            {"bggid": content["bggid"], "code": code},
        )
        rethtml = "<h3>Added code: {}</h3>".format(code)
        js = """setTimeout(function () {{
            document.location = '/game/{}';
        }}, 2000);""".format(
            content["bggid"]
        )
        ret["js"] = js
    else:
        # Look up the game id
        bggid = common.dbconn().one(
            "SELECT bggid FROM barcodes WHERE barcode = %s;", [code]
        )
        if bggid is None:
            rethtml = "<h1>No Game Found Matching Barcode</h1>"
            rethtml += "<p>Barcode: {}</p>".format(code)
        else:
            game = common.querygames(bggid=bggid, extendedlocation=True)

            rethtml = "<small>{}</small>".format(code)
            if game["row"] is None or game["col"] is None:
                rethtml += "<h1>No Location Configured</h1>"
            else:
                highlightleds(game)
                loc = "Col: {}, Row: {} ({})".format(
                    game["col"], game["row"], game["distancetxt"]
                )
                if common.CONFIG.get("showlocationtable", True):
                    loc += "<br>" + game["locationhtml"]
                rethtml += "<h2> Location: {}</h2>".format(loc)
            rethtml += '<p><a href="/game/{}">{}</a></p>'.format(bggid, game["name"])
    rethtml += "<p>Tap to clear</p>"
    ret["html"] = rethtml
    return jsonify(ret)


@app.route("/groups")
def groups():
    return render_template("groups.jinja")


@app.route("/players")
def players():
    return render_template("players.html")


@app.route("/plays/<int(signed=True):bgggameid>")
def plays(bgggameid):
    return jsonify(common.getplays(bgggameid))


@app.route("/recordplay", methods=["GET", "POST"])
def recordplay():
    content = request.json
    common.recordplay(content)
    return "OK"


@app.route("/deleteplay", methods=["POST"])
def deleteplay():
    content = request.json
    common.markdeleteplay(content["playid"])
    return "OK"


@app.route("/playerdetails")
def playerdetails():
    return jsonify(common.getplayerdetails())


@app.route("/getgroups")
def getgroups():
    return jsonify(common.getgroups())


@app.route("/updategroups", methods=["GET", "POST"])
def updategroups():
    content = request.json
    common.updategroups(content)
    return "OK"


@app.route("/updateplayers", methods=["GET", "POST"])
def updateplayers():
    content = request.json
    common.updateplayers(content)
    return "OK"


def justint(src):
    """Returns an int, stripping non-digit trailing characters"""
    while src and not src[-1].isdigit():
        src = src[:-1]
    return int(src)


def highlightleds(game):
    """Calls the configured function to hightlight where the game should go"""
    # Figure out which LED we shuold light up
    section = game["sectionconfig"]
    if "ledstrips" in section:
        leds = []
        for striptxt, ledrange in section["ledstrips"].items():
            ledstrip = justint(striptxt)
            ledstart, ledend = ledrange
            ledcount = ledend - ledstart + 1
            rowcount = section["end"] - section["start"] + 1
            ledsperrow = (ledcount - 1) / (rowcount - 1)
            print(
                "LED count: {}, row count: {}, per row: {}, gamerow: {}".format(
                    ledcount, rowcount, ledsperrow, game["row"]
                )
            )
            firstled = ledstart + ledsperrow * (
                game["row"] - game["rowstaken"] - section["start"] + 1
            )
            lastled = ledstart + ledsperrow * (game["row"] - section["start"])
            if firstled > lastled:
                firstled, lastled = lastled, firstled
            # Queue up the LEDS to light up
            for led in range(round(firstled), round(lastled + 1)):
                leds.append("{},{}".format(ledstrip, led))
        # Call the configured program with the LED's to light up
        cmd = copy.deepcopy(common.CONFIG.get("ledscommand"))
        if cmd:
            cmd += leds
            print(cmd)
            t = threading.Thread(target=subprocess.run, args=(cmd,), daemon=True)
            t.start()


@app.route("/locate/<int(signed=True):bggid>")
def locate(bggid):
    game = common.querygames(bggid=bggid, formatvals=False, extendedlocation=True)
    if game["row"] is None or game["col"] is None:
        print("Game NOT found :( ")
        return "FAIL"

    ret = "Col: {}, Row: {} ({})".format(game["col"], game["row"], game["distancetxt"])
    if common.CONFIG.get("showlocationtable", True):
        ret += "<br>" + game["locationhtml"]
    highlightleds(game)

    return ret


def intifval(v):
    try:
        return int(v)
    except Exception:
        return None


@app.route("/updateinfo/<int(signed=True):bggid>", methods=["GET", "POST"])
def updateinfo(bggid):
    content = request.json
    col = intifval(content["col"])
    row = intifval(content["row"])
    groupid = intifval(content["groupid"])
    common.updateinfo(bggid=bggid, row=row, col=col, groupid=groupid)
    return "Saved"


@app.route("/games.json")
def gamesjson():
    games = common.dbconn().all("SELECT * FROM games ORDER BY name;", back_as=dict)
    return jsonify(games)


def stream_template(template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(2)
    return rv


@app.route("/sync")
def sync():
    import updategames
    from io import StringIO

    def dummystream():
        yield "Starting Sync Process"
        yield ""
        f = StringIO()
        updategames.main(f)

        f.seek(0)
        for l in f:
            yield l

    return Response(stream_template("syncgames.html", loglines=dummystream()))
