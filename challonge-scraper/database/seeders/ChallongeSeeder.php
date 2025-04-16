<?php

namespace Database\Seeders;

use App\Models\ChallongeTournament;
use App\Models\ChallongeParticipant;
use App\Models\ChallongeMatch;
use App\Models\User;
use App\Models\Player;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class ChallongeSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        // Criar usuário de teste
        $user = User::create([
            'name' => 'Usuário Teste',
            'email' => 'teste@example.com',
            'password' => Hash::make('password'),
        ]);

        // Criar jogador
        $player = Player::create([
            'name' => 'Usuário Teste',
            'nickname' => 'Teste',
            'birth_date' => '1990-01-01',
            'nationality' => 'Brasileiro',
            'dominant_hand' => 'right',
            'height' => 1.80,
            'weight' => 75,
            'points' => 1000,
            'user_id' => $user->id
        ]);

        // Criar torneios
        $tournaments = [];
        for ($i = 1; $i <= 3; $i++) {
            $tournaments[] = ChallongeTournament::create([
                'challonge_id' => $i,
                'name' => "Torneio $i",
                'url' => "torneio-$i",
                'tournament_type' => 'single elimination',
                'state' => 'pending',
                'started_at' => now()->addDays($i * 7),
                'participants_count' => 8,
                'description' => "Descrição do Torneio $i"
            ]);
        }

        // Criar participantes
        $challongeIdCounter = 1;
        foreach ($tournaments as $tournament) {
            // Participante do usuário de teste
            $participant = ChallongeParticipant::create([
                'tournament_id' => $tournament->id,
                'challonge_id' => $challongeIdCounter++,
                'name' => $user->name,
                'seed' => 1,
                'user_id' => $user->id,
                'player_id' => $player->id
            ]);

            // Outros participantes
            for ($i = 2; $i <= 8; $i++) {
                ChallongeParticipant::create([
                    'tournament_id' => $tournament->id,
                    'challonge_id' => $challongeIdCounter++,
                    'name' => "Participante $i",
                    'seed' => $i
                ]);
            }

            // Criar partidas
            ChallongeMatch::create([
                'tournament_id' => $tournament->id,
                'challonge_id' => $challongeIdCounter++,
                'player1_id' => $participant->id,
                'player2_id' => ChallongeParticipant::where('tournament_id', $tournament->id)
                    ->where('id', '!=', $participant->id)
                    ->inRandomOrder()
                    ->first()
                    ->id,
                'round' => 1,
                'state' => 'pending',
                'started_at' => $tournament->started_at
            ]);
        }

        // Criar algumas partidas já jogadas
        $oldTournament = ChallongeTournament::create([
            'challonge_id' => 99,
            'name' => 'Torneio Anterior',
            'url' => 'torneio-anterior',
            'tournament_type' => 'single elimination',
            'state' => 'complete',
            'started_at' => now()->subDays(7),
            'completed_at' => now()->subDays(1),
            'participants_count' => 8,
            'description' => 'Torneio já finalizado'
        ]);

        $oldParticipant = ChallongeParticipant::create([
            'tournament_id' => $oldTournament->id,
            'challonge_id' => $challongeIdCounter++,
            'name' => $user->name,
            'seed' => 1,
            'user_id' => $user->id,
            'player_id' => $player->id
        ]);

        // Partida vencida
        $opponent1 = ChallongeParticipant::create([
            'tournament_id' => $oldTournament->id,
            'challonge_id' => $challongeIdCounter++,
            'name' => 'Oponente 1',
            'seed' => 2
        ]);

        ChallongeMatch::create([
            'tournament_id' => $oldTournament->id,
            'challonge_id' => $challongeIdCounter++,
            'player1_id' => $oldParticipant->id,
            'player2_id' => $opponent1->id,
            'round' => 1,
            'state' => 'complete',
            'winner_id' => $oldParticipant->id,
            'started_at' => now()->subDays(7),
            'completed_at' => now()->subDays(7)
        ]);

        // Partida perdida
        $opponent2 = ChallongeParticipant::create([
            'tournament_id' => $oldTournament->id,
            'challonge_id' => $challongeIdCounter++,
            'name' => 'Oponente 2',
            'seed' => 3
        ]);

        ChallongeMatch::create([
            'tournament_id' => $oldTournament->id,
            'challonge_id' => $challongeIdCounter++,
            'player1_id' => $oldParticipant->id,
            'player2_id' => $opponent2->id,
            'round' => 2,
            'state' => 'complete',
            'winner_id' => $opponent2->id,
            'started_at' => now()->subDays(6),
            'completed_at' => now()->subDays(6)
        ]);
    }
}
