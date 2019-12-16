from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from werkzeug.routing import IntegerConverter
import json
import common
import copy
import threading
import subprocess

from PIL import Image

try:
    from pyzbar import pyzbar

    BARCODE_SUPPORT = True
except:
    BARCODE_SUPPORT = False

app = Flask(__name__)


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
        "index.html",
        games=common.querygames(),
        ALL_THUMBS=thumbsurl,
        spritesize=spritesize,
    )


@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


@app.route("/layout")
def gamelayout():
    games = common.querygames(extendedlocation=True)
    # Generates a grid of each section, and what's in each section
    # List of columns, each column has a section, and each section has rows
    # and each row has a list of games. The section also includes the height
    # of the row.
    # This is built from the config of the columns
    table = copy.deepcopy(common.CONFIG["columns"])

    columns = []
    # Format for our purposes
    for col in table:
        columns.append(col["id"])
        for section in col.get("sections", []):
            section["height"] = abs(section.get("start", 0) - section.get("end", 0)) + 1
            section["games"] = {}

    layout = {}
    maxrows = 1
    for game in games:
        if game["row"] is not None and game["col"] is not None:
            for col in table:
                if game["col"] == col["id"]:
                    break
            game["rowtop"] = game["row"] - game["rowstaken"] + 1
            shelf = layout.get((game["col"], game["rowtop"]), [])
            shelf.append(game)
            layout[(game["col"], game["rowtop"])] = shelf
            if game["row"] > maxrows:
                maxrows = game["row"]
            # for section in col["sections"]:
            #    if game["row"] >= section["start"] and game["row"] <= section["end"]:
            #        sectiongames = section["games"]
            #        rowgames = sectiongames.get(game["row"], [])
            #        rowgames.append(game)
            #        sectiongames[game["row"]] = rowgames

    # from pprint import pprint
    # pprint(table)
    tbodyhtml = []
    for row in range(maxrows):
        rowhtml = "<tr>"
        for col in columns:
            shelf = layout.get((col, row))
            if shelf:
                print(shelf)
                style = "border: 2px solid black;"
                if not shelf[0].get("topofsection"):
                    style += "border-top: none;"
                if not shelf[0].get("bottomofsection"):
                    style += "border-bottom: none;"
                if shelf[0]["rowstaken"] > 1:
                    span = "rowspan={}".format(shelf[0]["rowstaken"])
                else:
                    span = ""
                shelfhtml = ""
                for game in shelf:
                    shelfhtml += '<a href="/game/{}"><img src="{}"></a>'.format(
                        game["bggid"], game["thumburl"]
                    )

                rowhtml += '<td style="{}" {}>{}</td>'.format(style, span, shelfhtml)
        rowhtml += "</tr>"
        tbodyhtml.append(rowhtml)
    html = "\n".join(tbodyhtml)

    return render_template(
        "gamelayout.html", games=table, columns=columns, html=html, layout=layout
    )


@app.route("/game/<int(signed=True):bggid>")
def game(bggid):
    return render_template(
        "game.jinja",
        game=common.querygames(bggid=bggid, includeexpansions=True),
        formatkey=common.formatgamekey,
        groups=common.getgroups(),
    )


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
    if BARCODE_SUPPORT:
        content = json.loads(request.form["json"])
        rethtml = "<h1>No Barcode Found</h1>"
        ret
        if request.files:
            print("Got upload!", request.files)
            f = request.files["upimage"]
            i = Image.open(f)
            data = pyzbar.decode(i)
            if data:
                code = data[0].data.decode()
                if content.get("bggid"):
                    # Have a game ID, associate with the game, then redirect back
                    common.dbconn(ignoreerror=True).run(
                        "INSERT INTO barcodes (bggid, barcode) VALUES (%s, %s);",
                        [content["bggid"], code],
                    )
                    rethtml = "<h3>Found code: {}</h3>".format(code)
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
                    print("FOUND:", bggid, "Code:", code)
                    if bggid is None:
                        rethtml = "<h1>No Game Found Matching Barcode</h1>"
                        rethtml += "<p>Barcode: {}</p>".format(code)
                    else:
                        loc = locate(bggid)
                        if loc == "FAIL":
                            rethtml = "<h1>No Location Configured</h1>"
                        else:
                            rethtml = "<h2> Location: {}</h2>".format(loc)
        rethtml += "<p>Tap to clear</p>"
        ret["html"] = rethtml
    return jsonify(ret)


@app.route("/groups")
def groups():
    return render_template("groups.jinja")


@app.route("/plays/<int(signed=True):bgggameid>")
def plays(bgggameid):
    return jsonify(common.getplays(bgggameid))


@app.route("/recordplay", methods=["GET", "POST"])
def recordplay():
    content = request.json
    common.recordplay(content)
    return "OK"


@app.route("/playernames")
def playernames():
    return jsonify(common.getplayernames())


@app.route("/getgroups")
def getgroups():
    return jsonify(common.getgroups())


@app.route("/updategroups", methods=["GET", "POST"])
def updategroups():
    content = request.json
    common.updategroups(content)
    return "OK"


@app.route("/locate/<int(signed=True):bggid>")
def locate(bggid):
    game = common.querygames(bggid=bggid, formatvals=False, extendedlocation=True)
    if game["row"] is None or game["col"] is None:
        print("Game NOT found :( ")
        return "FAIL"

    ret = "Col: {}, Row: {} ({})".format(game["col"], game["row"], game["distancetxt"])
    # Figure out which LED we shuold light up
    section = game["sectionconfig"]
    print(section)
    if "ledstrips" in section:
        leds = []
        for striptxt, ledrange in section["ledstrips"].items():
            ledstrip = int(striptxt)
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
            print("Done run")

    return ret


def intifval(v):
    try:
        return int(v)
    except:
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

