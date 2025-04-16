<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up()
    {
        DB::statement("
            CREATE VIEW matches AS
            SELECT 
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
                        INSTR(SUBSTR(m.scores_csv, INSTR(m.scores_csv, '-') + 1), '\"') - 1
                    ) AS INTEGER)
                ) -
                MIN(
                    CAST(SUBSTR(m.scores_csv, 2, INSTR(m.scores_csv, '-') - 2) AS INTEGER),
                    CAST(SUBSTR(
                        m.scores_csv,
                        INSTR(m.scores_csv, '-') + 1,
                        INSTR(SUBSTR(m.scores_csv, INSTR(m.scores_csv, '-') + 1), '\"') - 1
                    ) AS INTEGER)
                ) AS set_balance,

                t.id AS tournament_id,
                t.\"name\" AS tournament_name,
                t.category AS tournament_category,
                strftime('%m/%Y', t.started_at) AS started_month_year,
                strftime('%Y', t.started_at) AS started_year,
                m.round AS round

            FROM challonge_matches m
            JOIN challonge_tournaments t ON t.id = m.tournament_id
            JOIN challonge_participants w ON w.id = m.winner_id
            JOIN challonge_participants l ON l.id = m.loser_id
        ");
    }

    public function down()
    {
        DB::statement('DROP VIEW IF EXISTS matches');
    }
}; 