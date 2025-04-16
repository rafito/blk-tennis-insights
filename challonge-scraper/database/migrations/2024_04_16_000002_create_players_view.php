<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    public function up()
    {
        DB::statement("
            CREATE VIEW players AS
            SELECT 
                id,
                name
            FROM challonge_participants
        ");
    }

    public function down()
    {
        DB::statement('DROP VIEW IF EXISTS players');
    }
}; 