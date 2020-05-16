var playernames = ['Example', 'Names', 'Here'];
var currentPlayId = null;
var gamePlays = {};

$(document).ready(function () {
    // Update the list of available usernames
    fetch('/playernames')
        .then(function (response) {
            return response.json();
        })
        .then(function (response) {
            playernames = response;
        });
});

function locategame() {
    var b = document.getElementById("locate");
    b.innerHTML = "Locating... ";
    b.classList.remove('btn-primary');
    b.classList.remove('btn-success');
    b.classList.remove('btn-danger');
    b.classList.add('btn-info');

    fetch('/locate/' + bggid)
        .then(function (response) {
            return response.text();
        })
        .then(function (response) {
            b.classList.remove('btn-info');
            if (response == "FAIL") {
                text = "Not found ☹️";
                b.classList.add('btn-danger');
            } else {
                text = "Location: " + response;
                b.classList.add('btn-success');
            }
            b.innerHTML = text;
        });
}

function updateinfo() {
    var b = document.getElementById("updateinfo");
    b.innerHTML = "Updating... ";
    b.classList.remove('btn-primary');
    b.classList.remove('btn-success');
    b.classList.remove('btn-danger');
    b.classList.add('btn-info');
    var row = document.getElementById("row").value;
    var col = document.getElementById("col").value;
    var groupid = document.getElementById("groupid").value;
    fetch('/updateinfo/' + bggid, {
        headers: {
            'Content-Type': 'application/json'
        },
        method: "POST",
        body: JSON.stringify({ 'row': row, 'col': col, 'groupid': groupid })
    })
        .then(function (response) {
            return response.text();
        })
        .then(function (response) {
            document.getElementById("updateinfo").innerHTML = response;
            b.classList.remove('btn-info');
            b.classList.add('btn-success');
        });
}

function addPlayer(row, player) {
    var txt = player.name;
    if (player.win) {
        txt += " 🏆";
    }
    if (player.new) {
        txt += " 🆕";
    }
    row.insertCell().innerText = txt;
    row.insertCell().innerText = player.score;
    row.insertCell().innerText = player.color;
}

function updatePlays() {
    var tbody = document.getElementById("plays");

    while (tbody.rows.length > 0) tbody.deleteRow(-1);

    // Update the display to say it's updating...
    cell = tbody.insertRow().insertCell();
    cell.colSpan = 4;
    cell.innerText = "Updating...";

    stats = {};

    fetch('/plays/' + bggid)
        .then(function (response) {
            return response.json();
        })
        .then(function (plays) {
            gamePlays = {};
            while (tbody.rows.length > 0) tbody.deleteRow(-1);
            var oddrow = true;
            for (var play of plays) {
                gamePlays[play.playid] = play;
                row = tbody.insertRow();
                oddrow = !oddrow;
                if (oddrow) row.classList.add("table-info");
                if (play.sync_state === "delete") {
                    row.style.textDecoration = "line-through";
                    row.classList.add("text-muted");
                }

                var datecell = row.insertCell();
                datecell.dataset['playid'] = play.playid;
                h = document.createElement("h5");
                h.innerText = play.date;
                if (play.players.length >= 2) {
                    datecell.rowSpan = play.players.length;
                }
                var editbutton = $('<div class="dropdown float-right">' +
                    '<button type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" class="btn btn-outline-secondary dropdown-toggle btn-sm">Edit</button>' +
                    '<div class="dropdown-menu">' +
                    '  <button class="dropdown-item" type="button" onclick="editPlay(this);">Edit…</button>' +
                    '  <button class="dropdown-item" type="button" onclick="deletePlay(this);">Delete</button>' +
                    '</div>' +
                    '</div>');
                if (play.sync_state !== "delete") {
                    $(datecell).append(editbutton);
                }
                datecell.appendChild(h);
                if (play.comments) {
                    c = document.createElement("p");
                    c.innerText = play.comments;
                    datecell.appendChild(c);
                }

                for (player of play.players) {
                    if (row == null) {
                        row = tbody.insertRow();
                        if (oddrow) row.classList.add("table-info");
                        if (play.sync_state === "delete") {
                            row.style.textDecoration = "line-through";
                            row.classList.add("text-muted");
                        }
                    }
                    addPlayer(row, player);
                    playerstats = stats[player.name] || { "wins": 0, "plays": 0, "totalscores": 0, "countscores": 0, "highscore": null, "lowscore": null };
                    if (player.win) {
                        playerstats.wins += 1;
                    }
                    playerstats.plays += 1;
                    if (player.score != null) {
                        playerstats.totalscores += player.score;
                        playerstats.countscores += 1;
                        if (playerstats.highscore == null || player.score > playerstats.highscore) {
                            playerstats.highscore = player.score;
                        }
                        if (playerstats.lowscore == null || player.score < playerstats.lowscore) {
                            playerstats.lowscore = player.score;
                        }
                    }
                    stats[player.name] = playerstats;

                    row = null;
                }
            }

            playsstats(stats);
        });
}

