<?php

use Illuminate\Support\Facades\Route;
use Inertia\Inertia;
use App\Http\Controllers\ParticipantProfileController;
use App\Http\Controllers\DashboardController;

Route::get('/', function () {
    return Inertia::render('Welcome');
})->name('home');

Route::get('dashboard', [DashboardController::class, 'index'])
    ->middleware(['auth', 'verified'])
    ->name('dashboard');

Route::middleware(['auth'])->group(function () {
    Route::get('/profile/participant', [ParticipantProfileController::class, 'show'])->name('profile.participant');
    Route::get('/profile/participant/edit', [ParticipantProfileController::class, 'edit'])->name('profile.participant.edit');
    Route::put('/profile/participant', [ParticipantProfileController::class, 'update'])->name('profile.participant.update');
    Route::post('/profile/participant/{participant}/link', [ParticipantProfileController::class, 'link'])->name('profile.participant.link');
    Route::delete('/profile/participant/{participant}/unlink', [ParticipantProfileController::class, 'unlink'])->name('profile.participant.unlink');

    // Rotas de torneios
    Route::get('/tournaments', function () {
        return Inertia::render('Tournaments', [
            'tournaments' => [] // Aqui você deve passar os dados dos torneios
        ]);
    })->name('tournaments');

    // Rotas de participantes
    Route::get('/participants', function () {
        return Inertia::render('Participants', [
            'participants' => [] // Aqui você deve passar os dados dos participantes
        ]);
    })->name('participants');

    // Rota de head-to-head
    Route::get('/head-to-head', function () {
        return Inertia::render('HeadToHead', [
            'players' => [] // Aqui você deve passar os dados dos jogadores
        ]);
    })->name('head-to-head');
});

require __DIR__.'/settings.php';
require __DIR__.'/auth.php';
