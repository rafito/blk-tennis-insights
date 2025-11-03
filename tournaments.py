import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sqlite3

def get_tournament_champion(matches, tournament_id):
    """Identifica o campeão do torneio baseado na rodada mais alta"""
    tournament_matches = matches[matches['tournament_id'] == tournament_id]
    if tournament_matches.empty:
        return None
    
    # O campeão é o vencedor da rodada mais alta
    max_round = tournament_matches['round'].max()
    final_match = tournament_matches[tournament_matches['round'] == max_round]
    
    if not final_match.empty:
        champion_id = final_match.iloc[0]['winner_id']
        champion_name = final_match.iloc[0]['winner_name']
        return {'id': champion_id, 'name': champion_name}
    
    return None

# Removido: função get_participant_seeds (informação de seeds não confiável)

def create_tournament_bracket(matches, tournament_id, tournament_name):
    """Cria a visualização da chave do torneio em ASCII"""
    tournament_matches = matches[matches['tournament_id'] == tournament_id].copy()
    
    if tournament_matches.empty:
        st.warning(f"Nenhuma partida encontrada para o torneio {tournament_name}")
        return
    
    # Removido: busca de seeds (informação não confiável)
    
    # Organizar partidas por rodada
    rounds = sorted(tournament_matches['round'].unique())
    
    # Identificar o campeão
    champion = get_tournament_champion(matches, tournament_id)
    
    st.markdown(f"## 🏆 {tournament_name}")
    
    if champion:
        st.success(f"🥇 **CAMPEÃO: {champion['name']}**")
    
    # Determinar nomes das rodadas
    max_round = max(rounds)
    round_names = {}
    
    if max_round == 4:
        round_names = {1: "1ª Rodada", 2: "Quartas", 3: "Semifinal", 4: "Final"}
    elif max_round == 3:
        round_names = {1: "Quartas", 2: "Semifinal", 3: "Final"}
    elif max_round == 2:
        round_names = {1: "Semifinal", 2: "Final"}
    elif max_round == 1:
        round_names = {1: "Final"}
    else:
        for r in rounds:
            round_names[r] = f"Rodada {r}"
    
    # Obter host da session_state para criar links
    host = st.session_state.get('host', 'http://localhost:8502')
    
    # Organizar dados para ASCII art
    rounds_data = {}
    for round_num in rounds:
        round_matches = tournament_matches[tournament_matches['round'] == round_num].sort_values('match_id')
        rounds_data[round_num] = []
        
        for _, match in round_matches.iterrows():
            winner_name = match['winner_name']
            loser_name = match['loser_name']
            score = match['score'] if pd.notna(match['score']) else "A definir"
            
            # Removido: busca de seeds (informação não confiável)
            
            # Formattar nomes em CAPS LOCK (sem seed)
            winner_display = winner_name.upper()
            loser_display = loser_name.upper()
            
            # Truncar nomes se muito longos
            if len(winner_display) > 18:
                winner_display = winner_display[:15] + "..."
            if len(loser_display) > 18:
                loser_display = loser_display[:15] + "..."
            
            rounds_data[round_num].append({
                'winner': winner_display,
                'loser': loser_display,
                'score': score,
                'winner_id': match['winner_id'],
                'loser_id': match['loser_id'],
                'is_champion': round_num == max_round and champion and champion['name'] == winner_name
            })
    
    # Criar ASCII art da chave simplificada
    bracket_lines = []
    
    # Cabeçalho com nomes das rodadas
    header_parts = []
    for round_num in rounds:
        round_name = round_names.get(round_num, f"Rodada {round_num}")
        header_parts.append(f"{round_name:^22}")
    
    header = "".join(header_parts)
    bracket_lines.append(header)
    bracket_lines.append("=" * len(header))
    bracket_lines.append("")
    
    # Mostrar apenas as partidas únicas de cada rodada
    max_lines_per_round = max(len(rounds_data[r]) for r in rounds)
    
    for match_idx in range(max_lines_per_round):
        line_parts = []
        
        for round_idx, round_num in enumerate(rounds):
            if match_idx < len(rounds_data[round_num]):
                match_data = rounds_data[round_num][match_idx]
                
                winner = match_data['winner']
                loser = match_data['loser']
                score = match_data['score']
                
                if match_data['is_champion']:
                    winner = f"👑 {winner}"
                
                # Formattar a partida em blocos sem flechas
                match_text = f"✅ {winner:<18}\n   {loser:<18}"
                
                line_parts.append(match_text)
            else:
                # Espaço vazio
                empty_text = "\n".join([" " * 20] * 2)
                line_parts.append(empty_text)
        
        # Combinar as partes da linha
        combined_lines = [""] * 2
        for part in line_parts:
            part_lines = part.split('\n')
            for i in range(2):
                combined_lines[i] += part_lines[i] + "  "
        
        # Adicionar as linhas combinadas
        bracket_lines.extend(combined_lines)
        bracket_lines.append("")  # Espaçamento entre partidas
    
    # Remover linha vazia extra no final
    if bracket_lines and bracket_lines[-1] == "":
        bracket_lines.pop()
    
    # Exibir a chave ASCII com fonte pequena preservando identação
    bracket_text = "\n".join(bracket_lines)
    
    # Converter quebras de linha para HTML, preservar espaços e escapar caracteres especiais
    bracket_html = bracket_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    bracket_html = bracket_html.replace(' ', '&nbsp;').replace('\n', '<br>')
    
    # Aplicar CSS e exibir
    st.markdown(f"""
    <div style="
        font-family: 'Courier New', monospace;
        font-size: 10px;
        line-height: 1.2;
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 6px;
        border: 1px solid #e9ecef;
        overflow-x: auto;
        white-space: pre-line;
        color: #212529;
    ">
    {bracket_html}
    </div>
    """, unsafe_allow_html=True)

    
    # Mostrar resumo das partidas com cores
    st.markdown("### 📊 Resumo das Partidas")
    
    for round_num in rounds:
        round_name = round_names.get(round_num, f"Rodada {round_num}")
        st.markdown(f"**{round_name}:**")
        
        round_matches = rounds_data[round_num]
        for match_data in round_matches:
            winner = match_data['winner']
            loser = match_data['loser']
            
            if match_data['is_champion']:
                winner = f"👑 {winner}"
            
            # Usar success/error para cores
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"🏆 {winner}")
            with col2:
                st.error(f"❌ {loser}")
        
        st.divider()


