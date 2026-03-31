import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from player_analysis import display_player_page
from rankings import display_rankings_page
from tournaments import display_tournaments_page
import tracemalloc
import warnings
import asyncio
import io
import os

# Inicializar tracemalloc
tracemalloc.start()

# Configurar para ignorar avisos específicos do asyncio
warnings.filterwarnings("ignore", category=RuntimeWarning, message="coroutine.*never awaited")

# Configuração da página
st.set_page_config(
    page_title="BLK Tennis Insights",
    page_icon="🎾",
    layout="centered"
)

# Função para obter query parameters e host
def get_query_params():
    """Obtém os query parameters da URL e o host"""
    query_params = st.query_params
    
    # Em produção, usa o domínio correto
    host = 'https://blk-tennis-insights.streamlit.app'
    
    return {
        'player_id': query_params.get('player_id', None),
        'page': query_params.get('page', 'Análise de Jogadores'),
        'host': host
    }

@st.cache_data
def load_data():
    with st.spinner('Carregando dados do banco...'):
        try:
            from challonge_sync.db import init_schema_if_needed
            init_schema_if_needed()
        except Exception as e:
            st.warning(f"Bootstrap do schema: {e}")

        db_paths = []
        env_path = os.environ.get("BLK_SQLITE_PATH")
        if env_path:
            db_paths.append(env_path)
        db_paths.extend(["database.sqlite", "/app/database.sqlite"])

        conn = None
        chosen_path = None
        for path in db_paths:
            try:
                conn = sqlite3.connect(path)
                chosen_path = path
                break
            except sqlite3.OperationalError:
                continue

        if conn is None:
            st.error(
                "Não foi possível conectar ao banco de dados. "
                "Defina BLK_SQLITE_PATH ou coloque database.sqlite na raiz do projeto."
            )
            return None, None, None

        st.session_state["db_path"] = chosen_path

        try:
            matches = pd.read_sql_query("SELECT * FROM matches", conn)
            players = pd.read_sql_query("SELECT * FROM players", conn)
            tournaments = pd.read_sql_query("SELECT * FROM tournaments", conn)
        except Exception as e:
            conn.close()
            st.error(f"Erro ao ler views do banco (rode a sincronização ou verifique o schema): {e}")
            return None, None, None
        conn.close()

        print("\nColunas em matches:", matches.columns.tolist())
        print("\nColunas em tournaments:", tournaments.columns.tolist())
        print("\nColunas em players:", players.columns.tolist())

        if "start_date" in tournaments.columns:
            matches = matches.merge(
                tournaments[["id", "start_date"]],
                left_on="tournament_id",
                right_on="id",
                suffixes=("", "_tournament"),
            )
            matches = matches.rename(columns={"start_date": "tournament_date"})
        elif "created_at" in tournaments.columns:
            matches = matches.merge(
                tournaments[["id", "created_at"]],
                left_on="tournament_id",
                right_on="id",
                suffixes=("", "_tournament"),
            )
            matches = matches.rename(columns={"created_at": "tournament_date"})
        elif "started_at" in tournaments.columns:
            matches = matches.merge(
                tournaments[["id", "started_at"]],
                left_on="tournament_id",
                right_on="id",
                suffixes=("", "_tournament"),
            )
            matches = matches.rename(columns={"started_at": "tournament_date"})

        return matches, players, tournaments

# ===== Helpers/Admin =====
def _get_admin_password() -> str | None:
    try:
        # Preferir secrets em produção
        secret_pwd = st.secrets.get('ADMIN_PASSWORD')  # type: ignore[attr-defined]
    except Exception:
        secret_pwd = None
    env_pwd = os.environ.get('ADMIN_PASSWORD')
    return secret_pwd or env_pwd

def _connect_db() -> sqlite3.Connection | None:
    db_path = st.session_state.get("db_path")
    if not db_path:
        paths = []
        if os.environ.get("BLK_SQLITE_PATH"):
            paths.append(os.environ["BLK_SQLITE_PATH"])
        paths.extend(["database.sqlite", "/app/database.sqlite"])
        for path in paths:
            try:
                conn = sqlite3.connect(path)
                st.session_state["db_path"] = path
                return conn
            except sqlite3.OperationalError:
                continue
        return None
    try:
        return sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        return None


