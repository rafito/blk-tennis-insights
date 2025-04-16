<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\BelongsToMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Player extends Model
{
    use HasFactory;

    protected $fillable = [
        'name',
        'nickname',
        'birth_date',
        'nationality',
        'dominant_hand',
        'height',
        'weight',
        'profile_image',
        'ranking_position',
        'points',
        'email',
        'username',
        'user_id'
    ];

    protected $casts = [
        'birth_date' => 'date',
        'height' => 'float',
        'weight' => 'float',
        'ranking_position' => 'integer',
        'points' => 'integer'
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function challongeParticipations(): HasMany
    {
        return $this->hasMany(ChallongeParticipant::class);
    }

    public function currentStats(): HasOne
    {
        return $this->hasOne(PlayerStats::class)
            ->where('season_year', date('Y'))
            ->withDefault();
    }

    public function stats(): HasMany
    {
        return $this->hasMany(PlayerStats::class);
    }

    public function homeMatches(): HasMany
    {
        return $this->hasMany(ChallongeMatch::class, 'player1_id');
    }

    public function awayMatches(): HasMany
    {
        return $this->hasMany(ChallongeMatch::class, 'player2_id');
    }

    public function tournaments(): BelongsToMany
    {
        return $this->belongsToMany(ChallongeTournament::class, 'tournament_players');
    }

    public function getAllMatches()
    {
        return $this->homeMatches->merge($this->awayMatches)->sortByDesc('played_at');
    }

    public function getWinRate()
    {
        $totalMatches = $this->homeMatches->count() + $this->awayMatches->count();
        if ($totalMatches === 0) return 0;

        $wins = $this->homeMatches->where('winner_id', $this->id)->count() +
                $this->awayMatches->where('winner_id', $this->id)->count();

        return ($wins / $totalMatches) * 100;
    }
} 