def create_bracket_visualization(matches, tournament_id):
    """Cria uma visualização gráfica da chave usando Plotly"""
    tournament_matches = matches[matches['tournament_id'] == tournament_id].copy()
    
    if tournament_matches.empty:
        return None
    
    # Organizar dados para o gráfico
    rounds = sorted(tournament_matches['round'].unique())
    
    # Criar figura
    fig = go.Figure()
    
    # Posições para cada rodada
    round_positions = {}
    for i, round_num in enumerate(rounds):
        round_positions[round_num] = i * 2
    
    # Adicionar nós para cada partida
    for _, match in tournament_matches.iterrows():
        round_num = match['round']
        x_pos = round_positions[round_num]
        
        # Posição Y baseada no ID da partida para espaçamento
        y_pos = match['match_id'] % 10
        
        # Adicionar nó do vencedor
        fig.add_trace(go.Scatter(
            x=[x_pos],
            y=[y_pos],
            mode='markers+text',
            marker=dict(size=15, color='green'),
            text=match['winner_name'],
            textposition="middle right",
            name=f"Vencedor R{round_num}",
            showlegend=False
        ))
    
    # Configurar layout
    fig.update_layout(
        title="Chave do Torneio",
        xaxis_title="Rodadas",
        yaxis_title="Partidas",
        height=600,
        showlegend=False
    )
    
    return fig

