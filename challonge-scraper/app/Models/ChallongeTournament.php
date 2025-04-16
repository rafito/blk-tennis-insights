<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ChallongeTournament extends Model
{
    protected $fillable = [
        'challonge_id',
        'name',
        'category',
        'url',
        'tournament_type',
        'state',
        'started_at',
        'completed_at',
        'open_signup',
        'hold_third_place_match',
        'participants_count',
        'description',
        'raw_data',
        'synced',
        'last_sync_at'
    ];

    protected $casts = [
        'raw_data' => 'array',
        'open_signup' => 'boolean',
        'hold_third_place_match' => 'boolean',
        'synced' => 'boolean',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
        'last_sync_at' => 'datetime'
    ];

    public function participants()
    {
        return $this->hasMany(ChallongeParticipant::class, 'tournament_id');
    }

    public function matches()
    {
        return $this->hasMany(ChallongeMatch::class, 'tournament_id');
    }
} 