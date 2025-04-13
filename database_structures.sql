-- --------------------------------------------------------
-- Servidor:                     C:\Users\rafit\Repos\devorama\blk-tennis-team\database\database.sqlite
-- Versão do servidor:           3.48.0
-- OS do Servidor:               
-- HeidiSQL Versão:              12.10.0.7000
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES  */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Copiando estrutura do banco de dados para database
CREATE DATABASE IF NOT EXISTS "database";
;

-- Copiando estrutura para view database.matches
-- Criando tabela temporária para evitar erros de dependência de VIEW
CREATE TABLE "matches" (
	"match_id" INTEGER NULL,
	"winner_id" INTEGER NULL,
	"winner_name" VARCHAR(1) NULL,
	"loser_id" INTEGER NULL,
	"loser_name" VARCHAR(1) NULL,
	"score" TEXT NULL,
	"set_balance" UNKNOWN NULL,
	"tournament_id" INTEGER NULL,
	"tournament_name" VARCHAR(1) NULL,
	"tournament_category" VARCHAR(1) NULL,
	"started_month_year" UNKNOWN NULL,
	"started_year" UNKNOWN NULL,
	"round" INTEGER NULL
) ENGINE=MyISAM;

-- Copiando estrutura para view database.players
-- Criando tabela temporária para evitar erros de dependência de VIEW
CREATE TABLE "players" (
	"id" INTEGER NULL,
	"name" VARCHAR(1) NULL
) ENGINE=MyISAM;

-- Copiando estrutura para view database.tournaments
-- Criando tabela temporária para evitar erros de dependência de VIEW
CREATE TABLE "tournaments" (
	"id" INTEGER NULL,
	"name" VARCHAR(1) NULL,
	"category" VARCHAR(1) NULL,
	"started_at" DATETIME NULL,
	"state" VARCHAR(1) NULL,
	"started_month_year" UNKNOWN NULL,
	"started_year" UNKNOWN NULL
) ENGINE=MyISAM;

-- Removendo tabela temporária e criando a estrutura VIEW final
DROP TABLE IF EXISTS "matches";
CREATE VIEW "matches" AS SELECT 
    m.id AS match_id,
    w.id AS winner_id,
    w.display_name AS winner_name,
    l.id AS loser_id,
    l.display_name AS loser_name,
    m.scores_csv AS score,

    -- Saldo
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
    t."name" AS tournament_name,
    t.category AS tournament_category,
    strftime('%m/%Y', t.started_at) AS started_month_year,
    strftime('%Y', t.started_at) AS started_year,
    m.round AS round

FROM challonge_matches m
JOIN challonge_tournaments t ON t.id = m.tournament_id
JOIN challonge_participants w ON w.id = m.winner_id
JOIN challonge_participants l ON l.id = m.loser_id
;

-- Removendo tabela temporária e criando a estrutura VIEW final
DROP TABLE IF EXISTS "players";
CREATE VIEW "players" AS SELECT id, name FROM challonge_participants
;

-- Removendo tabela temporária e criando a estrutura VIEW final
DROP TABLE IF EXISTS "tournaments";
CREATE VIEW "tournaments" AS SELECT id, name, category, started_at, STATE,

    strftime('%m/%Y', started_at) AS started_month_year,
    strftime('%Y', started_at) AS started_year
	  FROM challonge_tournaments
;

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