function playsstats(stats) {
    var donughtdata = [];
    var tabledata = [];
    for (var player in stats) {
        pstats = stats[player];
        if (pstats.wins) {
            donughtdata.push({ "name": player, "value": pstats.wins });
        }
        tabledata.push([player, pstats.wins, pstats.plays, (pstats.wins / pstats.plays * 100).toFixed(0) + "%", (pstats.totalscores / pstats.countscores).toFixed(1), pstats.highscore, pstats.lowscore]);
    }
    donughtdata.sort((a, b) => a.value - b.value);
    var e = document.getElementById("play-donught");
    e.innerHTML = '';
    if (donughtdata.length) {
        e.appendChild(donughtchart(donughtdata, "Wins"));
    } else {
        e.innerHTML = "<h4>No wins recorded</h4>";
    }

    tabledata.sort((a, b) => {
        // Don't sort by name, start at col 2
        for (var i = 1; i < 6; i++) {
            if (a[i] != b[i]) {
                // Reverse order
                return b[i] - a[i];
            }
        }
        return 0;
    });
    document.getElementById("statsdata").innerHTML = "";
    rows = d3.select("#statsdata")
        .selectAll("tr")
        .data(tabledata)
        .enter()
        .append("tr");
    rows.selectAll("td")
        .data(row => row)
        .enter()
        .append("td")
        .text(e => e);

}

function recordPlay() {
    var b = document.getElementById("recordplaybtn");

    // Get all of the play information
    play = {
        'gamebggid': bggid,
        'date': $('#date')[0].value,
        'comments': $('#comments')[0].value
    };

    if (currentPlayId) {
        play['playid'] = currentPlayId;
    }

    var tbody = document.getElementById("newplaybody");
    var players = [];
    for (row of tbody.rows) {
        var jqrow = $(row);
        var playername = jqrow.find("input[name=player]")[0].value;
        if (playername.length > 0) {
            players.push({
                "name": playername,
                "color": jqrow.find("input[name=color]")[0].value,
                "score": parseInt(jqrow.find("input[name=score]")[0].value),
                "win": jqrow.find("input[name=win]")[0].checked,
                "new": jqrow.find("input[name=new]")[0].checked
            })
        }
    };
    play['players'] = players;

    if (!play['comments'] && !players.length) {
        alert("Need to include something! 😀");
        return;
    }
    b.innerHTML = "Saving... ";
    b.classList.remove('btn-primary');
    b.classList.remove('btn-success');
    b.classList.remove('btn-danger');
    b.classList.add('btn-info');

    console.log("This is the play:", play);
    console.log(JSON.stringify(play));
    fetch('/recordplay', {
        headers: {
            'Content-Type': 'application/json'
        },
        method: "POST",
        body: JSON.stringify(play)
    })
        .then(function (response) {
            return response.text();
        })
        .then(function (response) {
            var b = document.getElementById("recordplaybtn");
            b.classList.remove('btn-info');
            if (response == "OK") {
                resetLogPlayForm();
                updatePlays();
            } else {
                b.innerText = "Error: " + response;
                b.classList.add('btn-danger');
            }
        });
}

function resetLogPlayForm() {
    var b = document.getElementById("recordplaybtn");
    b.classList.remove('btn-info');
    b.innerText = "Record Play";
    b.classList.add('btn-primary');
    $("#logplaydiv").hide();
    $("#logplaybtn")[0].disabled = false;
    // Clear out the logged play info
    var tbody = $("#newplaybody")[0];
    while (tbody.rows.length > 0) tbody.deleteRow(-1);
    $('#comments')[0].value = '';
}

