<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ChallongeParticipant extends Model
{
    protected $fillable = [
        'tournament_id',
        'challonge_id',
        'name',
        'seed',
        'display_name',
        'username',
        'email',
        'checked_in',
        'checked_in_at',
        'active',
        'final_rank',
        'raw_data',
        'synced',
        'last_sync_at',
        'user_id',
        'player_id'
    ];

    protected $casts = [
        'checked_in' => 'boolean',
        'active' => 'boolean',
        'synced' => 'boolean',
        'raw_data' => 'array',
        'checked_in_at' => 'datetime',
        'last_sync_at' => 'datetime'
    ];

    public function tournament(): BelongsTo
    {
        return $this->belongsTo(ChallongeTournament::class, 'tournament_id');
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function player(): BelongsTo
    {
        return $this->belongsTo(Player::class);
    }

    public function matchesAsPlayer1()
    {
        return $this->hasMany(ChallongeMatch::class, 'player1_id');
    }

    public function matchesAsPlayer2()
    {
        return $this->hasMany(ChallongeMatch::class, 'player2_id');
    }
} 