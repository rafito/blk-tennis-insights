<?php

namespace App\Providers;
use Illuminate\Support\Facades\DB;

use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        if (config('database.default') === 'sqlite') {
            // Habilita WAL: melhora leitura concorrente
            DB::statement('PRAGMA journal_mode = WAL;');
            // Evita fsync pesado (bom com WAL)
            DB::statement('PRAGMA synchronous = NORMAL;');
            // Dá tempo pra liberar o lock
            DB::statement('PRAGMA busy_timeout = 5000;'); // 5s
            // (Opcional) reduz tamanho das páginas em FS lentos
            // DB::statement('PRAGMA cache_size = -2000;'); // ~2MB
            // Garante FKs
            DB::statement('PRAGMA foreign_keys = ON;');
        }
    }
}
