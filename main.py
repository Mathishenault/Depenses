import streamlit as st
import pandas as pd
import os
import hashlib
from Fonctions import extraire_transactions_credit, afficher_interface_fractionnement
from Fonctions import formater_dataframe, exporter_excel
from Fonctions import extraire_transactions_compte
from Convertion import importer_donnees_automatique

# ----------- CONFIG -----------
st.set_page_config(page_title="Classification des dépenses Desjardins", layout="wide")
st.session_state.setdefault('df_base', pd.DataFrame())
st.session_state.setdefault('current_file_hash', None)

# ----------- INTERFACE -----------
def main():
    dossier_cible = r"C:\Documents\Dépenses\GitDepenses\Depenses"
    uploaded_file = st.file_uploader("Téléverse ton relevé PDF", type="pdf")
    
    # Vérifier si un nouveau fichier a été uploadé
    if uploaded_file:
        current_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        if st.session_state.current_file_hash != current_hash:
            st.session_state.current_file_hash = current_hash
            # Réinitialiser seulement si c'est un nouveau fichier
            st.session_state.df_base = pd.DataFrame()
            st.rerun()
    
    if uploaded_file and st.session_state.df_base.empty:
        # Extraction selon le type de document
        doc_type = st.radio(
            "Type de document",
            ("Carte de crédit", "Compte bancaire"),
            horizontal=True,
            key='doc_type'
        )
        
        if doc_type == "Carte de crédit":
            st.session_state.df_base = extraire_transactions_credit(uploaded_file)
        else:
            st.session_state.df_base = extraire_transactions_compte(uploaded_file)
    
    if uploaded_file and not st.session_state.df_base.empty:
        doc_type = st.session_state.get('doc_type', "Compte bancaire")
        st.write(f"**Transactions {doc_type} extraites :** {len(st.session_state.df_base)}")
        
        # Affichage des transactions avec boutons de suppression
        st.subheader("Transactions")
        for idx, row in st.session_state.df_base.iterrows():
            cols = st.columns([0.8, 0.2])
            with cols[0]:
                st.write(f"{row['Date']} - {row['Description']} (${row['Montant']})")
            with cols[1]:
                if st.button("Supprimer", key=f"del_{idx}"):
                    st.session_state.df_base = st.session_state.df_base.drop(index=idx)
                    st.rerun()
        
        st.markdown("---")
        
        # Workflow existant avec le dataframe filtré
        df_fractionne = afficher_interface_fractionnement(st.session_state.df_base)
        df_final = formater_dataframe(df_fractionne)
        st.dataframe(df_final.head())
        
        # Export
        if st.button("📤 Exporter vers Excel"):
            excel_data = exporter_excel(df_final)
            try:
                chemin_complet = os.path.join(dossier_cible, "depenses_detailles.xlsx")
                fichier_existe = os.path.exists(chemin_complet)
                with open(chemin_complet, "wb") as f:
                    f.write(excel_data)
                if fichier_existe:
                    st.success(f"✅ Fichier existant remplacé dans :\n`{chemin_complet}`")
                    importer_donnees_automatique()
                else:
                    st.success(f"📁 Nouveau fichier créé dans :\n`{chemin_complet}`")
                    importer_donnees_automatique()
            except Exception as e:
                st.warning(f"Impossible d'écrire directement. Raison : {str(e)}")
                st.info("Utilisez le bouton de téléchargement ci-dessus")

if __name__ == "__main__":
    main()