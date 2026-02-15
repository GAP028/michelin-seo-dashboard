import dash
from dash import dcc, html, dash_table
import pandas as pd
import plotly.express as px
import sqlite3
from dash.dependencies import Input, Output, State
import io
import base64

DB_PATH = "search_data.db"

def get_data():
    conn = sqlite3.connect(DB_PATH)
    df_main = pd.read_sql_query("SELECT * FROM pays_dates", conn)
    try:
        df_appareils = pd.read_sql_query("SELECT * FROM appareils", conn)
    except:
        df_appareils = pd.DataFrame()
    try:
        df_requetes = pd.read_sql_query("SELECT * FROM requêtes", conn)
    except:
        df_requetes = pd.DataFrame()
    conn.close()
    df_main['date'] = pd.to_datetime(df_main['date'], errors='coerce')
    df_main = df_main.sort_values(by=['pays', 'date'])
    return df_main, df_appareils, df_requetes

df_dates, df_appareils, df_requetes = get_data()

app = dash.Dash(__name__)
server = app.server
app.title = "Michelin Dashboard"

uploaded_data_store = {}

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


app.layout = html.Div(id="main-container", style={'fontFamily': 'Arial, sans-serif', 'margin': '20px'}, children=[
    dcc.Store(id="theme-store", data="clair"),  # ← thème par défaut
     html.H1("Dashboard Michelin - Marché Mexicain", style={'textAlign': 'center', 'color': '#0B3D91'}),
      html.Button("Changer de thème", id='theme-toggle', n_clicks=0, style={
        'margin': '10px',
        'padding': '10px',
        'backgroundColor': '#e67e22',
        'color': 'white',
        'border': 'none',
        'borderRadius': '5px'
}),


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
        html.Button(" Supprimer le fichier", id='btn-upload-clear', n_clicks=0, style={'marginBottom': '10px'}),
        html.Button(" Télécharger le fichier modifié", id='btn-save-upload', n_clicks=0, style={'marginBottom': '10px'}),
        html.Button(" Exporter le Résumé en PDF", id='btn-export-pdf', n_clicks=0, style={'marginBottom': '10px'}),
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
        html.Ul(id='log-container', style={'maxHeight': '200px', 'overflowY': 'auto', 'backgroundColor': '#f4f4f4', 'padding': '10px'})
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
        html.H2("Filtres", style={'color': '#0B3D91'}),
        dcc.Dropdown(
            id='dropdown-pays',
            options=[{'label': pays, 'value': pays} for pays in df_dates['pays'].unique()],
            value=df_dates['pays'].unique()[0],
            clearable=False,
            style={'width': '50%', 'marginBottom': 10}
        ),
        dcc.DatePickerRange(
            id='date-range',
            start_date=df_dates['date'].min().date(),
            end_date=df_dates['date'].max().date(),
            display_format='YYYY-MM-DD',
            min_date_allowed=df_dates['date'].min().date(),
            max_date_allowed=df_dates['date'].max().date(),
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

    dcc.Graph(id='graph-clics'),
    dcc.Graph(id='graph-appareils',
              figure=px.pie(df_appareils, names='appareil', values='clics',
                            title='Clics par Appareil') if not df_appareils.empty else {}),
        html.Div([
            html.Label(" Rechercher un mot-clé :", style={'color': '#0B3D91', 'fontWeight': 'bold'}),
            dcc.Input(
                id='keyword-input',
                type='text',
                placeholder='Entrez un mot-clé...',
                debounce=True,  # pour éviter trop d'appels
                style={'marginBottom': '15px', 'width': '50%', 'padding': '10px'}
            ),
        ]),

    dcc.Graph(id='graph-requetes',
              figure=px.bar(df_requetes.sort_values(by='clics', ascending=False).head(10),
                            x='requêtes_les_plus_fréquentes', y='clics',
                            title='Top 10 Requêtes les plus fréquentes') if not df_requetes.empty else {}),
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
                                value='orthographic',  # valeur par défaut
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
            columns=[{"name": col, "id": col} for col in df_dates.columns],
            data=df_dates.to_dict('records'),
            editable=False,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'center', 'padding': '5px'},
            style_header={'backgroundColor': '#0B3D91', 'color': 'white'}
        )
    ])
]
# Mémoire temporaire pour fichier téléversé
uploaded_data_store = {}

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
        uploaded_data_store.clear()
        return html.Div(" Fichier supprimé."), [], []

    if contents:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            df_uploaded = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            uploaded_data_store['data'] = df_uploaded
            return html.Div([
                html.H5(f" Fichier {filename} chargé avec succès."),
                html.P(" Vous pouvez modifier les données dans le tableau.")
            ]), [{"name": col, "id": col} for col in df_uploaded.columns], df_uploaded.to_dict('records')
        except Exception as e:
            return html.Div([
                html.H5(" Erreur de lecture du fichier :"),
                html.Pre(str(e), style={'color': 'red'})
            ]), [], []

    return "", [], []

@app.callback(
    Output("download-modified-upload", "data"),
    Input("btn-save-upload", "n_clicks"),
    State("table-upload", "data"),
    prevent_initial_call=True,
)
def download_modified(n_clicks, table_data):
    if not table_data or len(table_data) == 0:
        return dcc.send_string(" Aucun fichier à télécharger. Veuillez d'abord téléverser et modifier un fichier.")
    df = pd.DataFrame(table_data)
    return dcc.send_data_frame(df.to_csv, "fichier_modifié.csv", index=False)
