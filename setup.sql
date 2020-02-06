CREATE TABLE IF NOT EXISTS games
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

CREATE TABLE IF NOT EXISTS groups
(
    id SERIAL UNIQUE,
    name text
);

CREATE TABLE IF NOT EXISTS gamesinfo
(
    gamesid INT UNIQUE NOT NULL REFERENCES games(id),
    row INT,
    col INT,
    groupid INT REFERENCES groups(id)
);

DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS plays;
CREATE TABLE IF NOT EXISTS plays
(
    id SERIAL UNIQUE,
    bggid BIGINT UNIQUE,
    date TIMESTAMPTZ,
    gamebggid BIGINT,
    comments TEXT
);

CREATE INDEX IF NOT EXISTS plays_gamebggid_idx ON plays
(gamebggid);

CREATE TABLE IF NOT EXISTS players
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

CREATE INDEX IF NOT EXISTS players_playsid_idx ON players
(playsid);

CREATE TABLE IF NOT EXISTS state
(
    id SERIAL UNIQUE,
    item TEXT UNIQUE,
    value TEXT
);


CREATE TABLE IF NOT EXISTS categories
(
    id SERIAL UNIQUE,
    bggcategoryid BIGINT UNIQUE,
    text TEXT
);

CREATE TABLE IF NOT EXISTS gamecategory
(
    id SERIAL UNIQUE,
    gameid BIGINT REFERENCES games(id),
    bggcategoryid BIGINT REFERENCES categories(bggcategoryid),
    UNIQUE (gameid, bggcategoryid)
);
CREATE INDEX IF NOT EXISTS gamecategory_gameid_idx ON gamecategory
(gameid);

CREATE TABLE IF NOT EXISTS mechanics
(
    id SERIAL UNIQUE,
    bggmechanicid BIGINT UNIQUE,
    text TEXT
);

CREATE TABLE IF NOT EXISTS gamemechanic
(
    id SERIAL UNIQUE,
    gameid BIGINT REFERENCES games(id),
    bggmechanicid BIGINT REFERENCES mechanics(bggmechanicid),
    UNIQUE (gameid, bggmechanicid)
);
CREATE INDEX IF NOT EXISTS gamemechanic_gameid_idx ON gamemechanic
(gameid);
