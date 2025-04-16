<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PlayerStats extends Model
{
    use HasFactory;

    protected $fillable = [
        'player_id',
        'matches_played',
        'matches_won',
        'matches_lost',
        'sets_won',
        'sets_lost',
        'games_won',
        'games_lost',
        'aces',
        'double_faults',
        'first_serve_percentage',
        'first_serve_points_won',
        'second_serve_points_won',
        'break_points_saved',
        'break_points_faced',
        'season_year'
    ];

    protected $casts = [
        'matches_played' => 'integer',
        'matches_won' => 'integer',
        'matches_lost' => 'integer',
        'sets_won' => 'integer',
        'sets_lost' => 'integer',
        'games_won' => 'integer',
        'games_lost' => 'integer',
        'aces' => 'integer',
        'double_faults' => 'integer',
        'first_serve_percentage' => 'float',
        'first_serve_points_won' => 'float',
        'second_serve_points_won' => 'float',
        'break_points_saved' => 'integer',
        'break_points_faced' => 'integer',
        'season_year' => 'integer'
    ];

    public function player(): BelongsTo
    {
        return $this->belongsTo(Player::class);
    }

    public function getWinPercentage(): float
    {
        if ($this->matches_played === 0) return 0.0;
        return ($this->matches_won / $this->matches_played) * 100;
    }

    public function getBreakPointsSavedPercentage(): float
    {
        if ($this->break_points_faced === 0) return 0.0;
        return ($this->break_points_saved / $this->break_points_faced) * 100;
    }
} 