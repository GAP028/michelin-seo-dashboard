import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.express as px
import sqlite3
from dash.dependencies import Input, Output, State
import io
import base64
import os
import pycountry
from dash.exceptions import PreventUpdate

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


df_dates = pd.DataFrame()
df_appareils = pd.DataFrame()
df_requetes = pd.DataFrame()

app = dash.Dash(__name__)
server = app.server
app.title = "Michelin Dashboard"

uploaded_data_store = {}

def style_plotly_figure(fig, theme):
    """Applique un thème Plotly cohérent avec ton thème Dash."""
    if fig is None or fig == {}:
        return fig

    if theme == "sombre":
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#1e1e1e",
            font=dict(color="#f5f5f5"),
            title=dict(font=dict(color="#f5f5f5")),
            legend=dict(font=dict(color="#f5f5f5")),
        )
        # axes lisibles en sombre
        fig.update_xaxes(gridcolor="#333", zerolinecolor="#333")
        fig.update_yaxes(gridcolor="#333", zerolinecolor="#333")

    elif theme == "orange":
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#fff8f0",
            plot_bgcolor="#fff8f0",
            font=dict(color="#222222"),
            title=dict(font=dict(color="#222222")),
        )

    else:  # clair
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#222222"),
            title=dict(font=dict(color="#222222")),
        )

    return fig

THEME_STYLES = {
    "clair": {
        "backgroundColor": "#ffffff",
        "color": "#222222",
        "table_header": {'backgroundColor': '#0B3D91', 'color': 'white'},
        "table_cell": {'textAlign': 'center', 'padding': '5px', 'color': 'black'}
    },
    "sombre": {
        "backgroundColor": '#1e1e1e',
        "color": '#ffffff',
        "table_header": {'backgroundColor': '#0B3D91', 'color': 'white'},
        "table_cell": {'textAlign': 'center', 'padding': '5px', 'color': 'white'}
    },
    "orange": {
        "backgroundColor": '#fff8f0',
        "color": '#e67e22',
        "table_header": {'backgroundColor': '#0B3D91', 'color': 'white'},
        "table_cell": {'textAlign': 'center', 'padding': '5px', 'color': '#e67e22'}
    }
}


