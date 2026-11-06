from pathlib import Path

import pandas as pd
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"

st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")


@st.cache_data
def lire_donnees() -> pd.DataFrame:
    """Charge le jeu de données nettoyé par le notebook."""
    return pd.read_csv(DOSSIER / "consommation_propre.csv")


donnees = lire_donnees()
communes = sorted(donnees["commune"].unique())
annees = sorted(donnees["annee"].unique())

st.markdown(
    "Ce tableau de bord analyse la consommation d'électricité de 12 quartiers "
    "et la compare aux heures de courant et à la température."
)
st.markdown(
    "Les données affichées ont été nettoyées et enrichies dans le notebook "
    "`exploration.ipynb`."
)

st.sidebar.header("Filtres")
communes_choisies = st.sidebar.multiselect(
    "Communes",
    options=communes,
    default=communes,
)
annee_choisie = st.sidebar.selectbox(
    "Année",
    options=annees,
    index=annees.index(2025) if 2025 in annees else len(annees) - 1,
)

selection = donnees[donnees["commune"].isin(communes_choisies)]
filtrees = selection[selection["annee"] == annee_choisie]

if not communes_choisies:
    st.info("Choisissez au moins une commune pour afficher les résultats.")
else:
    total_kwh = int(filtrees["kwh"].sum())
    kwh_par_abonne = float(filtrees["kwh_par_abonne"].mean())
    heures_moyennes = float(filtrees["heures_courant"].mean())

    col1, col2, col3 = st.columns(3)
    col1.metric("Consommation totale", f"{total_kwh / 1_000_000:.2f} M kWh")
    col2.metric("kWh par abonné et par mois", f"{kwh_par_abonne:.1f}")
    col3.metric("Heures de courant par jour", f"{heures_moyennes:.1f} h")

    onglets = st.tabs(
        [
            "Quartiers et abonnés",
            "Évolution par commune",
            "Chaleur ou courant ?",
            "Coupures",
            "Relevés remarquables",
        ]
    )

    with onglets[0]:
        st.subheader("Quels quartiers consomment le plus par abonné ?")
        par_quartier = (
            selection[selection["annee"] == annee_choisie]
            .groupby(["quartier", "type"], as_index=False)["kwh_par_abonne"]
            .mean()
            .sort_values("kwh_par_abonne", ascending=False)
        )
        st.bar_chart(par_quartier, x="quartier", y="kwh_par_abonne", color="type")
        st.write(
            f"Pour {annee_choisie}, la consommation mensuelle moyenne par abonné "
            f"est de {filtrees.groupby('type')['kwh_par_abonne'].mean().round(1).to_dict()} "
            "kWh selon le type de quartier."
        )

    with onglets[1]:
        st.subheader("Comment la consommation évolue-t-elle par commune ?")
        evolution = (
            selection[selection["annee"] == annee_choisie]
            .groupby(["mois", "commune"], as_index=False)
            .agg(kwh_par_abonne=("kwh_par_abonne", "mean"))
            .sort_values("mois")
        )
        st.line_chart(evolution, x="mois", y="kwh_par_abonne", color="commune")
        totaux = selection.pivot_table(
            index="commune", columns="annee", values="kwh", aggfunc="sum"
        )
        if {2024, 2025}.issubset(totaux.columns):
            variations = (totaux[2025] / totaux[2024] - 1) * 100
            commune_max = variations.idxmax()
            st.write(
                f"Entre 2024 et 2025, la hausse la plus forte est à "
                f"{commune_max} ({variations[commune_max]:.1f} %)."
            )

    with onglets[2]:
        st.subheader("La consommation suit-elle la chaleur ou les heures de courant ?")
        residentiel = selection[
            selection["type"].str.startswith("R")
        ]
        points = residentiel[residentiel["annee"] == annee_choisie]
        st.scatter_chart(
            points,
            x="heures_courant",
            y="kwh_par_abonne",
            color="commune",
        )
        correlations = residentiel[
            ["kwh_par_abonne", "heures_courant", "temperature_c"]
        ].corr()["kwh_par_abonne"]
        st.write(
            f"Sur les quartiers résidentiels, la corrélation est de "
            f"{correlations['heures_courant']:.2f} avec les heures de courant "
            f"et de {correlations['temperature_c']:.2f} avec la température."
        )

    with onglets[3]:
        st.subheader("Où les coupures sont-elles les plus longues ?")
        heures = (
            selection.groupby("commune")["heures_courant"]
            .agg(médiane="median", Q1=lambda valeurs: valeurs.quantile(0.25), Q3=lambda valeurs: valeurs.quantile(0.75))
            .sort_values("médiane")
        )
        st.bar_chart(heures)
        rares = selection[
            (selection["annee"] == 2025) & (selection["heures_courant"] < 8)
        ]
        st.write(
            f"En 2025, {len(rares)} relevés indiquent moins de 8 heures de courant : "
            f"{', '.join(rares['quartier'].tolist()) or 'aucun'}."
        )

    with onglets[4]:
        st.subheader("Quels relevés sortent du lot ?")
        remarquables = selection.nlargest(3, "kwh")[
            ["mois", "quartier", "type", "kwh"]
        ]
        st.bar_chart(remarquables, x="quartier", y="kwh", color="type")
        st.dataframe(remarquables, hide_index=True)

    st.markdown(
        """
        ### Conclusion

        Dans les quartiers résidentiels, la consommation par abonné est davantage
        associée aux heures de courant (corrélation de 0,76) qu'à la température
        (−0,15). Cette association ne prouve pas que les heures de courant causent
        à elles seules la consommation : une corrélation ne démontre pas la causalité.
        """
    )

    with st.expander("Afficher les données filtrées"):
        st.dataframe(filtrees, hide_index=True)
