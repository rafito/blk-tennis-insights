-- BLK Tennis Insights — esquema SQLite (substitui migrations Laravel para bootstrap Python)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE,
    email_verified_at DATETIME NULL,
    password VARCHAR NOT NULL,
    remember_token VARCHAR NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS challonge_tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    challonge_id INTEGER NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    category VARCHAR NULL,
    url VARCHAR NOT NULL,
    tournament_type VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    open_signup INTEGER NOT NULL DEFAULT 0,
    hold_third_place_match INTEGER NOT NULL DEFAULT 0,
    participants_count INTEGER NOT NULL DEFAULT 0,
    description TEXT NULL,
    raw_data TEXT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    last_sync_at DATETIME NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS challonge_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
    tournament_id INTEGER NOT NULL REFERENCES challonge_tournaments(id) ON DELETE CASCADE,
    challonge_id INTEGER NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    seed INTEGER NULL,
    display_name VARCHAR NULL,
    username VARCHAR NULL,
    email VARCHAR NULL,
    checked_in INTEGER NOT NULL DEFAULT 0,
    checked_in_at DATETIME NULL,
    active INTEGER NOT NULL DEFAULT 1,
    final_rank INTEGER NULL,
    raw_data TEXT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    last_sync_at DATETIME NULL,
    player_id INTEGER NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL
);

CREATE TABLE IF NOT EXISTS challonge_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    tournament_id INTEGER NOT NULL REFERENCES challonge_tournaments(id) ON DELETE CASCADE,
    challonge_id INTEGER NOT NULL UNIQUE,
    player1_id INTEGER NULL REFERENCES challonge_participants(id),
    player2_id INTEGER NULL REFERENCES challonge_participants(id),
    round INTEGER NULL,
    state VARCHAR NOT NULL DEFAULT 'pending',
    winner_id VARCHAR NULL,
    loser_id VARCHAR NULL,
    score VARCHAR NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    underway INTEGER NOT NULL DEFAULT 0,
    underway_at DATETIME NULL,
    scores_csv TEXT NULL,
    raw_data TEXT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    last_sync_at DATETIME NULL,
    created_at DATETIME NULL,
    updated_at DATETIME NULL
);

DROP VIEW IF EXISTS matches;
CREATE VIEW matches AS
SELECT
    m.id AS match_id,
    w.id AS winner_id,
    w.display_name AS winner_name,
    l.id AS loser_id,
    l.display_name AS loser_name,
    m.scores_csv AS score,
    MAX(
        CAST(SUBSTR(m.scores_csv, 2, INSTR(m.scores_csv, '-') - 2) AS INTEGER),
        CAST(SUBSTR(
            m.scores_csv,
            INSTR(m.scores_csv, '-') + 1,
            INSTR(SUBSTR(m.scores_csv, INSTR(m.scores_csv, '-') + 1), '"') - 1
        ) AS INTEGER)
    ) -
    MIN(
        CAST(SUBSTR(m.scores_csv, 2, INSTR(m.scores_csv, '-') - 2) AS INTEGER),
        CAST(SUBSTR(
            m.scores_csv,
            INSTR(m.scores_csv, '-') + 1,
            INSTR(SUBSTR(m.scores_csv, INSTR(m.scores_csv, '-') + 1), '"') - 1
        ) AS INTEGER)
    ) AS set_balance,
    t.id AS tournament_id,
    t.name AS tournament_name,
    t.category AS tournament_category,
    strftime('%m/%Y', t.started_at) AS started_month_year,
    strftime('%Y', t.started_at) AS started_year,
    m.round AS round
FROM challonge_matches m
JOIN challonge_tournaments t ON t.id = m.tournament_id
JOIN challonge_participants w ON w.id = m.winner_id
JOIN challonge_participants l ON l.id = m.loser_id;

DROP VIEW IF EXISTS players;
CREATE VIEW players AS
SELECT id, name FROM challonge_participants;

DROP VIEW IF EXISTS tournaments;
CREATE VIEW tournaments AS
SELECT
    id,
    name,
    category,
    started_at,
    state,
    strftime('%m/%Y', started_at) AS started_month_year,
    strftime('%Y', started_at) AS started_year
FROM challonge_tournaments;
