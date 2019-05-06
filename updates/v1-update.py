#!/usr/bin/env python3
import sys

sys.path.append("..")
from common import dbconn


def main():
    # Just ignore all errors, as it means the item has probably already been created
    dbconn(ignoreerror=True).run("ALTER TABLE games ADD COLUMN image_w smallint;")
    dbconn(ignoreerror=True).run("ALTER TABLE games ADD COLUMN image_h smallint;")
    dbconn(ignoreerror=True).run("ALTER TABLE games ADD COLUMN thumb_w smallint;")
    dbconn(ignoreerror=True).run("ALTER TABLE games ADD COLUMN thumb_h smallint;")
    dbconn(ignoreerror=True).run(
        """
        CREATE TABLE barcodes
            (
                id SERIAL UNIQUE,
                bggid BIGINT REFERENCES games(bggid),
                barcode TEXT UNIQUE
            );
        """
    )


if __name__ == "__main__":
    main()
