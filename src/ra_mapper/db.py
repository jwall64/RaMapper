import sqlite3

from .utils import now_millis


class DatabaseConnection:
    def __init__(self, path):
        try: 
            self.connection = sqlite3.connect(path)

            cursor = self.connection.cursor()
            self._init_db(cursor)

            self.connection.commit()
        except sqlite3.Error as e:
            print(e)
            exit(1)


    def _init_db(self, cursor: sqlite3.Cursor):

        cursor.execute("""
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK(id = 1), 
    schema_version INTEGER NOT NULL, 
    generated_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
""")

        cursor.execute("SELECT schema_version FROM meta;")
        rows = cursor.fetchall()

        if len(rows) == 0:
            now = now_millis()

            print("Initializing DB...")
            cursor.executescript("""
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE system (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    is_game_system INTEGER NOT NULL DEFAULT 0,
    fetched_at INTEGER NOT NULL
);

CREATE TABLE igdb_system (
    id INTEGER PRIMARY KEY,
    igdb_id INTEGER NOT NULL,
    is_engine INTEGER NOT NULL DEFAULT 0,
    UNIQUE (igdb_id, is_engine)
);

CREATE TABLE system_mapping (
    system_id INTEGER NOT NULL,
    igdb_system_id INTEGER NOT NULL,
    FOREIGN KEY (system_id) REFERENCES system(id),
    FOREIGN KEY (igdb_system_id) REFERENCES igdb_system(id),
    UNIQUE (system_id, igdb_system_id)
);

CREATE TABLE game (
    id INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    updated_at INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (system_id) REFERENCES system(id)
);

CREATE TABLE subset (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    updated_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE subset_parent (
    subset_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    FOREIGN KEY (subset_id) REFERENCES subset(id),
    FOREIGN KEY (game_id) REFERENCES game(id),
    UNIQUE (subset_id, game_id)
);

CREATE TABLE game_mapping (
    game_id INTEGER,
    igdb_id INTEGER,
    FOREIGN KEY (game_id) REFERENCES game(id)
    UNIQUE (game_id, igdb_id)
);

CREATE TABLE game_tag (
    game_id INTEGER,
    tag TEXT,
    FOREIGN KEY (game_id) REFERENCES game(id)
);
""")
            cursor.execute("INSERT INTO meta (id, schema_version, generated_at, updated_at) VALUES (?, ?, ?, ?);", [1, 1, now, now])
            
            print("Initialized DB")

        elif rows[0][0] != 1:
            print("Unsupported database version: ", rows[0][0])
            exit(1)
        else:
            cursor.execute(
                "UPDATE meta SET updated_at=?;", 
                [now_millis()]
            )
    
    def cursor(self):
        return self.connection.cursor()
    
    def commit(self):
        self.connection.commit()