def _get_challonge_credentials() -> tuple[str | None, str | None]:
    try:
        u = st.secrets.get("CHALLONGE_USERNAME")  # type: ignore[attr-defined]
        k = st.secrets.get("CHALLONGE_API_KEY")  # type: ignore[attr-defined]
    except Exception:
        u, k = None, None
    return (u or os.environ.get("CHALLONGE_USERNAME"), k or os.environ.get("CHALLONGE_API_KEY"))

def display_admin_page():
    st.header('🔐 Admin')

    # Botão de logout se já estiver autenticado
    if st.session_state.get('admin_authenticated'):
        col1, col2 = st.columns([0.8, 0.2])
        with col2:
            if st.button('🚪 Logout', type='secondary'):
                st.session_state['admin_authenticated'] = False
                st.rerun()

    configured_password = _get_admin_password()
    if not st.session_state.get('admin_authenticated'):
        st.info('Área restrita. Informe a senha de administrador.')
        if not configured_password:
            st.error('Senha de administrador não configurada. Defina ADMIN_PASSWORD em st.secrets ou variável de ambiente.')
            return
        with st.form('admin_login_form', clear_on_submit=True):
            pwd = st.text_input('Senha', type='password')
            submitted = st.form_submit_button('Entrar')
        if submitted:
            if pwd == configured_password:
                st.session_state['admin_authenticated'] = True
                st.success('Autenticado com sucesso!')
                st.rerun()  # Recarrega a página para mostrar o conteúdo autenticado
            else:
                st.error('Senha inválida.')
        return  # CRÍTICO: Impede acesso ao conteúdo sem autenticação

    conn = _connect_db()
    if conn is None:
        st.error('Não foi possível abrir conexão com o banco de dados.')
        return

    with conn:
        tabs = st.tabs(
            [
                "🧑‍💼 Jogadores",
                "🏟️ Torneios",
                "🔄 Sincronização Challonge",
                "🔗 Mesclar jogadores",
            ]
        )

        # ----- Jogadores (challonge_participants) -----
        with tabs[0]:
            st.subheader('Editar Jogadores (participants)')
            # Filtros
            search = st.text_input('Buscar por nome/username/email', '')
            limit = st.number_input('Limite', min_value=10, max_value=5000, value=200, step=10)

            base_query = (
                "SELECT id, tournament_id, name, display_name, username, email, seed, active, final_rank, player_id "
                "FROM challonge_participants"
            )
            df_players = pd.read_sql_query(base_query + " ORDER BY id DESC LIMIT ?", conn, params=(int(limit),))
            if search:
                mask = (
                    df_players['name'].str.contains(search, case=False, na=False) |
                    df_players['display_name'].str.contains(search, case=False, na=False) |
                    df_players['username'].str.contains(search, case=False, na=False) |
                    df_players['email'].str.contains(search, case=False, na=False)
                )
                df_players = df_players[mask]

            st.dataframe(df_players, use_container_width=True)

            if df_players.empty:
                st.info('Nenhum jogador encontrado com os filtros atuais.')
            else:
                # Seleção e edição
                selected_id = st.selectbox(
                    'Selecionar jogador pelo ID',
                    options=df_players['id'].tolist(),
                    format_func=lambda x: f"{x} - {df_players.loc[df_players['id']==x, 'name'].values[0]}" if (df_players['id']==x).any() else str(x)
                )

                selected_rows = df_players.loc[df_players['id'] == selected_id]
                if selected_rows.empty:
                    st.warning('Seleção inválida. Atualize a lista ou ajuste os filtros.')
                else:
                    row = selected_rows.iloc[0]
                    with st.form('edit_player_form'):
                        name = st.text_input('name', row['name'] or '')
                        display_name = st.text_input('display_name', row['display_name'] or '')
                        email = st.text_input('email', row['email'] or '')
                        submitted = st.form_submit_button('Salvar alterações')

                    if submitted:
                        try:
                            conn.execute(
                                """
                                UPDATE challonge_participants
                                SET name = ?, display_name = ?, email = ?
                                WHERE id = ?
                                """,
                                (name, display_name, email, int(selected_id))
                            )
                            conn.commit()
                            st.success('Jogador atualizado com sucesso.')
                        except Exception as e:
                            st.error(f'Erro ao atualizar jogador: {e}')

        # ----- Torneios (challonge_tournaments) -----
        with tabs[1]:
            st.subheader('Editar Torneios')
            df_tourn = pd.read_sql_query(
                "SELECT id, name, category, state, started_at, completed_at, description FROM challonge_tournaments ORDER BY started_at DESC, id DESC",
                conn
            )
            st.dataframe(df_tourn, use_container_width=True)

            if df_tourn.empty:
                st.info('Nenhum torneio encontrado. Use a aba **Sincronização Challonge** para importar da API.')
            else:
                selected_tid = st.selectbox(
                    'Selecionar torneio pelo ID',
                    options=df_tourn['id'].tolist(),
                    format_func=lambda x: f"{x} - {df_tourn.loc[df_tourn['id']==x, 'name'].values[0]}" if (df_tourn['id']==x).any() else str(x)
                )

                selected_trows = df_tourn.loc[df_tourn['id'] == selected_tid]
                if selected_trows.empty:
                    st.warning('Seleção inválida. Atualize a lista.')
                else:
                    trow = selected_trows.iloc[0]

                    def _parse_dt(val: str | None):
                        if pd.isna(val) or val in (None, ''):
                            return None
                        try:
                            return pd.to_datetime(val)
                        except Exception:
                            return None

                    started_dt = _parse_dt(trow['started_at'])
                    completed_dt = _parse_dt(trow['completed_at'])

                    with st.form('edit_tournament_form'):
                        name = st.text_input('name', trow['name'] or '')
                        category = st.text_input('category', trow['category'] or '')
                        state = st.selectbox('state', options=['pending', 'underway', 'complete', 'awaiting_review', 'group_stages_underway'], index=(['pending','underway','complete','awaiting_review','group_stages_underway'].index(trow['state']) if trow['state'] in ['pending','underway','complete','awaiting_review','group_stages_underway'] else 0))
                        started_at = st.text_input('started_at (YYYY-MM-DD HH:MM:SS ou vazio)', started_dt.strftime('%Y-%m-%d %H:%M:%S') if started_dt is not None else '')
                        completed_at = st.text_input('completed_at (YYYY-MM-DD HH:MM:SS ou vazio)', completed_dt.strftime('%Y-%m-%d %H:%M:%S') if completed_dt is not None else '')
                        description = st.text_area('description', trow['description'] or '')
                        submitted_t = st.form_submit_button('Salvar alterações')

                    if submitted_t:
                        try:
                            started_val = None if started_at.strip() == '' else started_at.strip()
                            completed_val = None if completed_at.strip() == '' else completed_at.strip()
                            conn.execute(
                                """
                                UPDATE challonge_tournaments
                                SET name = ?, category = ?, state = ?, started_at = ?, completed_at = ?, description = ?
                                WHERE id = ?
                                """,
                                (name, category if category != '' else None, state, started_val, completed_val, description if description != '' else None, int(selected_tid))
                            )
                            conn.commit()
                            st.success('Torneio atualizado com sucesso.')
                        except Exception as e:
                            st.error(f'Erro ao atualizar torneio: {e}')

        # ----- Sincronização Challonge (Python) -----
        with tabs[2]:
            if st.session_state.pop("admin_sync_success", False):
                st.success("Sincronização concluída com sucesso.")
            err_msg = st.session_state.pop("admin_sync_error", None)
            if err_msg:
                st.error(err_msg)

            st.subheader("Dados do Challonge")
            st.markdown(
                "Aqui o app **baixa** torneios, jogadores e partidas da sua conta Challonge "
                "e grava no banco local. As chaves ficam em **Secrets** "
                "(`CHALLONGE_USERNAME` e `CHALLONGE_API_KEY`)."
            )
            cu, ck = _get_challonge_credentials()
            if not cu or not ck:
                st.error(
                    "Configure `CHALLONGE_USERNAME` e `CHALLONGE_API_KEY` em `.streamlit/secrets.toml` "
                    "ou nas variáveis de ambiente."
                )
            else:
                st.success("Conectado à API Challonge (credenciais OK).")

            log_box = st.empty()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Uso do dia a dia** — importa só o que ainda não entrou (torneios novos).")
                btn_inc = st.button(
                    "Buscar dados novos",
                    key="sync_inc",
                    type="primary",
                    disabled=not (cu and ck),
                    help="Atualiza a lista de torneios na API e baixa participantes/partidas só dos torneios que ainda não foram sincronizados.",
                )
            with c2:
                st.markdown("**Tudo de novo** — refaz a importação de **todos** os torneios (útil após mudanças grandes na API).")
                btn_force = st.button(
                    "Atualizar todos os torneios",
                    key="sync_force",
                    disabled=not (cu and ck),
                    help="Baixa de novo participantes e partidas de cada torneio. Pode demorar mais que a opção ao lado.",
                )

            with st.expander("Opções avançadas — apagar banco local"):
                st.markdown(
                    "Apaga o arquivo **database.sqlite** deste projeto, recria as tabelas vazias "
                    "e em seguida baixa tudo do Challonge. Use para **testar do zero** ou se o banco "
                    "estiver corrompido; não desfaz alterações no site Challonge."
                )
                confirm_reset = st.checkbox(
                    "Entendo que os dados locais serão apagados",
                    key="sync_reset_confirm",
                )
                btn_reset = st.button(
                    "Apagar banco local e baixar tudo de novo",
                    key="sync_reset",
                    disabled=not (cu and ck) or not confirm_reset,
                    type="secondary",
                )

            def _run_sync(force: bool, reset_db: bool) -> None:
                from challonge_sync.pipeline import run_pipeline

                buf = io.StringIO()

                def _log(msg: str) -> None:
                    buf.write(msg + "\n")
                    log_box.code(buf.getvalue(), language="text")

                run_pipeline(
                    username=cu or "",
                    api_key=ck or "",
                    force=force,
                    reset_db=reset_db,
                    log=_log,
                )
                st.cache_data.clear()
                st.session_state["admin_sync_success"] = True

            if btn_inc and cu and ck:
                try:
                    _run_sync(force=False, reset_db=False)
                except Exception as e:
                    st.session_state["admin_sync_error"] = str(e)
                st.rerun()
            if btn_force and cu and ck:
                try:
                    _run_sync(force=True, reset_db=False)
                except Exception as e:
                    st.session_state["admin_sync_error"] = str(e)
                st.rerun()
            if btn_reset and cu and ck and confirm_reset:
                try:
                    _run_sync(force=True, reset_db=True)
                except Exception as e:
                    st.session_state["admin_sync_error"] = str(e)
                st.rerun()

        # ----- Mesclar participantes (manual) -----
        with tabs[3]:
            st.subheader("Mesclar jogadores duplicados")
            st.markdown(
                "Busque pelo **nome**, selecione **vários** registros e escolha qual fica como **principal**. "
                "Os outros são removidos e as partidas passam a usar o mesmo participante — mesma lógica "
                "do merge automático após o sync."
            )
            m_search = st.text_input(
                "Buscar por nome (contém)",
                key="merge_search",
                placeholder="Ex.: Silva, João…",
            )
            m_limit = st.number_input(
                "Máximo de linhas na busca",
                min_value=20,
                max_value=5000,
                value=500,
                step=50,
                key="merge_limit",
            )
            q = (
                "SELECT p.id, p.tournament_id, p.name, p.display_name, t.name AS tournament_name "
                "FROM challonge_participants p "
                "JOIN challonge_tournaments t ON t.id = p.tournament_id "
                "ORDER BY p.id DESC LIMIT ?"
            )
            df_m = pd.read_sql_query(q, conn, params=(int(m_limit),))
            if m_search.strip():
                ms = m_search.strip()
                mask_m = (
                    df_m["name"].str.contains(ms, case=False, na=False)
                    | df_m["display_name"].str.contains(ms, case=False, na=False)
                    | df_m["tournament_name"].str.contains(ms, case=False, na=False)
                )
                df_m = df_m[mask_m]

            if df_m.empty:
                st.info("Nenhum participante encontrado. Ajuste a busca ou rode a sincronização.")
            else:
                st.caption(f"{len(df_m)} registro(s) na lista.")
                opt_ids = df_m["id"].astype(int).tolist()

                def _fmt_mid(pid: int) -> str:
                    r = df_m.loc[df_m["id"] == pid].iloc[0]
                    return (
                        f"ID {pid} — {r['name']} "
                        f"(torneio: {r['tournament_name'][:40]}{'…' if len(str(r['tournament_name'])) > 40 else ''})"
                    )

                picked = st.multiselect(
                    "Selecione os participantes a mesclar (mínimo 2)",
                    options=opt_ids,
                    format_func=_fmt_mid,
                    key="merge_multiselect",
                )
                if len(picked) >= 2:
                    keep_id = st.selectbox(
                        "Manter este como principal (nome e dados deste registro ficam)",
                        options=picked,
                        format_func=_fmt_mid,
                        key="merge_keep",
                    )
                    remove_ids = [x for x in picked if x != keep_id]
                    st.warning(
                        f"Serão **removidos** {len(remove_ids)} registro(s); "
                        f"as partidas passam a referenciar o ID **{keep_id}** (pode haver torneios diferentes)."
                    )
                    if st.button("Confirmar mesclagem", type="primary", key="merge_confirm"):
                        try:
                            from challonge_sync.merge import merge_manual_into

                            n = merge_manual_into(
                                conn,
                                keep_id=int(keep_id),
                                remove_ids=remove_ids,
                            )
                            st.success(
                                f"Mesclagem concluída: {n} registro(s) fundido(s) no principal {keep_id}."
                            )
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

