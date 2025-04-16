<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::create('challonge_matches', function (Blueprint $table) {
            $table->id();
            $table->foreignId('tournament_id')->constrained('challonge_tournaments')->onDelete('cascade');
            $table->unsignedBigInteger('challonge_id')->unique();
            $table->foreignId('player1_id')->nullable()->constrained('challonge_participants');
            $table->foreignId('player2_id')->nullable()->constrained('challonge_participants');
            $table->integer('round')->nullable();
            $table->string('state')->default('pending');
            $table->string('winner_id')->nullable();
            $table->string('loser_id')->nullable();
            $table->string('score')->nullable();
            $table->dateTime('started_at')->nullable();
            $table->dateTime('completed_at')->nullable();
            $table->boolean('underway')->default(false);
            $table->dateTime('underway_at')->nullable();
            $table->json('scores_csv')->nullable();
            $table->json('raw_data')->nullable(); // Armazena dados brutos da API
            $table->boolean('synced')->default(false);
            $table->dateTime('last_sync_at')->nullable();
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('challonge_matches');
    }
}; 