<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ChallongeMatch extends Model
{
    protected $fillable = [
        'tournament_id',
        'challonge_id',
        'player1_id',
        'player2_id',
        'round',
        'state',
        'winner_id',
        'loser_id',
        'score',
        'started_at',
        'completed_at',
        'underway',
        'underway_at',
        'scores_csv',
        'raw_data',
        'synced',
        'last_sync_at'
    ];

    protected $casts = [
        'raw_data' => 'array',
        'scores_csv' => 'array',
        'underway' => 'boolean',
        'synced' => 'boolean',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
        'underway_at' => 'datetime',
        'last_sync_at' => 'datetime'
    ];

    public function tournament()
    {
        return $this->belongsTo(ChallongeTournament::class, 'tournament_id');
    }

    public function player1()
    {
        return $this->belongsTo(ChallongeParticipant::class, 'player1_id');
    }

    public function player2()
    {
        return $this->belongsTo(ChallongeParticipant::class, 'player2_id');
    }
} 