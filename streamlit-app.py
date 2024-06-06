############################################## Imports ##############################################
# Importation des bibliothèques nécessaires
import streamlit as st  # Pour créer l'application web
import requests  # Pour effectuer des requêtes HTTP
import pandas as pd  # Pour la manipulation des données
from pyquery import PyQuery as pq  # Pour le parsing HTML
import folium  # Pour créer des cartes interactives
from geopy.geocoders import Nominatim  # Pour la géolocalisation
from geopy.extra.rate_limiter import RateLimiter  # Pour limiter le taux des requêtes à l'API de géolocalisation
from streamlit_folium import st_folium  # Pour intégrer Folium avec Streamlit
import re  # Pour les expressions régulières
import matplotlib.pyplot as plt  # Pour créer des graphiques
#####################################################################################################

# Titre de l'application
st.title("Devoir Python de fin d'année - M2 MSSI - Juliette Frédy")
# En-tête de l'application avec une description
st.header("Bienvenue sur mon application streamlit ! Ici, vous pourrez visualiser une carte avec les espaces de coworking situés à Paris. Vous pourrez également visualiser des graphiques analysant certaines données des espaces de coworking.", divider='rainbow')

# Fonction pour récupérer les liens des espaces de coworking à Paris
def url_coworking(main_url):
    # Faire une requête HTTP pour obtenir le contenu de la page
    response = requests.get(main_url)
    html_content = response.text
    # Utiliser PyQuery pour parser le contenu HTML
    doc = pq(html_content)
    # Extraire les URLs contenant le mot "paris"
    url_coworking_paris = [a.attr('href') for a in doc('a[href*=paris]').items()]
    return url_coworking_paris

# URL principale des espaces de coworking
main_url = "https://www.leportagesalarial.com/coworking/"
# Récupération des liens des espaces de coworking à Paris
url_coworking_paris = url_coworking(main_url)
# Création d'un DataFrame avec les URLs des espaces de coworking
data = {'URL_Coworking_Paris': url_coworking_paris}
df = pd.DataFrame(data)

# Fonction pour extraire les informations des espaces de coworking
def extract_coworking_info(url):
    # Faire une requête HTTP pour obtenir le contenu de la page
    response = requests.get(url)
    if response.status_code == 200:
        html = response.text
        # Utiliser PyQuery pour parser le contenu HTML
        doc = pq(html)
        # Extraire les différentes informations
        name = doc('h1').text().split(':')[0].strip()
        adresse = doc('li:contains("Adresse")').text().replace('Adresse :', '').strip()
        # Utiliser une expression régulière pour trouver le code postal
        code_postal_match = re.search(r'\b\d{2}\s*\d{3}\b', adresse)
        code_postal = code_postal_match.group().replace(" ", "") if code_postal_match else None
        description = doc('h2:contains("Présentation de")').nextAll('p').text()
        téléphone = doc('li:contains("Téléphone")').text().replace('Téléphone : ', '').strip()
        access_elements = doc('li:contains("Accès :")')
        # Extraire et nettoyer les informations d'accès
        accesses = [pq(el).text().replace('Accès : ', '').strip() for el in access_elements]
        accès = ', '.join(accesses)
        site = doc('li:contains("Site") a').attr('href')
        twitter = doc('li:contains("Twitter") a').attr('href')
        facebook = doc('li:contains("Facebook") a').attr('href')
        linkedin = doc('li:contains("LinkedIn") a').attr('href')
        # Retourner les informations sous forme de dictionnaire
        return {
            'url': url,
            'name': name,
            'adresse': adresse,
            'code postal': code_postal,
            'description': description,
            'téléphone': téléphone,
            'accès': accès,
            'site': site,
            'twitter': twitter,
            'facebook': facebook,
            'linkedin': linkedin,
        }
    else:
        st.error(f"Erreur lors de la récupération de {url}")
        return None

# Fonction pour nettoyer l'adresse
def clean_address(adresse):
    # Utiliser une expression régulière pour corriger les espaces dans les codes postaux français
    adresse = re.sub(r'(\d{2})\s(\d{3})', r'\1\2', adresse)
    return adresse

# Extraction des informations des espaces de coworking
coworking_data = []
for url in df['URL_Coworking_Paris']:
    # Extraire les informations pour chaque URL
    info = extract_coworking_info(url)
    if info:
        coworking_data.append(info)

# Mise à jour du DataFrame avec les informations extraites
df = pd.DataFrame(coworking_data)

# Ajouter des colonnes pour les coordonnées géographiques
df['latitude'] = None
df['longitude'] = None

