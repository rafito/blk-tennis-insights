<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Artisan;

class SyncAllChallongeDataCommand extends Command
{
    protected $signature = 'challonge:sync-all {--reset-db : Reseta o banco de dados antes da sincronização}';
    protected $description = 'Executa todos os comandos de sincronização do Challonge em sequência';

    public function handle()
    {
        $this->info('Iniciando sincronização completa do Challonge...');

        if ($this->option('reset-db')) {
            $this->info('Resetando o banco de dados...');
            
            // Executa as migrações para garantir que as tabelas existam
            $this->info('Executando migrações...');
            Artisan::call('migrate:fresh');
            $this->info('Migrações concluídas com sucesso.');
        }

        // Executa challonge-sync
        $this->info('Executando challonge-sync...');
        $this->call('challonge:sync');
        $this->info('challonge-sync concluído.');

        // Executa challonge:update-match-ids
        $this->info('Executando challonge:update-match-ids...');
        $this->call('challonge:update-match-ids');
        $this->info('challonge:update-match-ids concluído.');

        // Executa challonge:merge-participants
        $this->info('Executando challonge:merge-participants...');
        $this->call('challonge:merge-participants');
        $this->info('challonge:merge-participants concluído.');

        $this->info('Sincronização completa concluída com sucesso!');
    }
} 