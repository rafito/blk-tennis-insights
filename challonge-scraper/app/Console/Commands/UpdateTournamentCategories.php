<?php

namespace App\Console\Commands;

use App\Models\ChallongeTournament;
use Illuminate\Console\Command;

class UpdateTournamentCategories extends Command
{
    protected $signature = 'tournaments:update-categories';
    protected $description = 'Atualiza as categorias dos torneios com base no nome';

    public function handle()
    {
        $this->info('Iniciando atualização das categorias dos torneios...');

        $tournaments = ChallongeTournament::all();
        $updated = 0;

        foreach ($tournaments as $tournament) {
            $category = $this->determineCategory($tournament->name);
            $tournament->category = $category;
            $tournament->save();
            $updated++;
            
            $this->info("Torneio '{$tournament->name}' atualizado para categoria: {$category}");
        }

        $this->info("Processo concluído. {$updated} torneios atualizados.");
    }

    private function determineCategory(string $name): string
    {
        $name = strtoupper($name);
        
        // Padrão para torneios com formato XCatY
        if (preg_match('/\dCAT([ABC])/', $name, $matches)) {
            $categoryLetter = $matches[1];
            switch ($categoryLetter) {
                case 'A': return '3a CLASSE';
                case 'B': return '4a CLASSE';
                case 'C': return '5a CLASSE';
            }
        }

        // Padrão para torneios com formato Xa ou Xa CLASSE
        if (preg_match('/(\d)A\s*(?:CLASSE)?/', $name, $matches)) {
            $categoryNumber = (int)$matches[1];
            switch ($categoryNumber) {
                case 3: return '3a CLASSE';
                case 4: return '4a CLASSE';
                case 5: return '5a CLASSE';
            }
        }

        // Padrão para torneios FINALS com letras A, B, C
        if (preg_match('/FINALS.*?([ABC])/', $name, $matches)) {
            $categoryLetter = $matches[1];
            switch ($categoryLetter) {
                case 'A': return '3a CLASSE';
                case 'B': return '4a CLASSE';
                case 'C': return '5a CLASSE';
            }
        }

        // Padrão específico para DOBLES com número
        if (preg_match('/DOBLES.*?(\d)A/', $name, $matches)) {
            $categoryNumber = (int)$matches[1];
            switch ($categoryNumber) {
                case 3: return '3a CLASSE';
                case 4: return '4a CLASSE';
                case 5: return '5a CLASSE';
            }
        }
        
        return '3a CLASSE'; // Categoria padrão caso não encontre nenhuma correspondência
    }
} 