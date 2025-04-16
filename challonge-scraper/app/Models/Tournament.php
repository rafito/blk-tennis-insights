<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Tournament extends Model
{
    use HasFactory;

    protected $fillable = [
        'name',
        'start_date',
        'end_date',
        'participants_count',
        'image_url',
        'status'
    ];

    protected $casts = [
        'start_date' => 'datetime',
        'end_date' => 'datetime'
    ];

    public function matches()
    {
        return $this->hasMany(Match::class);
    }

    public function participants()
    {
        return $this->belongsToMany(Player::class, 'tournament_participants');
    }
} 