var playernames = ['Example', 'Names', 'Here'];

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

    fetch('/plays/' + bggid)
        .then(function (response) {
            return response.json();
        })
        .then(function (plays) {
            while (tbody.rows.length > 0) tbody.deleteRow(-1);
            var oddrow = true;
            for (i = 0; i < plays.length; i++) {
                play = plays[i];
                row = tbody.insertRow();
                oddrow = !oddrow;
                if (oddrow) row.classList.add("table-info");

                var datecell = row.insertCell();
                h = document.createElement("h5");
                h.innerText = play.date;
                datecell.appendChild(h);
                if (play.comments) {
                    c = document.createElement("p");
                    c.innerText = play.comments;
                    datecell.appendChild(c);
                }

                if (play.players.length >= 2) {
                    datecell.rowSpan = play.players.length;
                }
                for (player of play.players) {
                    if (row == null) {
                        row = tbody.insertRow();
                        if (oddrow) row.classList.add("table-info");
                    }
                    addPlayer(row, player);
                    row = null;
                }
            }
        });
}

function recordPlay() {
    var b = document.getElementById("recordplaybtn");

    // Get all of the play information
    play = {
        'gamebggid': bggid,
        'date': $('#date')[0].value,
        'comments': $('#comments')[0].value
    };

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
                b.innerText = "Record Play";
                b.classList.add('btn-primary');
                $("#logplaydiv")[0].style.display = "none";
                $("#logplaybtn")[0].disabled = false;
                // Clear out the logged play info
                var tbody = $("#newplaybody")[0];
                while (tbody.rows.length > 0) tbody.deleteRow(-1);
                $('#comments')[0].value = '';
                updatePlays();
            } else {
                b.innerText = "Error: " + response;
                b.classList.add('btn-danger');
            }
        });
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
}

function logplay() {
    $("#logplaydiv")[0].style.display = "";
    var now = new Date();
    var isodate = now.toISOString().substring(0, 10);
    $("#date")[0].value = isodate;
    addNewPlayPlayer();
    location.hash = "#top";
    location.hash = "#logplay";
    $("#logplaybtn")[0].disabled = true;
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