def display_tournaments_page(matches, players, tournaments):
    """Exibe a página de torneios"""
    st.header("🎾 Torneios")
    
    # Garantir que o host esteja disponível na session_state
    if 'host' not in st.session_state:
        st.session_state['host'] = 'http://localhost:8502'
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Filtro por categoria
        categories = ["Todas"] + sorted(tournaments['category'].dropna().unique().tolist())
        selected_category = st.selectbox(
            "📂 Categoria:",
            categories,
            index=0
        )
    
    with col2:
        # Filtro por ano
        years = ["Todos"] + sorted(tournaments['started_year'].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox(
            "📅 Ano:",
            years,
            index=0
        )
    
    with col3:
        # Filtro por estado
        states = ["Todos"] + sorted(tournaments['state'].dropna().unique().tolist())
        selected_state = st.selectbox(
            "🏁 Estado:",
            states,
            index=0
        )
    
    # Aplicar filtros
    filtered_tournaments = tournaments.copy()
    
    if selected_category != "Todas":
        filtered_tournaments = filtered_tournaments[filtered_tournaments['category'] == selected_category]
    
    if selected_year != "Todos":
        filtered_tournaments = filtered_tournaments[filtered_tournaments['started_year'] == selected_year]
    
    if selected_state != "Todos":
        filtered_tournaments = filtered_tournaments[filtered_tournaments['state'] == selected_state]
    
    # Mostrar estatísticas
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("Total de Torneios", len(filtered_tournaments))
    with col_stats2:
        if not filtered_tournaments.empty:
            tournament_ids = filtered_tournaments['id'].tolist()
            total_matches = len(matches[matches['tournament_id'].isin(tournament_ids)])
            st.metric("Total de Partidas", total_matches)
        else:
            st.metric("Total de Partidas", 0)
    with col_stats3:
        completed_tournaments = len(filtered_tournaments[filtered_tournaments['state'] == 'complete'])
        st.metric("Torneios Finalizados", completed_tournaments)
    
    # Lista de torneios
    if not filtered_tournaments.empty:
        st.subheader("📋 Lista de Torneios")
        
        # Preparar dados para exibição
        display_tournaments = filtered_tournaments.copy()
        display_tournaments = display_tournaments.sort_values('started_at', ascending=False)
        
        # Adicionar informação do campeão
        champions_info = []
        for _, tournament in display_tournaments.iterrows():
            champion = get_tournament_champion(matches, tournament['id'])
            champions_info.append(champion['name'] if champion else 'Em andamento')
        
        display_tournaments['champion'] = champions_info
        
        # Selecionar colunas para exibição
        display_columns = ['name', 'category', 'started_month_year', 'state', 'champion']
        display_tournaments_table = display_tournaments[display_columns].copy()
        display_tournaments_table.columns = ['Nome', 'Categoria', 'Data', 'Estado', 'Campeão']
        
        # Exibir tabela
        st.dataframe(
            display_tournaments_table,
            use_container_width=True,
            hide_index=True
        )
        
        # Seleção de torneio para visualizar chave
        st.subheader("🔍 Visualizar Chave do Torneio")
        
        tournament_options = {
            f"{row['name']} ({row['started_month_year']})": row['id'] 
            for _, row in display_tournaments.iterrows()
        }
        
        if tournament_options:
            selected_tournament_name = st.selectbox(
                "Selecione um torneio para visualizar a chave:",
                ["Selecione..."] + list(tournament_options.keys())
            )
            
            if selected_tournament_name != "Selecione...":
                tournament_id = tournament_options[selected_tournament_name]
                tournament_info = display_tournaments[display_tournaments['id'] == tournament_id].iloc[0]
                
                # Mostrar chave do torneio
                create_tournament_bracket(matches, tournament_id, tournament_info['name'])
                

        else:
            st.info("Nenhum torneio disponível para visualização.")
    else:
        st.info("Nenhum torneio encontrado com os filtros selecionados.")
