<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\ChallongeMatch;
use App\Models\ChallongeParticipant;

class ChallongeUpdateMatchIdsCommand extends Command
{
    protected $signature = 'challonge:update-match-ids';
    protected $description = 'Atualiza os IDs de vencedor e perdedor nas partidas do Challonge para usar participant_id';

    public function handle()
    {
        $this->info('Iniciando atualização dos IDs nas partidas...');

        $matches = ChallongeMatch::whereNotNull('winner_id')
            ->orWhereNotNull('loser_id')
            ->get();

        $updated = 0;
        $skipped = 0;

        foreach ($matches as $match) {
            if ($match->winner_id) {
                $participant = ChallongeParticipant::where('challonge_id', $match->winner_id)->first();
                if ($participant) {
                    $match->winner_id = $participant->id;
                    $updated++;
                } else {
                    $this->warn("Participante vencedor não encontrado para ID {$match->winner_id}");
                    $skipped++;
                }
            }

            if ($match->loser_id) {
                $participant = ChallongeParticipant::where('challonge_id', $match->loser_id)->first();
                if ($participant) {
                    $match->loser_id = $participant->id;
                    $updated++;
                } else {
                    $this->warn("Participante perdedor não encontrado para ID {$match->loser_id}");
                    $skipped++;
                }
            }

            $match->save();
        }

        $this->info("Atualização concluída!");
        $this->info("Total de IDs atualizados: {$updated}");
        $this->info("Total de IDs ignorados: {$skipped}");
    }
} 