# BLK Tennis Insights

Dashboard interativo para análise de dados de tênis da academia BLK Tennis.

## Requisitos

- Python 3.10 ou superior (recomendado)
- pip

## Instalação

1. Clone o repositório e entre na pasta:

```bash
git clone [URL_DO_REPOSITÓRIO]
cd blk-tennis-insights
python3 -m venv venv
source venv/bin/activate
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Variáveis de ambiente (sincronização Challonge)

- `CHALLONGE_USERNAME` — usuário da API Challonge (Basic Auth)
- `CHALLONGE_API_KEY` — chave da API
- `BLK_SQLITE_PATH` — (opcional) caminho absoluto para `database.sqlite`; o padrão é `database.sqlite` na raiz do projeto

No Streamlit Cloud, configure esses valores em **Secrets** (e `ADMIN_PASSWORD` para o painel Admin).

## Execução

```bash
streamlit run app.py
```

O app fica em `http://localhost:8501`.

## Sincronização com o Challonge (Python)

O pipeline que antes era `php artisan` no Laravel foi substituído pelo pacote `challonge_sync/`.

### Linha de comando

```bash
export CHALLONGE_USERNAME="seu_usuario"
export CHALLONGE_API_KEY="sua_chave"

# Incremental (só torneios com synced=0)
python3 -m challonge_sync

# Reprocessar todos os torneios
python3 -m challonge_sync --force

# Apagar o SQLite e recriar o schema, depois sync completo (destrutivo)
python3 -m challonge_sync --reset-db --force
```

### Painel Admin (Streamlit)

Na página **Admin**, aba **Sincronização Challonge**, use os botões incremental, force ou reset (este último exige confirmação).

### Schema do banco

O arquivo [`schema.sql`](schema.sql) define tabelas `challonge_*` e as views `matches`, `players`, `tournaments`. Na primeira execução, se o banco estiver ausente, o app tenta aplicar esse schema automaticamente.

### Mescla de participantes (fuzzy)

Decisões opcionais ficam em `merge_decisions.json` na raiz (ou caminho em `MERGE_DECISIONS_PATH`). Grupos fuzzy sem decisão persistida são ignorados; duplicatas com nomes “efetivamente idênticos” são mescladas automaticamente.

## Estrutura do projeto

- `app.py` — aplicação Streamlit
- `challonge_sync/` — cliente HTTP, sync, merge, categorias
- `schema.sql` — DDL SQLite e views
- `database.sqlite` — banco local (gerado; não versionar dados reais)
- `requirements.txt` — dependências Python

## Funcionalidades

- Análise de jogadores, rankings e torneios
- Admin: edição de participantes e torneios; sincronização on demand com Challonge