# Fonction pour obtenir les coordonnées géographiques
geolocator = Nominatim(user_agent="coworking_locator")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# Obtenir les coordonnées géographiques pour chaque adresse
for index, row in df.iterrows():
    try:
        cleaned_address = clean_address(row['adresse'])
        location = geocode(cleaned_address)
        if location:
            df.at[index, 'latitude'] = location.latitude
            df.at[index, 'longitude'] = location.longitude
    except Exception as e:
        st.error(f"Erreur lors de la géolocalisation de l'adresse: {row['adresse']} - {e}")

# Créer une carte Folium avec les tuiles OpenStreetMap
map_coworking = folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles='OpenStreetMap')

# Ajouter des marqueurs pour chaque espace de coworking sur la carte
for index, row in df.iterrows():
    if pd.notna(row['latitude']) and pd.notna(row['longitude']):
        popup_content = f"""
        <b>{row['name']}</b><br>
        Adresse: {row['adresse']}<br>
        Téléphone: {row['téléphone']}<br>
        Accès: {row['accès']}<br>
        Description: {row['description']}<br>
        <a href="{row['site']}" target="_blank">Lien vers la page</a>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=row['name']
        ).add_to(map_coworking)

# Afficher la carte dans l'application Streamlit
st.header("Carte des Espaces de Coworking à Paris")
st_folium(map_coworking)

# Sauvegarder les données dans un fichier Excel
excel_path = "coworking_data.xlsx"
df.to_excel(excel_path, index=False)
st.success(f"Les données ont été sauvegardées dans le fichier Excel à l'emplacement : {excel_path}")
st.header("", divider='rainbow')

############################# Créer un histogramme du nombre de coworking par code postal #############################
st.header("Nombre de coworking par code postal à Paris")
plt.figure(figsize=(10, 6))
# Créer un histogramme du nombre de coworking par code postal
df['code postal'].value_counts().plot(kind='bar')
plt.title('Nombre de coworking par code postal à Paris')
plt.xlabel('Code postal')
plt.ylabel('Nombre de coworking')
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid()
# Afficher le graphique dans l'application Streamlit
st.pyplot(plt)
st.header("Ce graphique montre le nombre d'espaces de coworking disponibles par arrondissement.", divider='rainbow')

############################# Créer un histogramme du nombre de dessertes de transport par lieu de coworking #############################
st.header('Nombre de dessertes pour chaque espace de coworking')
plt.figure(figsize=(10, 6))
noms_coworking = []
dessertes = []

# Fonction pour compter les dessertes
def count_dessertes(accès):
    if pd.isna(accès) or accès.strip() == '':
        return 0
    else:
        # Supprimer les parenthèses et leur contenu, et normaliser les séparateurs
        accès = re.sub(r'\([^)]+\)', '', accès).strip()
        accès = re.sub(r',\s*(et|ou)\s*', ',', accès)
        dessertes_list = [item.strip() for item in accès.split(',') if item.strip()]
        return len(dessertes_list)

# Compter les dessertes pour chaque espace de coworking
for index, row in df.iterrows():
    nom_coworking = row['name']
    noms_coworking.append(nom_coworking)
    nb_dessertes = count_dessertes(row['accès'])
    dessertes.append(nb_dessertes)

# Créer un histogramme du nombre de dessertes pour chaque espace de coworking
plt.bar(noms_coworking, dessertes, color='skyblue')
plt.title('Nombre de dessertes pour chaque espace de coworking')
plt.xlabel('Espace de coworking')
plt.ylabel('Nombre de dessertes')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
# Afficher le graphique dans l'application Streamlit
st.pyplot(plt)
st.header("Ce graphique montre le nombre de dessertes (accès métro) par espaces de coworking.", divider='rainbow')

############################# Créer un histogramme du nombre de réseaux sociaux par lieu de coworking #############################
st.header('Nombre de réseaux sociaux pour chaque espace de coworking')
plt.figure(figsize=(10, 6))
noms_coworking = []
reseaux_sociaux = []

# Compter les réseaux sociaux pour chaque espace de coworking
for index, row in df.iterrows():
    nom_coworking = row['name']
    noms_coworking.append(nom_coworking)
    # Compter les réseaux sociaux disponibles
    nb_reseaux_sociaux = sum(not pd.isnull(row[réseau]) for réseau in ['twitter', 'facebook', 'linkedin'])
    reseaux_sociaux.append(nb_reseaux_sociaux)

# Créer un histogramme du nombre de réseaux sociaux pour chaque espace de coworking
plt.bar(noms_coworking, reseaux_sociaux, color='lightgreen')
plt.title('Nombre de réseaux sociaux pour chaque espace de coworking')
plt.xlabel('Espace de coworking')
plt.ylabel('Nombre de réseaux sociaux')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
# Afficher le graphique dans l'application Streamlit
st.pyplot(plt)
st.header("Ce graphique met en évidence le nombre de réseaux sociaux disponibles par espace de coworking.", divider='rainbow')
