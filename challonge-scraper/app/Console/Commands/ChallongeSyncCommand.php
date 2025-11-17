<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use App\Models\ChallongeTournament;
use App\Models\ChallongeParticipant;
use App\Models\ChallongeMatch;
use Carbon\Carbon;

class ChallongeSyncCommand extends Command
{
    protected $signature = 'challonge:sync {--force : Força a sincronização mesmo para registros já sincronizados}';
    protected $description = 'Sincroniza dados do Challonge';

    private $apiKey;
    private $username;
    private $baseUrl = 'https://api.challonge.com/v1';

    public function __construct()
    {
        parent::__construct();
        $this->apiKey = config('services.challonge.api_key');
        $this->username = config('services.challonge.username');
    }

    public function handle()
    {
        $this->info('Iniciando sincronização com Challonge...');

        try {
            // Sincroniza torneios
            $this->syncTournaments();

            // Para cada torneio, sincroniza participantes e partidas
            $query = ChallongeTournament::query();
            if (!$this->option('force')) {
                $query->where('synced', false);
            }
            
            $totalTournaments = $query->count();
            $this->info("Total de torneios para sincronizar: {$totalTournaments}");

            foreach ($query->get() as $tournament) {
                try {
                    $this->syncParticipants($tournament);
                    $this->syncMatches($tournament);
                    
                    $tournament->update([
                        'synced' => true,
                        'last_sync_at' => now()
                    ]);
                    
                    $this->info("Torneio {$tournament->name} sincronizado com sucesso");
                } catch (\Exception $e) {
                    $this->error("Erro ao sincronizar torneio {$tournament->name}: " . $e->getMessage());
                    // Não atualiza o campo synced em caso de erro
                }
            }

            $this->info('Sincronização concluída com sucesso!');
        } catch (\Exception $e) {
            $this->error('Erro durante a sincronização: ' . $e->getMessage());
        }
    }

    private function syncTournaments()
    {
        $response = Http::withBasicAuth($this->username, $this->apiKey)
            ->get("{$this->baseUrl}/tournaments.json");

        if (!$response->successful()) {
            throw new \Exception("Falha ao obter torneios: " . $response->body());
        }

        foreach ($response->json() as $tournamentData) {
            $tournament = $tournamentData['tournament'];
            
            // Ignora torneios de duplas/dobles
            if (stripos($tournament['name'], 'DUPLAS') !== false || 
                stripos($tournament['name'], 'DOBLES') !== false ||
                stripos($tournament['name'], 'teste') !== false ||
                stripos($tournament['name'], 'DOUBLES') !== false ||
                stripos($tournament['name'], 'CLOSED') !== false) {
                $this->info("Ignorando torneio: {$tournament['name']}");
                continue;
            }
            
            $this->info("Sincronizando torneio: {$tournament['name']} (ID: {$tournament['id']})");
            
            $category = $this->determineCategory($tournament['name']);
            $startedAt = $this->adjustDateYear($tournament['started_at'], $tournament['name']);
            $completedAt = $this->adjustDateYear($tournament['completed_at'], $tournament['name']);
            
            $createdOrUpdated = ChallongeTournament::updateOrCreate(
                ['challonge_id' => $tournament['id']],
                [
                    'name' => $tournament['name'],
                    'category' => $category,
                    'url' => $tournament['url'],
                    'tournament_type' => $tournament['tournament_type'],
                    'state' => $tournament['state'],
                    'started_at' => $startedAt,
                    'completed_at' => $completedAt,
                    'open_signup' => $tournament['open_signup'],
                    'hold_third_place_match' => $tournament['hold_third_place_match'],
                    'participants_count' => $tournament['participants_count'],
                    'description' => $tournament['description'],
                    'raw_data' => $tournament
                ]
            );

            // Apenas torneios recém-criados devem começar como não sincronizados
            if ($createdOrUpdated->wasRecentlyCreated) {
                $createdOrUpdated->synced = false;
                $createdOrUpdated->last_sync_at = null;
                $createdOrUpdated->save();
            }
        }
    }

    private function adjustDateYear(?string $dateValue, string $name)
    {
        if (!$dateValue) {
            return null;
        }

        try {
            $date = Carbon::parse($dateValue);
        } catch (\Exception $e) {
            return $dateValue;
        }

        $yearFromName = $this->extractYearFromName($name);

        if ($yearFromName && $date->year !== $yearFromName) {
            $date = $date->setYear($yearFromName);
        }

        return $date;
    }

    private function extractYearFromName(string $name): ?int
    {
        if (preg_match('/\b(20\d{2})\b/', $name, $matches)) {
            return (int) $matches[1];
        }

        if (preg_match('/\b(\d{2})\b/', $name, $matches)) {
            $twoDigitYear = (int) $matches[1];

            if ($twoDigitYear >= 20) {
                return 2000 + $twoDigitYear;
            }
        }

        return null;
    }

