<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::create('challonge_participants', function (Blueprint $table) {
            $table->id();
            $table->foreignId('tournament_id')->constrained('challonge_tournaments')->onDelete('cascade');
            $table->unsignedBigInteger('challonge_id')->unique();
            $table->string('name');
            $table->integer('seed')->nullable();
            $table->string('display_name')->nullable();
            $table->string('username')->nullable();
            $table->string('email')->nullable();
            $table->boolean('checked_in')->default(false);
            $table->dateTime('checked_in_at')->nullable();
            $table->boolean('active')->default(true);
            $table->integer('final_rank')->nullable();
            $table->json('raw_data')->nullable(); // Armazena dados brutos da API
            $table->boolean('synced')->default(false);
            $table->dateTime('last_sync_at')->nullable();
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('challonge_participants');
    }
}; 