app.layout = html.Div(id="main-container",**{"data-theme": "light"},style={'fontFamily': 'Arial, sans-serif', 'margin': '20px'}, children=[
    dcc.Store(id="theme-store", data="clair"),  # ← thème par défaut
    dcc.Store(id="data-store", data=None),          # contiendra les données uploadées
    dcc.Store(id="data-source-store", data="db"),   # "db" ou "upload"

     html.H1("Dashboard Michelin - Marché Mexicain", style={'textAlign': 'center', 'color': '#0B3D91'}),
      html.Button("Changer de thème", id='theme-toggle', n_clicks=0, style={
        'margin': '10px',
        'padding': '10px',
        'backgroundColor': '#e67e22',
        'color': 'white',
        'border': 'none',
        'borderRadius': '5px'
        }),

        html.Div(
            [
                html.H2("🚀 Bienvenue sur le Dashboard d'Analyse SEO"),
                html.P(
                    """
                    Cette plateforme permet d'analyser des données SEO (clics, impressions, CTR, position)
                    à partir de fichiers CSV ou Excel fournis par l'utilisateur.

                    🔹 Étape 1 : Téléversez votre fichier.
                    🔹 Étape 2 : Le système analyse automatiquement les données.
                    🔹 Étape 3 : Visualisez les KPIs et graphiques interactifs.
                    
                    Aucune donnée n'est stockée sur le serveur.
                    L'analyse est effectuée uniquement en mémoire pour des raisons de confidentialité.
                    """,
                    style={"fontSize": "16px", "lineHeight": "1.8"}
                ),
                html.Hr()
            ],
            className="card",
            style={
                "backgroundColor": "#f4f6f9",
                "padding": "20px",
                "borderRadius": "10px",
                "marginBottom": "30px"
            }
        ),

        html.Div([
        html.H2("Téléversement de fichier CSV", style={'color': '#0B3D91'}),
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Glissez-déposez un fichier CSV ici ou ', html.A('cliquez pour sélectionner')]),
            style={
                'width': '100%',
                'height': '100px',
                'lineHeight': '100px',
                'borderWidth': '2px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'marginBottom': '10px'
            },
            multiple=False
        ),
        html.Button(" Supprimer le fichier", id='btn-upload-clear', n_clicks=0,disabled=True, style={'marginBottom': '10px'}),
        html.Button(" Télécharger le fichier modifié", id='btn-save-upload', n_clicks=0,disabled=True, style={'marginBottom': '10px'}),
        html.Button(" Exporter le Résumé en PDF", id='btn-export-pdf', n_clicks=0,disabled=True, style={'marginBottom': '10px'}),
        html.Button(" Réinitialiser le dashboard", id='btn-reset', n_clicks=0,
            style={'marginBottom': '20px', 'backgroundColor': '#0B3D91', 'color': 'white', 'padding': '10px', 'borderRadius': '5px'}),
        dcc.Download(id="download-pdf"),
        dcc.Download(id="download-modified-upload"),
        html.Div(id='upload-status'),

        html.Div([
            html.H3(" Aperçu du fichier téléversé", style={'color': '#0B3D91'}),
            dash_table.DataTable(
                id='table-upload',
                columns=[],
                data=[],
                editable=True,
                row_deletable=True,
                style_table={'overflowX': 'auto'},
                style_cell={},
                style_header={}
            )
        ])
    ])
])
app.layout.children += [
    html.Div([
        html.H2(" Historique des actions", style={'color': '#0B3D91'}),
        html.Ul(id='log-container',className="card", style={'maxHeight': '200px', 'overflowY': 'auto', 'backgroundColor': '#f4f4f4', 'padding': '10px'})
    ], style={'marginTop': '30px'}),
    dcc.Store(id='log-store', data=[]),

    html.Div([
        html.H2("KPI Globaux", style={'color': '#0B3D91'}),
        html.Div([
            html.Div([html.H4("Total des clics"), html.P(id='kpi-clics', style={'fontSize': 22})]),
            html.Div([html.H4("Total des impressions"), html.P(id='kpi-impressions', style={'fontSize': 22})]),
            html.Div([html.H4("CTR moyen"), html.P(id='kpi-ctr', style={'fontSize': 22})]),
            html.Div([html.H4("Position moyenne"), html.P(id='kpi-position', style={'fontSize': 22})])
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': 40})
    ]),

    html.Div([
    html.Div(id="data-source-debug", style={"marginTop": "8px", "fontStyle": "italic"}),
    ], style={'marginBottom': '15px'}),

    html.Div([
        html.H2("Filtres", style={'color': '#0B3D91'}),
        dcc.Dropdown(
            id='dropdown-pays',
            options=[],
            value=None,
            clearable=False,
            placeholder="Veuillez d'abord téléverser un fichier",
            style={'width': '50%', 'marginBottom': 10}
        ),

        dcc.DatePickerRange(
            id='date-range',
            start_date=None,
            end_date=None,
            display_format='YYYY-MM-DD',
            min_date_allowed=None,
            max_date_allowed=None,
            style={'marginBottom': 10}
        ),

        html.Div(
            id='error-message',
            style={
                'color': 'white',
                'backgroundColor': '#e74c3c',
                'padding': '10px',
                'marginBottom': '20px',
                'display': 'none',
                'borderRadius': '5px'
            }
        )

]),
    html.Div(
        id="dashboard-content",
        children=[
            dcc.Graph(id='graph-clics'),

            dcc.Graph(id='graph-appareils'),

            html.Div([
                html.Label(" Rechercher un mot-clé :", style={'color': '#0B3D91', 'fontWeight': 'bold'}),
                dcc.Input(
                    id='keyword-input',
                    type='text',
                    placeholder='Entrez un mot-clé...',
                    debounce=True,
                    style={'marginBottom': '15px', 'width': '50%', 'padding': '10px'}
                ),
            ]),
            dcc.Graph(id='graph-requetes'),
            html.Div([
                html.Label(" Choisissez une projection géographique :", style={'color': '#0B3D91', 'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id='projection-dropdown',
                    options=[
                        {'label': 'Orthographic (globe)', 'value': 'orthographic'},
                        {'label': 'Mercator', 'value': 'mercator'},
                        {'label': 'Natural Earth', 'value': 'natural earth'},
                        {'label': 'Equirectangular (classique)', 'value': 'equirectangular'},
                        {'label': 'Kavrayskiy7', 'value': 'kavrayskiy7'}
                    ],
                    value='orthographic',
                    clearable=False,
                    style={'width': '60%', 'marginBottom': '15px'}
                ),
            ]),

            html.Div([
                html.H2(" Carte du monde des clics", style={'color': '#0B3D91'}),
                dcc.Graph(id='graph-carte-monde')
            ], style={'marginBottom': 40}),

            dcc.Graph(id='graph-correlation'),
            
            html.Div([
                html.H2(" Table des Données SEO", style={'color': '#0B3D91'}),
                html.Button(" Exporter les données en CSV", id='btn-export', n_clicks=0, style={'marginBottom': 10}),
                dcc.Download(id="download-dataframe-csv"),
                dash_table.DataTable(
                    id='table-dates',
                    columns=[],
                    data=[],
                    editable=False,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '5px'},
                    style_header={'backgroundColor': '#0B3D91', 'color': 'white'}
                )
            ])
        ],
        style={"display": "none"}  # caché tant que pas de fichier
    ),
]
from dash.exceptions import PreventUpdate

@app.callback(
    [Output('upload-status', 'children'),
     Output('table-upload', 'columns'),
     Output('table-upload', 'data')],
    [Input('upload-data', 'contents'),
     Input('btn-upload-clear', 'n_clicks')],
    State('upload-data', 'filename')
)
def handle_upload(contents, clear_clicks, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "", [], []

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger == "btn-upload-clear":
        if 'data' in uploaded_data_store:
            uploaded_data_store.clear()
            return html.Div("✅ Fichier supprimé."), [], []
        raise PreventUpdate

    if contents:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            df_uploaded = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            uploaded_data_store['data'] = df_uploaded
            return (
                html.Div([
                    html.H5(f"✅ Fichier {filename} chargé avec succès."),
                    html.P("🔧 Vous pouvez modifier les données dans le tableau.")
                ]),
                [{"name": col, "id": col} for col in df_uploaded.columns],
                df_uploaded.to_dict('records')
            )
        except Exception as e:
            return html.Div([html.H5("❌ Erreur :"), html.Pre(str(e))]), [], []

    return "", [], []


@app.callback(
    [Output("btn-upload-clear", "disabled"),
     Output("btn-save-upload", "disabled"),
     Output("btn-export-pdf", "disabled")],
    Input("table-upload", "data")
)
def toggle_buttons(table_data):
    has_data = bool(table_data) and len(table_data) > 0
    return (not has_data, not has_data, not has_data)


@app.callback(
    [Output('dropdown-pays', 'options'),
     Output('dropdown-pays', 'value'),
     Output('date-range', 'start_date'),
     Output('date-range', 'end_date'),
     Output('keyword-input', 'value')],
    [Input('table-upload', 'data'),
     Input('btn-reset', 'n_clicks')],
    prevent_initial_call=True
)
def sync_filters_with_upload_or_reset(table_data, n_reset):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    # Si aucun fichier -> on vide tout
    if not table_data:
        return [], None, None, None, ""

    df = pd.DataFrame(table_data)

    # Vérifs colonnes minimales
    if 'pays' not in df.columns or 'date' not in df.columns:
        return [], None, None, None, ""

    # Nettoyage date
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    # options pays
    pays_uniques = df['pays'].dropna().unique()
    options = [{'label': p, 'value': p} for p in pays_uniques]

    # valeurs par défaut
    pays_defaut = pays_uniques[0] if len(pays_uniques) > 0 else None
    date_min = df['date'].min().date() if not df.empty else None
    date_max = df['date'].max().date() if not df.empty else None

    # Si déclencheur = upload -> on initialise
    if trigger == 'table-upload':
        return options, pays_defaut, date_min, date_max, ""

    # Si déclencheur = reset -> on réinitialise
    if trigger == 'btn-reset':
        return options, pays_defaut, date_min, date_max, ""

    raise PreventUpdate

@app.callback(
    Output("download-modified-upload", "data"),
    Input("btn-save-upload", "n_clicks"),
    State("table-upload", "data"),
    prevent_initial_call=True,
)
def download_modified(n_clicks, table_data):
    #  si aucun fichier -> on ne lance PAS de téléchargement (pas d'erreur)
    if not table_data or len(table_data) == 0:
        raise PreventUpdate

    df = pd.DataFrame(table_data)
    return dcc.send_data_frame(df.to_csv, "fichier_modifie.csv", index=False)

@app.callback(
    [Output('kpi-clics', 'children'),
     Output('kpi-impressions', 'children'),
     Output('kpi-ctr', 'children'),
     Output('kpi-position', 'children'),
     Output('graph-clics', 'figure'),
     Output('graph-correlation', 'figure'),
     Output('table-dates', 'columns'),
     Output('table-dates', 'data'),
     Output('error-message', 'children')],
    [Input('dropdown-pays', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('theme-store', 'data')]

)
def update_dashboard(selected_pays, start_date, end_date, theme):
    error_style = {
        'color': 'white',
        'backgroundColor': '#e74c3c',
        'padding': '10px',
        'marginBottom': '20px',
        'borderRadius': '5px'
    }

    # 1) pas de fichier
    if 'data' not in uploaded_data_store:
        return (
            "-", "-", "-", "-",     # KPI
            {}, {},                 # figures
            [], [],                 # table columns, table data
            html.Div("⚠️ Veuillez téléverser un fichier CSV ou Excel pour commencer l'analyse.", style=error_style)
        )

    # 2) dates manquantes
    if not start_date or not end_date:
        return (
            "-", "-", "-", "-",
            {}, {},
            [], [],
            html.Div("⚠️ Sélectionnez une plage de dates valide.", style=error_style)
        )

    # 3) dates incohérentes
    if pd.to_datetime(start_date) > pd.to_datetime(end_date):
        return (
            "-", "-", "-", "-",
            {}, {},
            [], [],
            html.Div("⚠️ La date de début ne peut pas être après la date de fin.", style=error_style)
        )

    # 4) filtrage
    df = uploaded_data_store['data'].copy()

    # sécurise les colonnes minimales
    required_cols = {"pays", "date", "nombre_clics", "impressions", "position"}
    missing = required_cols - set(df.columns)
    if missing:
        return (
            "-", "-", "-", "-",
            {}, {},
            [], [],
            html.Div(f"⚠️ Colonnes manquantes dans le fichier : {', '.join(sorted(missing))}", style=error_style)
        )

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    filtered_df = df[
        (df['pays'] == selected_pays) &
        (df['date'] >= pd.to_datetime(start_date)) &
        (df['date'] <= pd.to_datetime(end_date))
    ]

    if filtered_df.empty:
        return (
            "-", "-", "-", "-",
            {}, {},
            [], [],
            html.Div("⚠️ Aucune donnée disponible pour cette sélection.", style=error_style)
        )

    # 5) KPI
    total_clics = filtered_df['nombre_clics'].sum()
    total_impressions = filtered_df['impressions'].sum()
    ctr = round((total_clics / total_impressions) * 100, 2) if total_impressions else 0
    pos = round(filtered_df['position'].mean(), 2)

    # 6) figures
    fig = px.line(
        filtered_df, x='date', y='nombre_clics',
        title=f"Évolution des clics – {selected_pays}",
        markers=True
    )

    fig_corr = px.scatter(
        filtered_df,
        x='position',
        y='nombre_clics',
        size='impressions',
        title="Corrélation : Position vs Clics",
        labels={'position': 'Position', 'nombre_clics': 'Clics'}
    )
    fig = style_plotly_figure(fig, theme)
    fig_corr = style_plotly_figure(fig_corr, theme)


    # 7) table
    cols = [{"name": c, "id": c} for c in filtered_df.columns]
    data = filtered_df.to_dict("records")

    return (
        f"{total_clics:,} clics (sur la période sélectionnée)",
        f"{total_impressions:,} impressions",
        f"{ctr} %",
        f"{pos}",
        fig,
        fig_corr,
        cols,
        data,
        ""  # pas d'erreur
    )

@app.callback(
    Output('graph-appareils', 'figure'),
    [Input('dropdown-pays', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('theme-store', 'data')] 

)
def update_appareils(selected_pays, start_date, end_date,theme):
    # pas de fichier
    if 'data' not in uploaded_data_store:
        return {}

    df = uploaded_data_store['data'].copy()

    # colonnes nécessaires
    required = {"pays", "date", "nombre_clics", "appareil"}
    if not required.issubset(df.columns):
        # si tu veux debug: return px.scatter(title="Colonne 'appareil' manquante")
        return {}

    # nettoyage date
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    if not start_date or not end_date or not selected_pays:
        return {}

    # filtre
    f = df[
        (df['pays'] == selected_pays) &
        (df['date'] >= pd.to_datetime(start_date)) &
        (df['date'] <= pd.to_datetime(end_date))
    ]

    if f.empty:
        return {}

    # group by appareil
    g = f.groupby("appareil", as_index=False)["nombre_clics"].sum().sort_values("nombre_clics", ascending=False)

    fig = px.bar(
        g,
        x="appareil",
        y="nombre_clics",
        title="Répartition des clics par appareil",
        labels={"appareil": "Appareil", "nombre_clics": "Clics"}
    )
    fig.update_layout(transition_duration=400)
    fig = style_plotly_figure(fig, theme)
    return fig

@app.callback(
    [Output("main-container", "style"),
     Output("table-dates", "style_cell"),
     Output("table-dates", "style_header"),
     Output("main-container", "data-theme"),
     Output("table-upload", "style_cell"),
     Output("table-upload", "style_header")],
    Input("theme-store", "data")
)
def update_theme_style(theme):

    # ✅ mapping pour ton CSS: light / dark / orange
    theme_attr = "light"
    if theme == "sombre":
        theme_attr = "dark"
    elif theme == "orange":
        theme_attr = "orange"

    if theme == 'sombre':
        base_style = {
            'backgroundColor': '#1e1e1e',
            'color': '#f5f5f5',
            'fontFamily': 'Arial, sans-serif',
            'padding': '20px'
        }
        cell = {
            'textAlign': 'center',
            'padding': '5px',
            'color': '#f5f5f5',
            'backgroundColor': '#1e1e1e'
        }
        header = {'backgroundColor': '#0B3D91', 'color': 'white'}

    elif theme == 'orange':
        base_style = {
            'backgroundColor': '#fff8f0',
            'color': '#e67e22',
            'fontFamily': 'Arial, sans-serif',
            'padding': '20px'
        }
        cell = {'textAlign': 'center', 'padding': '5px', 'color': '#222222', 'backgroundColor': '#fff8f0'}
        header = {'backgroundColor': '#e67e22', 'color': 'white'}

    else:
        base_style = {
            'backgroundColor': '#ffffff',
            'color': '#222222',
            'fontFamily': 'Arial, sans-serif',
            'padding': '20px'
        }
        cell = {'textAlign': 'center', 'padding': '5px', 'color': '#222222', 'backgroundColor': 'white'}
        header = {'backgroundColor': '#0B3D91', 'color': 'white'}

    # IMPORTANT: on renvoie theme_attr (light/dark/orange)
    return base_style, cell, header, theme_attr, cell, header

@app.callback(
    Output("theme-store", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-store", "data")
)
def toggle_theme(n, current_theme):
    themes = ['clair', 'sombre', 'orange']
    i = themes.index(current_theme)
    return themes[(i + 1) % len(themes)]

@app.callback(
    Output('graph-requetes', 'figure'),
    [Input('keyword-input', 'value'),
     Input('dropdown-pays', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date'),
     Input('theme-store', 'data')]
)
def update_requete_graph(keyword, selected_pays, start_date, end_date,theme):
    if 'data' not in uploaded_data_store:
        return {}

    df = uploaded_data_store['data'].copy()

    # on accepte plusieurs noms possibles
    col_query_candidates = ["requête", "requete", "query", "requêtes_les_plus_fréquentes"]
    query_col = next((c for c in col_query_candidates if c in df.columns), None)

    if query_col is None or "nombre_clics" not in df.columns or "pays" not in df.columns or "date" not in df.columns:
        return {}

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    if not start_date or not end_date or not selected_pays:
        return {}

    f = df[
        (df['pays'] == selected_pays) &
        (df['date'] >= pd.to_datetime(start_date)) &
        (df['date'] <= pd.to_datetime(end_date))
    ]

    if f.empty:
        return {}

    if keyword:
        k = keyword.lower().strip()
        f = f[f[query_col].astype(str).str.lower().str.contains(k, na=False)]

    g = f.groupby(query_col, as_index=False)["nombre_clics"].sum().sort_values("nombre_clics", ascending=False).head(10)

    fig = px.bar(
        g,
        x=query_col,
        y="nombre_clics",
        title="Top 10 requêtes (filtrées)",
        labels={query_col: "Requête", "nombre_clics": "Clics"}
    )
    fig.update_layout(transition_duration=400)
    fig = style_plotly_figure(fig, theme)
    return fig

@app.callback(
    Output('graph-carte-monde', 'figure'),
    [Input('dropdown-pays', 'value'),
     Input('projection-dropdown', 'value'),
     Input('theme-store', 'data')] 
)
def update_world_map(selected_pays, projection,theme):
    if 'data' not in uploaded_data_store:
        return {}

    df = uploaded_data_store['data'].copy()

    if "pays" not in df.columns or "nombre_clics" not in df.columns:
        return {}

    # 🔹 Convertir pays → ISO-3
    def country_to_iso3(name):
        try:
            return pycountry.countries.lookup(name).alpha_3
        except:
            return None

    df["iso3"] = df["pays"].apply(country_to_iso3)

    df_grouped = (
        df.dropna(subset=["iso3"])
          .groupby("iso3", as_index=False)["nombre_clics"]
          .sum()
    )

    fig = px.choropleth(
        df_grouped,
        locations="iso3",
        locationmode="ISO-3",
        color="nombre_clics",
        color_continuous_scale="Blues",
        title="Clics par pays (toutes périodes)"
    )

    fig.update_geos(projection_type=projection)
    fig.update_layout(transition_duration=500)
    fig = style_plotly_figure(fig, theme)
    return fig
@app.callback(
    Output("download-pdf", "data"),
    Input("btn-export-pdf", "n_clicks"),
    [State('kpi-clics', 'children'),
     State('kpi-impressions', 'children'),
     State('kpi-ctr', 'children'),
     State('kpi-position', 'children')],
    prevent_initial_call=True
)
def export_pdf(n_clicks, clics, impressions, ctr, pos):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "Résumé des KPIs - Dashboard Michelin")

    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Total des clics : {clics}")
    c.drawString(100, 730, f"Impressions totales : {impressions}")
    c.drawString(100, 710, f"CTR moyen : {ctr}")
    c.drawString(100, 690, f"Position moyenne : {pos}")

    c.drawString(100, 640, "Date d'export : " + pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"))

    c.showPage()
    c.save()

    buffer.seek(0)
    return dcc.send_bytes(buffer.getvalue(), "resume_dashboard.pdf")

@app.callback(
    [Output('log-store', 'data'),
     Output('log-container', 'children')],
    [Input('btn-upload-clear', 'n_clicks'),
     Input('btn-save-upload', 'n_clicks'),
     Input('theme-toggle', 'n_clicks')],
    [State('log-store', 'data')]
)
def update_log(clear_clicks, save_clicks, theme_clicks, logs):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    action = ctx.triggered[0]['prop_id'].split('.')[0]
    new_entry = ""

    if action == 'btn-upload-clear':
        new_entry = " Fichier supprimé"
    elif action == 'btn-save-upload':
        new_entry = " Fichier modifié téléchargé"
    elif action == 'theme-toggle':
        new_entry = " Thème changé"

    if new_entry:
        logs.append(f"{pd.Timestamp.now().strftime('%H:%M:%S')} – {new_entry}")

    return logs, [html.Li(log) for log in reversed(logs[-20:])]  # max 20 dernières actions

@app.callback(
    Output("dashboard-content", "style"),
    Input("table-upload", "data")
)
def show_hide_dashboard(table_data):
    if not table_data:
        return {"display": "none"}
    return {"display": "block"}

#  Lancement de l'application
if __name__ == '__main__':
    app.run(debug=True)