@app.callback(
    [Output('kpi-clics', 'children'),
     Output('kpi-impressions', 'children'),
     Output('kpi-ctr', 'children'),
     Output('kpi-position', 'children'),
     Output('graph-clics', 'figure'),
     Output('graph-correlation', 'figure'),
     Output('table-dates', 'data'),
     Output('error-message', 'children')],
    [Input('dropdown-pays', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date')]
)
def update_dashboard(selected_pays, start_date, end_date):
    default_style = {'display': 'none'}
    error_style = {
        'color': 'white',
        'backgroundColor': '#e74c3c',
        'padding': '10px',
        'marginBottom': '20px',
        'borderRadius': '5px'
     }

    if not start_date or not end_date:
        return ["-"] * 4 + [{}] + [[]] + html.Div(" Sélectionnez une plage de dates valide.", style=error_style)

    if pd.to_datetime(start_date) > pd.to_datetime(end_date):
        return ["-"] * 4 + [{}] + [[]] + html.Div(" La date de début ne peut pas être après la date de fin.", style=error_style)

    filtered_df = df_dates[
        (df_dates['pays'] == selected_pays) &
        (df_dates['date'] >= pd.to_datetime(start_date)) &
        (df_dates['date'] <= pd.to_datetime(end_date))
    ]

    if filtered_df.empty:
        return ["-"] * 4 + [{}] + [[]] + html.Div(" Aucune donnée disponible pour cette sélection.", style=error_style)
    

    total_clics = filtered_df['nombre_clics'].sum()
    total_impressions = filtered_df['impressions'].sum()
    ctr = round((total_clics / total_impressions) * 100, 2) if total_impressions else 0
    pos = round(filtered_df['position'].mean(), 2)

    fig = px.line(
        filtered_df, x='date', y='nombre_clics',
        title=f" Évolution des clics – {selected_pays}",
        markers=True
    )
    fig.update_layout(transition_duration=500)
    fig_corr = px.scatter(
    filtered_df,
    x='position',
    y='ctr',
    size='impressions',
    color='date',
    title=" Corrélation CTR / Position Moyenne",
    labels={'ctr': 'Taux de clics (CTR)', 'position': 'Position Moyenne'}
)
    fig_corr.update_traces(marker=dict(opacity=0.6, line=dict(width=1, color='DarkSlateGrey')))

    return (
        f"{total_clics:,} clics (sur la période sélectionnée)",
        f"{total_impressions:,} impressions",
        f"{ctr} %",
        f"{pos}",
        fig,
        fig_corr,
        filtered_df.to_dict('records'),
        ""
    )
#  Callback : changer dynamiquement de thème
@app.callback(
    [Output("main-container", "style"),
     Output("table-dates", "style_cell"),
     Output("table-dates", "style_header"),
     Output("table-upload", "style_cell"),
     Output("table-upload", "style_header")],
    Input("theme-store", "data")
)
def update_theme_style(theme):
    if theme == 'sombre':
     base_style = {
        'backgroundColor': '#1e1e1e',
        'color':'red',
        'fontFamily': 'Arial, sans-serif',
        'padding': '20px'
    }
     cell = {'textAlign': 'center', 'padding': '5px', 'color': 'red', 'backgroundColor': '#1e1e1e'}
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

    return base_style, cell, header, cell, header


#  Bouton : changer de thème (tourne entre clair → sombre → orange)
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
    Input('keyword-input', 'value')
)
def update_requete_graph(keyword):
    if df_requetes.empty:
        return {}

    filtered = df_requetes.copy()

    if keyword:
        keyword_lower = keyword.lower()
        filtered = filtered[filtered['requêtes_les_plus_fréquentes'].str.lower().str.contains(keyword_lower)]

    # S’il reste peu de lignes, on affiche tout
    top = filtered.sort_values(by='clics', ascending=False).head(10)

    fig = px.bar(
        top,
        x='requêtes_les_plus_fréquentes',
        y='clics',
        title=" Top Requêtes Filtrées",
        labels={'requêtes_les_plus_fréquentes': 'Requête', 'clics': 'Nombre de clics'}
    )
    return fig
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

@app.callback(
    Output('graph-carte-monde', 'figure'),
    [Input('dropdown-pays', 'value'),
     Input('projection-dropdown', 'value')]
)

def update_world_map(selected_pays, projection):
    df_grouped = df_dates.groupby("pays", as_index=False)["nombre_clics"].sum()

    fig = px.choropleth(
        df_grouped,
        locations="pays",
        locationmode="country names",
        color="nombre_clics",
        hover_name="pays",
        color_continuous_scale="Blues",
        title=" Clics par pays (toutes périodes)"
    )
    fig.update_geos(projection_type=projection)
    fig.update_layout(transition_duration=500)
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
    [Output('dropdown-pays', 'value'),
     Output('date-range', 'start_date'),
     Output('date-range', 'end_date'),
     Output('keyword-input', 'value')],
    Input('btn-reset', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filters(n_clicks):
    # Réinitialiser aux valeurs par défaut
    pays_defaut = df_dates['pays'].unique()[0]
    date_min = df_dates['date'].min().date()
    date_max = df_dates['date'].max().date()
    return pays_defaut, date_min, date_max, ""


#  Lancement de l'application
if __name__ == '__main__':
    app.run(debug=True)
