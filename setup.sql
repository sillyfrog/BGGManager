CREATE TABLE games
(
    id SERIAL UNIQUE,
    bggid BIGINT UNIQUE,
    name TEXT,
    description TEXT,
    status TEXT,
    rating REAL,
    complexity REAL,
    playingtime INT,
    minplayers INT,
    maxplayers INT,
    yearpublished INT,
    minage INT,
    expansionbggid BIGINT,
    lastmodified TIMESTAMPTZ
);

CREATE TABLE groups
(
    id SERIAL UNIQUE,
    name text
);

CREATE TABLE gamesinfo
(
    gamesid INT UNIQUE NOT NULL REFERENCES games(id),
    row INT,
    col INT,
    groupid INT REFERENCES groups(id)
);

DROP TABLE players;
DROP TABLE plays;
CREATE TABLE plays
(
    id SERIAL UNIQUE,
    bggid BIGINT UNIQUE,
    date TIMESTAMPTZ,
    gamebggid BIGINT,
    comments TEXT
);

CREATE INDEX ON plays
(gamebggid);

CREATE TABLE players
(
    id SERIAL UNIQUE,
    playsid INT REFERENCES plays(id),
    name TEXT,
    color TEXT,
    score INT,
    new BOOLEAN,
    win BOOLEAN,
    UNIQUE (playsid, name)
);

CREATE INDEX ON players
(playsid);

CREATE TABLE state
(
    id SERIAL UNIQUE,
    item TEXT UNIQUE,
    value TEXT
);


CREATE TABLE categories
(
    id SERIAL UNIQUE,
    bggcategoryid BIGINT UNIQUE,
    text TEXT
);

CREATE TABLE gamecategory
(
    id SERIAL UNIQUE,
    gameid BIGINT REFERENCES games(id),
    bggcategoryid BIGINT REFERENCES categories(bggcategoryid),
    UNIQUE (gameid, bggcategoryid)
);
CREATE INDEX ON gamecategory
(gameid);

CREATE TABLE mechanics
(
    id SERIAL UNIQUE,
    bggmechanicid BIGINT UNIQUE,
    text TEXT
);

CREATE TABLE gamemechanic
(
    id SERIAL UNIQUE,
    gameid BIGINT REFERENCES games(id),
    bggmechanicid BIGINT REFERENCES mechanics(bggmechanicid),
    UNIQUE (gameid, bggmechanicid)
);
CREATE INDEX ON gamemechanic
(gameid);
