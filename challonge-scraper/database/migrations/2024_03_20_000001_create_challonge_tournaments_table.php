<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::create('challonge_tournaments', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('challonge_id')->unique();
            $table->string('name');
            $table->string('url');
            $table->string('tournament_type');
            $table->string('state');
            $table->dateTime('started_at')->nullable();
            $table->dateTime('completed_at')->nullable();
            $table->boolean('open_signup')->default(false);
            $table->boolean('hold_third_place_match')->default(false);
            $table->integer('participants_count')->default(0);
            $table->text('description')->nullable();
            $table->json('raw_data')->nullable(); // Armazena dados brutos da API
            $table->boolean('synced')->default(false);
            $table->dateTime('last_sync_at')->nullable();
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('challonge_tournaments');
    }
}; 