    private function determineCategory(string $name): string
    {
        $name = strtoupper($name);
        
        // Procura por padrão Xa ou X a ou Xa CLASSE
        if (preg_match('/(\d)\s*A\s*(?:CLASSE)?/', $name, $matches)) {
            $categoryNumber = (int)$matches[1];
            return "{$categoryNumber}a CLASSE";
        }

        // Procura por padrão FINALS seguido de A, B ou C
        if (preg_match('/FINALS.*?([ABC])\b/', $name, $matches)) {
            $categoryLetter = $matches[1];
            switch ($categoryLetter) {
                case 'A': return '3a CLASSE';
                case 'B': return '4a CLASSE';
                case 'C': return '5a CLASSE';
            }
        }

        // Procura por padrão X/a
        if (preg_match('/(\d)\/A/', $name, $matches)) {
            $categoryNumber = (int)$matches[1];
            return "{$categoryNumber}a CLASSE";
        }

        // Procura por padrão XcatA
        if (preg_match('/(\d)CAT([ABC])/', $name, $matches)) {
            $categoryLetter = $matches[2];
            switch ($categoryLetter) {
                case 'A': return '3a CLASSE';
                case 'B': return '4a CLASSE';
                case 'C': return '5a CLASSE';
            }
        }

        // Procura por padrão X/Ya
        if (preg_match('/\d+\/(\d)A/', $name, $matches)) {
            $categoryNumber = (int)$matches[1];
            return "{$categoryNumber}a CLASSE";
        }
        
        return '3a CLASSE'; // Categoria padrão caso não encontre nenhuma correspondência
    }

    private function syncParticipants($tournament)
    {
        $response = Http::withBasicAuth($this->username, $this->apiKey)
            ->get("{$this->baseUrl}/tournaments/{$tournament->challonge_id}/participants.json");

        if (!$response->successful()) {
            throw new \Exception("Falha ao obter participantes do torneio {$tournament->id}: " . $response->body());
        }

        foreach ($response->json() as $participantData) {
            $participant = $participantData['participant'];

            // Ignora participantes que são duplas (contêm "/" no nome)
            if (strpos($participant['name'], '/') !== false) {
                $this->info("Ignorando dupla: {$participant['name']}");
                continue;
            }

            echo "Sincronizando participante: " . $participant['name'] . PHP_EOL;
            ChallongeParticipant::updateOrCreate(
                [
                    'challonge_id' => $participant['id']
                ],
                [
                    'tournament_id' => $tournament->id,
                    'name' => $participant['name'],
                    'seed' => $participant['seed'] ?? null,
                    'display_name' => $participant['display_name'] ?? null,
                    'username' => $participant['username'] ?? null,
                    'email' => $participant['email'] ?? null,
                    'checked_in' => $participant['checked_in'] ?? false,
                    'checked_in_at' => $participant['checked_in_at'] ?? null,
                    'active' => $participant['active'] ?? true,
                    'final_rank' => $participant['final_rank'] ?? null,
                    'raw_data' => $participant,
                    'synced' => true,
                    'last_sync_at' => now()
                ]
            );
        }
    }

    private function syncMatches($tournament)
    {
        $response = Http::withBasicAuth($this->username, $this->apiKey)
            ->get("{$this->baseUrl}/tournaments/{$tournament->challonge_id}/matches.json");

        if (!$response->successful()) {
            throw new \Exception("Falha ao obter partidas do torneio {$tournament->id}: " . $response->body());
        }

        foreach ($response->json() as $matchData) {
            $match = $matchData['match'];
            
            // Busca IDs dos participantes locais
            $player1 = ChallongeParticipant::where('challonge_id', $match['player1_id'])->first();
            $player2 = ChallongeParticipant::where('challonge_id', $match['player2_id'])->first();

            ChallongeMatch::updateOrCreate(
                [
                    'tournament_id' => $tournament->id,
                    'challonge_id' => $match['id']
                ],
                [
                    'player1_id' => $player1?->id,
                    'player2_id' => $player2?->id,
                    'round' => $match['round'],
                    'state' => $match['state'] ?? 'pending',
                    'winner_id' => $match['winner_id'] ?? null,
                    'loser_id' => $match['loser_id'] ?? null,
                    'score' => $match['score'] ?? null,
                    'started_at' => $match['started_at'] ?? null,
                    'completed_at' => $match['completed_at'] ?? null,
                    'underway' => $match['underway'] ?? false,
                    'underway_at' => $match['underway_at'] ?? null,
                    'scores_csv' => $match['scores_csv'] ?? null,
                    'raw_data' => $match,
                    'synced' => true,
                    'last_sync_at' => now()
                ]
            );
        }
    }
} 