function blurPlayer(obj) {
    if (obj.value) {
        if (($(obj).closest('tr').index() + 1) == $(obj).closest('tbody')[0].rows.length) {
            addNewPlayPlayer();
        }
    }
}

function addNewPlayPlayer() {
    var row = $("<tr>");
    var cell = $("<td>");
    playerinput = $('<input type="text" style="width: 8em;" name="player" class="typeahead" data-provide="typeahead" onBlur="blurPlayer(this);" />');
    playerinput.appendTo(cell);
    cell.appendTo(row);

    var cell = $("<td>");
    input = $('<input style="width: 5em;" name="score" type="number" pattern="\\d*" />');
    input.appendTo(cell)
    cell.appendTo(row);

    var cell = $("<td>");
    input = $('<div class="input-group-text"><input name="win" type="checkbox" /></div>');
    input.appendTo(cell)
    cell.appendTo(row);

    var cell = $("<td>");
    input = $('<div class="input-group-text"><input name="new" type="checkbox" /></div>');
    input.appendTo(cell)
    cell.appendTo(row);

    var cell = $("<td>");
    input = $('<input style="width: 6em;" name="color" type="text" />');
    input.appendTo(cell)
    cell.appendTo(row);

    row.appendTo($("#newplaybody"));

    playerinput.typeahead({
        hint: true,
        highlight: true,
        minLength: 0
    },
        {
            name: 'playerusernames',
            limit: 15,
            source: substringMatcher(playernames)
        });
    playerinput[0].style.backgroundColor = "";
    return row;
}

function editPlay(e) {
    resetLogPlayForm();
    currentPlayId = $(e).closest("td[data-playid]")[0].dataset.playid;
    var play = gamePlays[currentPlayId];
    $("#date").val(play.date);
    $("#comments").val(play.comments);

    for (var player of play.players) {
        var row = addNewPlayPlayer();
        row.find("input[name=player]").val(player.name);
        row.find("input[name=score]").val(player.score);
        row.find("input[name=color]").val(player.color);
        row.find("input[name=win]").prop('checked', player.win);
        row.find("input[name=new]").prop('checked', player.new);
    }
    addNewPlayPlayer();
    $("#logplaydiv").show();
    location.hash = "#top";
    location.hash = "#logplay";
    $("#logplaybtn")[0].disabled = true;
}

function isotoday() {
    var now = new Date();
    var year = now.getFullYear().toFixed(0);
    var month = (now.getMonth() + 1).toFixed(0).padStart(2, "0");
    var day = now.getDate().toFixed(0).padStart(2, "0");
    return year + "-" + month + "-" + day;
}


function logplay() {
    resetLogPlayForm();
    currentPlayId = null;
    $("#date")[0].value = isotoday();
    addNewPlayPlayer();
    $("#logplaydiv").show();
    location.hash = "#top";
    location.hash = "#logplay";
    $("#logplaybtn")[0].disabled = true;
}

var toDeletePlayId;
function deletePlay(e) {
    toDeletePlayId = $(e).closest("td[data-playid]")[0].dataset.playid;
    $("#modalPlayDate").text(gamePlays[toDeletePlayId].date);
    $("#modalConfirmDelete").modal("show");
}

function actionDeletePlay() {
    $("#btnDoDelete").text("Deleting...");
    fetch('/deleteplay', {
        headers: {
            'Content-Type': 'application/json'
        },
        method: "POST",
        body: JSON.stringify({ 'playid': toDeletePlayId })
    })
        .then(function (response) {
            return response.text();
        })
        .then(function (response) {
            if (response == "OK") {
                $("#btnDoDelete").text("Done");
                toDeletePlayId = null;
                window.location.reload();
            } else {
                $("#btnDoDelete").text("Error: " + response);
            }
        });
}

// Crap for the type ahead/combobox

var substringMatcher = function (strs) {
    return function findMatches(q, cb) {
        var matches, substringRegex;

        // an array that will be populated with substring matches
        matches = [];

        // regex used to determine if a string contains the substring `q`
        substrRegex = new RegExp(q, 'i');

        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function (i, str) {
            if (substrRegex.test(str)) {
                matches.push(str);
            }
        });

        cb(matches);
    };
};