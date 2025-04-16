<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Models\ChallongeParticipant;
use App\Models\ChallongeMatch;
use Illuminate\Support\Str;

class ChallongeMergeParticipantsCommand extends Command
{
    protected $signature = 'challonge:merge-participants 
        {--similarity=80 : Porcentagem mínima de similaridade para considerar duplicatas}
        {--max-group-size=0 : Número máximo de participantes similares em um grupo (0 = sem limite)}';
    protected $description = 'Mescla participantes duplicados baseado na similaridade dos nomes';
    protected $cacheFile = 'storage/app/merge_decisions.json';

    private function loadMergeDecisions()
    {
        if (file_exists($this->cacheFile)) {
            return json_decode(file_get_contents($this->cacheFile), true) ?? [];
        }
        return [];
    }

    private function saveMergeDecision($participantIds, $decision)
    {
        $decisions = $this->loadMergeDecisions();
        sort($participantIds);
        $key = implode('-', $participantIds);
        $decisions[$key] = $decision;
        file_put_contents($this->cacheFile, json_encode($decisions));
    }

    private function shouldMergeParticipants($participantIds)
    {
        $decisions = $this->loadMergeDecisions();
        sort($participantIds);
        $key = implode('-', $participantIds);
        return $decisions[$key] ?? null;
    }

    private function normalizeNameForComparison(string $str): string
    {
        // Remove espaços extras e pontos
        $str = preg_replace('/\s+/', ' ', $str); // Converte múltiplos espaços em um
        $str = str_replace(['. ', '.'], ' ', $str); // Converte pontos em espaços
        $str = trim($str); // Remove espaços das extremidades
        return Str::lower($str); // Converte para minúsculas
    }

    private function areNamesEffectivelyIdentical(string $str1, string $str2): bool
    {
        $norm1 = $this->normalizeNameForComparison($str1);
        $norm2 = $this->normalizeNameForComparison($str2);
        
        // Remove todos os espaços para comparação direta
        $withoutSpaces1 = str_replace(' ', '', $norm1);
        $withoutSpaces2 = str_replace(' ', '', $norm2);
        
        return $withoutSpaces1 === $withoutSpaces2;
    }

    private function calculateSimilarity(string $str1, string $str2): float
    {
        // Verifica se os nomes são efetivamente idênticos após normalização
        if ($this->areNamesEffectivelyIdentical($str1, $str2)) {
            return 100;
        }

        // Normaliza as strings para comparação
        $str1 = $this->normalizeNameForComparison($str1);
        $str2 = $this->normalizeNameForComparison($str2);

        // Se as strings são idênticas após normalização básica
        if ($str1 === $str2) {
            return 100;
        }

        // Penaliza se a primeira letra for diferente
        $firstChar1 = mb_substr($str1, 0, 1);
        $firstChar2 = mb_substr($str2, 0, 1);
        
        // Calcula a distância de Levenshtein
        $levenshtein = levenshtein($str1, $str2);
        $maxLength = max(strlen($str1), strlen($str2));
        
        // Calcula a similaridade base
        $similarity = (1 - ($levenshtein / $maxLength)) * 100;

        // Reduz a similaridade se a primeira letra for diferente
        if ($firstChar1 !== $firstChar2) {
            $similarity *= 0.7; // Reduz em 30% a similaridade
        }

        return $similarity;
    }

    public function handle()
    {
        $this->info('Iniciando processo de mesclagem de participantes...');
        $similarityThreshold = $this->option('similarity');
        $maxGroupSize = (int)$this->option('max-group-size');

        // Busca todos os participantes
        $participants = ChallongeParticipant::all();
        $merged = 0;

        // Array para armazenar grupos de participantes similares
        $similarGroups = [];

        // Compara cada participante com todos os outros
        foreach ($participants as $p1) {
            $found = false;
            foreach ($similarGroups as &$group) {
                // Se o grupo já atingiu o tamanho máximo, pula
                if ($maxGroupSize > 0 && count($group) >= $maxGroupSize) {
                    continue;
                }

                // Verifica se o participante atual é similar a qualquer um do grupo
                foreach ($group as $p) {
                    if ($this->calculateSimilarity($p1->name, $p->name) >= $similarityThreshold) {
                        // Se o grupo já atingiu o tamanho máximo, não adiciona
                        if ($maxGroupSize > 0 && count($group) >= $maxGroupSize) {
                            break;
                        }
                        $group[] = $p1;
                        $found = true;
                        break 2;
                    }
                }
            }
            
            // Se não encontrou grupo similar, cria um novo
            if (!$found) {
                $similarGroups[] = [$p1];
            }
        }

        // Processa cada grupo de participantes similares
        foreach ($similarGroups as $group) {
            if (count($group) > 1) {
                $this->info("\nEncontrado grupo de participantes similares (" . count($group) . " participantes):");
                foreach ($group as $p) {
                    $this->info("- {$p->name} (ID: {$p->id})");
                }

                $participantIds = array_map(function($p) { return $p->id; }, $group);
                $shouldMerge = $this->shouldMergeParticipants($participantIds);

                // Verifica se os nomes são efetivamente idênticos
                $allAreIdentical = true;
                $firstParticipant = $group[0];
                foreach ($group as $p) {
                    if (!$this->areNamesEffectivelyIdentical($firstParticipant->name, $p->name)) {
                        $allAreIdentical = false;
                        break;
                    }
                }

                if ($allAreIdentical) {
                    $shouldMerge = true;
                    $this->info("Nomes efetivamente idênticos - mesclagem automática.");
                } elseif ($shouldMerge === null) {
                    $shouldMerge = $this->confirm('Deseja mesclar estes participantes?');
                    $this->saveMergeDecision($participantIds, $shouldMerge);
                } else {
                    $this->info($shouldMerge ? "Usando decisão anterior: mesclar" : "Usando decisão anterior: não mesclar");
                }

                if ($shouldMerge) {
                    // Usa o primeiro participante como principal
                    $mainParticipant = $group[0];
                    
                    foreach ($group as $index => $participant) {
                        if ($index === 0) continue; // Pula o participante principal

                        // Atualiza as referências nas partidas
                        ChallongeMatch::where('player1_id', $participant->id)
                            ->update(['player1_id' => $mainParticipant->id]);
                        
                        ChallongeMatch::where('player2_id', $participant->id)
                            ->update(['player2_id' => $mainParticipant->id]);

                        // Atualiza os IDs de vencedor e perdedor
                        ChallongeMatch::where('winner_id', $participant->id)
                            ->update(['winner_id' => $mainParticipant->id]);
                        
                        ChallongeMatch::where('loser_id', $participant->id)
                            ->update(['loser_id' => $mainParticipant->id]);

                        // Deleta o participante duplicado
                        $participant->delete();
                        $merged++;
                    }

                    $this->info("Participantes mesclados com sucesso em: {$mainParticipant->name}");
                }
            }
        }

        $this->info("\nProcesso concluído! {$merged} participantes foram mesclados.");
    }
} 