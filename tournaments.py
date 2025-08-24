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

def create_tournament_bracket(matches, tournament_id, tournament_name):
    """Cria a visualização da chave do torneio"""
    tournament_matches = matches[matches['tournament_id'] == tournament_id].copy()
    
    if tournament_matches.empty:
        st.warning(f"Nenhuma partida encontrada para o torneio {tournament_name}")
        return
    
    # Organizar partidas por rodada
    rounds = sorted(tournament_matches['round'].unique())
    
    # Criar estrutura da chave
    st.subheader(f"🏆 Chave do Torneio: {tournament_name}")
    
    # Identificar o campeão
    champion = get_tournament_champion(matches, tournament_id)
    if champion:
        st.success(f"🥇 **Campeão:** {champion['name']}")
    
    # Determinar nomes das rodadas baseado no número total de rodadas
    max_round = max(rounds)
    round_names = {}
    
    if max_round == 4:
        round_names = {1: "1ª Rodada", 2: "Quartas de Final", 3: "Semifinal", 4: "Final"}
    elif max_round == 3:
        round_names = {1: "Quartas de Final", 2: "Semifinal", 3: "Final"}
    elif max_round == 2:
        round_names = {1: "Semifinal", 2: "Final"}
    elif max_round == 1:
        round_names = {1: "Final"}
    else:
        for r in rounds:
            round_names[r] = f"Rodada {r}"
    
    # Mostrar partidas por rodada em formato de chave ATP
    cols = st.columns(len(rounds))
    
    for i, round_num in enumerate(rounds):
        with cols[i]:
            round_name = round_names.get(round_num, f"Rodada {round_num}")
            st.markdown(f"### {round_name}")
            
            round_matches = tournament_matches[tournament_matches['round'] == round_num].sort_values('match_id')
            
            for j, (_, match) in enumerate(round_matches.iterrows()):
                # Criar card da partida estilo ATP
                winner_name = match['winner_name']
                loser_name = match['loser_name']
                score = match['score'] if pd.notna(match['score']) else "N/A"
                
                # Obter host da session_state para criar links
                host = st.session_state.get('host', 'http://localhost:8502')
                winner_link = f"{host}?page=Análise de Jogadores&player_id={match['winner_id']}"
                loser_link = f"{host}?page=Análise de Jogadores&player_id={match['loser_id']}"
                
                # Estilizar o card da partida no estilo ATP com links
                st.markdown(f"""
                <div style="
                    border: 2px solid #1f77b4;
                    border-radius: 12px;
                    padding: 15px;
                    margin: 10px 0;
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                ">
                    <div style="
                        font-weight: bold; 
                        color: #1f77b4; 
                        font-size: 16px;
                        margin-bottom: 5px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <span>🏆 {winner_name}</span>
                        <a href="{winner_link}" target="_self" style="
                            text-decoration: none;
                            font-size: 14px;
                            color: #1f77b4;
                            background-color: #e3f2fd;
                            padding: 2px 6px;
                            border-radius: 4px;
                            border: 1px solid #1f77b4;
                            cursor: pointer;
                        " title="Ver análise do jogador">👤</a>
                    </div>
                    <div style="
                        color: #6c757d; 
                        font-size: 14px;
                        margin-bottom: 8px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <span>⚪ {loser_name}</span>
                        <a href="{loser_link}" target="_self" style="
                            text-decoration: none;
                            font-size: 14px;
                            color: #6c757d;
                            background-color: #f5f5f5;
                            padding: 2px 6px;
                            border-radius: 4px;
                            border: 1px solid #6c757d;
                            cursor: pointer;
                        " title="Ver análise do jogador">👤</a>
                    </div>
                    <div style="
                        font-size: 12px; 
                        color: #495057; 
                        background-color: #fff;
                        padding: 4px 8px;
                        border-radius: 6px;
                        text-align: center;
                        border: 1px solid #dee2e6;
                    ">
                        {score}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Adicionar espaçamento entre partidas
                if j < len(round_matches) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)

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
                
                # Mostrar estatísticas do torneio
                with st.expander("📊 Estatísticas do Torneio", expanded=False):
                    tournament_matches = matches[matches['tournament_id'] == tournament_id]
                    
                    col_t1, col_t2, col_t3 = st.columns(3)
                    with col_t1:
                        st.metric("Partidas", len(tournament_matches))
                    with col_t2:
                        unique_players = pd.concat([
                            tournament_matches['winner_id'],
                            tournament_matches['loser_id']
                        ]).nunique()
                        st.metric("Participantes", unique_players)
                    with col_t3:
                        if not tournament_matches.empty:
                            rounds = tournament_matches['round'].max()
                            st.metric("Rodadas", rounds)
                        else:
                            st.metric("Rodadas", 0)
        else:
            st.info("Nenhum torneio disponível para visualização.")
    else:
        st.info("Nenhum torneio encontrado com os filtros selecionados.")
