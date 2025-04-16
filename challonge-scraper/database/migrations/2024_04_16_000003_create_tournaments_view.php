<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up()
    {
        DB::statement("
            CREATE VIEW tournaments AS
            SELECT 
                id,
                name,
                category,
                started_at,
                state,
                strftime('%m/%Y', started_at) AS started_month_year,
                strftime('%Y', started_at) AS started_year
            FROM challonge_tournaments
        ");
    }

    public function down()
    {
        DB::statement('DROP VIEW IF EXISTS tournaments');
    }
}; 