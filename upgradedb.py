#!/usr/bin/env python3
import sys

from common import dbconn
import common


def main():
    dbconn().run("ALTER TABLE games ADD COLUMN IF NOT EXISTS image_w smallint;")
    dbconn().run("ALTER TABLE games ADD COLUMN IF NOT EXISTS image_h smallint;")
    dbconn().run("ALTER TABLE games ADD COLUMN IF NOT EXISTS thumb_w smallint;")
    dbconn().run("ALTER TABLE games ADD COLUMN IF NOT EXISTS thumb_h smallint;")
    dbconn().run("ALTER TABLE games ADD COLUMN IF NOT EXISTS imgid integer UNIQUE;")
    dbconn().run(
        """
        CREATE TABLE IF NOT EXISTS barcodes
            (
                id SERIAL UNIQUE,
                bggid BIGINT REFERENCES games(bggid),
                barcode TEXT UNIQUE
            );
        """
    )
    dbconn().run(
        """
        CREATE OR REPLACE FUNCTION next_imgid() RETURNS bigint
            LANGUAGE sql
            AS $$SELECT gs FROM generate_series(1, (SELECT COUNT(*) FROM games) + 10) AS gs EXCEPT (SELECT imgid FROM games) ORDER BY 1 LIMIT 1; $$;
        """
    )

    dbconn().run("UPDATE games SET imgid = next_imgid() WHERE imgid IS NULL;")
    dbconn().run("ALTER TABLE games ALtER COLUMN imgid SET DEFAULT next_imgid();")

    import updategames

    updategames.generatesprites()


if __name__ == "__main__":
    main()
