<?php

namespace App\Http\Controllers;

use App\Models\ChallongeTournament;
use App\Models\ChallongeMatch;
use App\Models\Player;
use Illuminate\Http\Request;
use Inertia\Inertia;

class DashboardController extends Controller
{
    public function index()
    {
        $participant = auth()->user()->participants()->first();
        
        if (!$participant) {
            return Inertia::render('Dashboard', [
                'playerStats' => [
                    'wins' => 0,
                    'losses' => 0,
                    'ranking' => 0,
                    'points' => 0
                ],
                'tournaments' => [],
                'upcomingMatches' => []
            ]);
        }

        $player = $participant->player;
        
        // Estatísticas do jogador
        $playerStats = [
            'wins' => ChallongeMatch::where('winner_id', $participant->id)->count(),
            'losses' => ChallongeMatch::where(function($query) use ($participant) {
                $query->where('player1_id', $participant->id)
                    ->orWhere('player2_id', $participant->id);
            })->where('winner_id', '!=', $participant->id)->count(),
            'ranking' => $player ? Player::where('points', '>', $player->points)->count() + 1 : 0,
            'points' => $player ? $player->points : 0
        ];

        // Próximos torneios
        $tournaments = ChallongeTournament::where('state', 'pending')
            ->orderBy('started_at')
            ->take(3)
            ->get()
            ->map(function ($tournament) {
                return [
                    'name' => $tournament->name,
                    'startDate' => $tournament->started_at ? $tournament->started_at->format('d/m/Y') : 'A definir',
                    'status' => 'upcoming',
                    'participants' => $tournament->participants_count,
                    'imageUrl' => null
                ];
            });

        // Próximas partidas
        $upcomingMatches = ChallongeMatch::with(['player1', 'player2', 'tournament'])
            ->where(function($query) use ($participant) {
                $query->where('player1_id', $participant->id)
                    ->orWhere('player2_id', $participant->id);
            })
            ->where('state', 'pending')
            ->orderBy('started_at')
            ->take(2)
            ->get()
            ->map(function ($match) {
                return [
                    'id' => $match->id,
                    'player1' => [
                        'name' => $match->player1->name,
                        'imageUrl' => null
                    ],
                    'player2' => [
                        'name' => $match->player2->name,
                        'imageUrl' => null
                    ],
                    'datetime' => $match->started_at ? $match->started_at->format('d/m/Y H:i') : 'A definir',
                    'court' => 'A definir',
                    'tournament' => $match->tournament->name
                ];
            });

        return Inertia::render('Dashboard', [
            'playerStats' => $playerStats,
            'tournaments' => $tournaments,
            'upcomingMatches' => $upcomingMatches
        ]);
    }
} 