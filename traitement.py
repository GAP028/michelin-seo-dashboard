import pandas as pd
import sqlite3

#  Définition des fichiers CSV à traiter
files = {
    "Appareils": "Appareils.csv",
    "Apparence_Resultats": "Apparence dans les résultats de recherche.csv",
    "Dates": "Dates.csv",
    "Filtres": "Filtres.csv",
    "Pages": "Pages.csv",
    "Pays": "Pays.csv",
    "Requetes": "Requêtes.csv"
}

#  Chargement et nettoyage des données
dataframes = {}
for name, path in files.items():
    try:
        df = pd.read_csv(path, encoding="utf-8", sep=",")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin1", sep=",")
    except Exception as e:
        print(f"Erreur lors de la lecture de {name}: {e}")
        continue
    
    # Standardisation des noms de colonnes
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    
    # Stockage des DataFrames nettoyés
    dataframes[name] = df

#  Connexion SQLite
db_path = "search_data.db"
conn = sqlite3.connect(db_path)

#  Répartition équilibrée des pays sur plusieurs dates
df_dates = dataframes["Dates"]
df_pays = dataframes["Pays"]

# Vérification des colonnes
if 'nombre_clics' not in df_dates.columns:
    df_dates.rename(columns={'clics': 'nombre_clics'}, inplace=True)

# Normalisation des données
liste_pays = df_pays['pays'].unique()
nb_dates = len(df_dates)

df_expanded = pd.DataFrame()
for pays in liste_pays:
    subset = df_dates.sample(n=min(10, nb_dates), replace=True)  # Prendre 10 dates aléatoires par pays
    subset['pays'] = pays
    df_expanded = pd.concat([df_expanded, subset], ignore_index=True)

# Stocker les données dans la base SQLite
df_expanded.to_sql("pays_dates", conn, if_exists="replace", index=False)

conn.close()
print(" Nettoyage et répartition des données terminés !")
