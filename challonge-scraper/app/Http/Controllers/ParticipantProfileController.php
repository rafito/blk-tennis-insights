<?php

namespace App\Http\Controllers;

use App\Models\ChallongeParticipant;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Validation\Rule;
use Inertia\Inertia;

class ParticipantProfileController extends Controller
{
    public function show()
    {
        $participant = Auth::user()->participants()->latest()->first();
        return Inertia::render('Profile/Participant', [
            'participant' => $participant
        ]);
    }

    public function edit()
    {
        $participant = Auth::user()->participants()->latest()->first();
        
        if (!$participant) {
            return redirect()->route('profile.participant')
                ->with('error', 'Você ainda não está vinculado a nenhum torneio como participante.');
        }

        return Inertia::render('Profile/ParticipantEdit', [
            'participant' => $participant
        ]);
    }

    public function update(Request $request)
    {
        $participant = Auth::user()->participants()->latest()->first();

        if (!$participant) {
            return redirect()->route('profile.participant')
                ->with('error', 'Você ainda não está vinculado a nenhum torneio como participante.');
        }

        $validated = $request->validate([
            'name' => ['required', 'string', 'max:255'],
            'display_name' => ['nullable', 'string', 'max:255'],
            'username' => ['nullable', 'string', 'max:255'],
            'email' => [
                'required',
                'email',
                Rule::unique('challonge_participants')->ignore($participant->id)
            ],
        ]);

        $participant->update($validated);

        return redirect()->route('profile.participant')
            ->with('success', 'Perfil de participante atualizado com sucesso!');
    }

    public function link(ChallongeParticipant $participant)
    {
        if ($participant->user_id) {
            return back()->with('error', 'Este participante já está vinculado a outro usuário.');
        }

        $participant->update(['user_id' => Auth::id()]);

        return back()->with('success', 'Participante vinculado com sucesso ao seu perfil!');
    }

    public function unlink(ChallongeParticipant $participant)
    {
        if ($participant->user_id !== Auth::id()) {
            return back()->with('error', 'Você não tem permissão para desvincular este participante.');
        }

        $participant->update(['user_id' => null]);

        return back()->with('success', 'Participante desvinculado com sucesso do seu perfil!');
    }
} 