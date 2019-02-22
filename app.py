from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from werkzeug.routing import IntegerConverter
import json
import common
import copy
import threading
import subprocess

app = Flask(__name__)

# XXX Should be able to do away with this with next release of werkzeug
class SignedIntConverter(IntegerConverter):
    regex = r"-?\d+"


app.url_map.converters["signed_int"] = SignedIntConverter


@app.route("/")
def index():
    return render_template("index.html", games=common.querygames())


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


@app.route("/game/<signed_int:bggid>")
def game(bggid):
    return render_template(
        "game.jinja",
        game=common.querygames(bggid=bggid, includeexpansions=True),
        formatkey=common.formatgamekey,
        groups=common.getgroups(),
    )


@app.route("/groups")
def groups():
    return render_template("groups.jinja")


@app.route("/plays/<signed_int:bgggameid>")
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


@app.route("/locate/<signed_int:bggid>")
def locate(bggid):
    game = common.querygames(bggid=bggid, formatvals=False, extendedlocation=True)
    if game["row"] is None or game["col"] is None:
        print("Game NOT found :( ")
        return "FAIL"

    ret = "Col: {}, Row: {} ({})".format(game["col"], game["row"], game["distancetxt"])
    print("XXX Locating game at: {} x {}".format(game["col"], game["row"]))
    # Figure out which LED we shuold light up
    section = game["sectionconfig"]
    print(section)
    if section.get("ledstart") is not None and section.get("ledend") is not None:
        ledcount = section["ledend"] - section["ledstart"] + 1
        rowcount = section["end"] - section["start"] + 1
        ledsperrow = (ledcount - 1) / (rowcount - 1)
        print(
            "LED count: {}, row count: {}, per row: {}, gamerow: {}".format(
                ledcount, rowcount, ledsperrow, game["row"]
            )
        )
        firstled = section["ledstart"] + ledsperrow * (
            game["row"] - game["rowstaken"] - section["start"] + 1
        )
        lastled = section["ledstart"] + ledsperrow * (game["row"] - section["start"])
        if firstled > lastled:
            firstled, lastled = lastled, firstled
        print(
            "XXX Lighting up LEDs {} to {} on strips {}".format(
                (firstled), (lastled), section["ledstrips"]
            )
        )
        # Call the configured program with the LED's to light up
        leds = []
        for strip in section["ledstrips"]:
            for led in range(round(firstled), round(lastled + 1)):
                leds.append("{},{}".format(strip, led))
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


@app.route("/updateinfo/<signed_int:bggid>", methods=["GET", "POST"])
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