# Carregar dados
matches, players, tournaments = load_data()

if matches is None:
    st.stop()

# Debug temporário
print("Colunas disponíveis em matches:", matches.columns.tolist())

# Título principal
st.title("🎾 BLK Tennis Insights")

# Obter query parameters
params = get_query_params()

# Botão global sutil de refresh
_top_cols = st.columns([0.85, 0.15])
with _top_cols[1]:
    if st.button("⟳", help="Atualizar dados (limpa cache e recalcula)", key="global_refresh"):
        st.cache_data.clear()
        st.rerun()

# Navegação no topo com ícones
pages = ["👤 Análise de Jogadores", "🏆 Rankings", "🎾 Torneios", "🔐 Admin"]
page_name_to_index = {"Análise de Jogadores": 0, "Rankings": 1, "Torneios": 2, "Admin": 3}
page = st.selectbox(
    "📍 Navegação:",
    pages,
    index=page_name_to_index.get(params['page'], 0),
    format_func=lambda x: x.split(" ", 1)[1]  # Remove o emoji do display
)

# Atualizar query parameters quando a página mudar
st.query_params['page'] = page.split(" ", 1)[1]  # Remove o emoji
if params['player_id']:
    st.query_params['player_id'] = params['player_id']

# Exibir página selecionada
if "Análise de Jogadores" in page:
    # Armazenar o host na session_state
    st.session_state['host'] = params['host']
    display_player_page(matches, players, shared_player_id=params['player_id'])
elif "Rankings" in page:
    # Armazenar o host na session_state
    st.session_state['host'] = params['host']
    display_rankings_page(matches, players, tournaments)
elif "Torneios" in page:
    # Armazenar o host na session_state
    st.session_state['host'] = params['host']
    display_tournaments_page(matches, players, tournaments) 
elif "Admin" in page:
    # Armazenar o host na session_state
    st.session_state['host'] = params['host']
    display_admin_page()