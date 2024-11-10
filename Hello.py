# TODO internalizar static GTFS

import streamlit as st
from streamlit.logger import get_logger
LOGGER = get_logger(__name__)

# Import
import requests
import pandas as pd
from google.transit import gtfs_realtime_pb2
import folium
from folium.map import FeatureGroup
from streamlit_folium import st_folium
#from gtfs_functions import Feed
from datetime import datetime, timedelta
import gtfs_realtime_pb2  # Generated from gtfs-realtime.proto

from shapely import wkt
import geopandas as gpd

def geometry_column():
  df['geometry'] = df['geometry'].apply(wkt.loads)
  gdf = gpd.GeoDataFrame(df, geometry='geometry')
  return gdf

now = datetime.now() #- timedelta(hours=1, minutes=0)
formated_now = now.strftime("%H:%M:%S")

@st.cache_resource
def get_realtime_gtfs():
  feed_url = 'https://gateway.carris.pt/gateway/gtfs/api/v2.11/GTFS/realtime/vehiclepositions'
  response = requests.get(feed_url, allow_redirects=True)
  feed = gtfs_realtime_pb2.FeedMessage()
  feed.ParseFromString(response.content)
  return feed

@st.cache_data
def organize_gtfs(feed):
  vehicle_positions = []
  for entity in feed.entity:
      if entity.HasField('vehicle'):
          vehicle_positions.append({
              'trip_id': entity.vehicle.trip.trip_id,
              'route_id': entity.vehicle.trip.route_id,
              'vehicle_id': entity.vehicle.vehicle.id,
              'latitude': entity.vehicle.position.latitude,
              'longitude': entity.vehicle.position.longitude,
              'timestamp': pd.to_datetime(entity.vehicle.timestamp, unit='s'),
              'current_stop_sequence': entity.vehicle.current_stop_sequence,
              'stop_id': entity.vehicle.stop_id,
              'current_status': entity.vehicle.current_status,
          })
  vehicle_positions_df = pd.DataFrame(vehicle_positions)
  return vehicle_positions_df

def mapasimples(df):
  m = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=13, tiles='CartoDB dark_matter')
  html = f"""<div><svg><circle cx="5" cy="5" r="2" fill=yellow opacity=".8"/></svg></div>"""
  for idx, row in df.iterrows():
      folium.Marker([row['latitude'], row['longitude']], icon=folium.DivIcon(html=html)
      ).add_to(m)
  return m

@st.cache_data
def get_static_feed():
  static_gtfs = 'https://gateway.carris.pt/gateway/gtfs/api/v2.11/GTFS/'
  time_windows = list(range(24))
  static_feed = Feed(static_gtfs, time_windows=time_windows)
  return static_feed

#def get_route_short_name(df):
  
def obter_carreiras(df): #Se não for usar lista predefinida
    grouped = df.groupby('route_short_name')
    carreiras = []
    for name, group in grouped:
        carreiras.append(name)
    return carreiras

def join_static(vehicle_positions_df, static_feed):
  routes = static_feed.routes
  trips = static_feed.trips
  shapes = static_feed.shapes
  vehicle_positions_df_plus = vehicle_positions_df.merge(routes[['route_id', 'route_short_name', 'route_long_name']], on='route_id')
  vehicle_positions_df_plus = vehicle_positions_df_plus.merge(trips[['trip_id', 'direction_id', 'shape_id']], on='trip_id')
  vehicle_positions_df_plus = vehicle_positions_df_plus.merge(shapes, on='shape_id')
  return vehicle_positions_df_plus

def join_static_filtro_pre(df, linha_selec='742', sentido_selec=0):
  routes = pd.read_csv('routes.txt', sep=',') #/workspaces/ondeestaacarris/
  trips =  pd.read_csv('trips.txt', sep=',')
  shapes = pd.read_csv('shapesid.csv', sep=',')

  routes = routes[routes['route_short_name'] == linha_selec]
  df = df.merge(routes[['route_id', 'route_short_name', 'route_long_name']], on='route_id')
  
  trips = trips[trips['direction_id'] == sentido_selec]
  df = df.merge(trips[['trip_id', 'direction_id', 'shape_id']], on='trip_id')
  
  df = df.merge(shapes, on='shape_id')
  df['geometry'] = df['geometry'].apply(wkt.loads)
  
  return df

@st.cache_data
def lastseen(df):
  df['now'] = now
  df['last_seen'] = (df['now'] - df['timestamp']).dt.total_seconds()/60
  df['last_seen_txt'] = df['last_seen'].apply(lambda x: f"{x:.1f}")
  df['last_seen_tooltip'] = df['last_seen_txt'].apply(lambda x: f"Last seen {x} minutes ago")
  return df

def filtro_pre(df, linha_selec, sentido_selec):
    df = df[df['route_short_name'] == linha_selec]
    df = df[df['direction_id'] == sentido_selec] 
    return df

def mapalinha(df):
  m = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=13, tiles='CartoDB dark_matter')
  html = f"""<div><svg><circle cx="5" cy="5" r="4" fill=yellow opacity=".8"/></svg></div>"""
  # Add markers for each vehicle
  for idx, row in df.iterrows():
      folium.Marker([row['latitude'], row['longitude']], icon=folium.DivIcon(html=html), tooltip=(row['last_seen_tooltip']) #tooltip=('last seen at: '+row['timestamp'].astype(str)
      ).add_to(m) #completar TOOLTIP
  # Add each bus line
  for line in df['geometry']:
          folium.PolyLine([(p[1], p[0]) for p in line.coords], color='#17365D', weight=2.5).add_to(m)
  return m

def mapalinhafiltro_og(df):
    grouped = df.groupby('route_short_name')

    m = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], 
                zoom_start=13, 
                tiles='CartoDB dark_matter')

    html = """<div><svg><circle cx="5" cy="5" r="4" fill="yellow" opacity=".8"/></svg></div>"""

    # Loop through each group to create separate layers
    for name, group in grouped:
        fg = FeatureGroup(name=name, show=False)  # Set show=False to hide layers by default

        # Add markers for each vehicle in this line
        for idx, row in group.iterrows():
            folium.Marker(
                [row['latitude'], row['longitude']], 
                icon=folium.DivIcon(html=html), 
                tooltip=row['last_seen_tooltip']
            ).add_to(fg)

        # Add polyline for the bus line, assuming 'geometry' is a LineString in Shapely format
        if hasattr(group.iloc[0]['geometry'], 'coords'):
            folium.PolyLine(
                [(p[1], p[0]) for p in group.iloc[0]['geometry'].coords], 
                color='#17365D', 
                weight=2.5
            ).add_to(fg)
        
        fg.add_to(m)

    # Add Layer Control to toggle bus lines
    folium.LayerControl().add_to(m)

    return m

#carreiras = obter_carreiras(df)

#linha_selec = '742'
#sentido_selec = 0

#df = filtro_pre(df, linha_selec, sentido_selec)
#mapa_linha = mapalinha(df)
#mapa_linha = mapalinhafiltro_og(df)

carreiras = ['12E', '13B', '15E', '17B', '18E', '19B', '22B', '24E', '25E', '26B', '28E', '29B', '31B', '32B', '34B', '37B', '40B', '41B', '43B', '44B', '46B', '49B', '52B', '55B', '58B', '61B', '67B', '701', '702', '703', '705', '706', '708', '709', '70B', '711', '712', '713', '714', '716', '717', '718', '720', '722', '723', '724', '725', '726', '727', '728', '729', '730', '731', '732', '734', '735', '736', '738', '73B', '742', '744', '746', '747', '748', '749', '750', '751', '753', '754', '755', '756', '758', '759', '760', '764', '765', '767', '768', '76B', '770', '771', '773', '774', '776', '778', '781', '782', '783', '793', '794', '796', '797', '798', '799', '79B']
sentidos = [0, 1]

def run():
    #st.set_page_config(
    #    page_title="Onde está o meu autocarro?",
    #    page_icon="👋",
    #)

    st.write("# Onde está o meu autocarro?")
    st.markdown(f"""
      Localizações dos autocarros da Carris em tempo real.
      Obtidas às {formated_now}
      """
    )

    linha_selec = st.selectbox("Escolhe a carreira", options=carreiras, index=carreiras.index("742"))
    sentido_selec = st.selectbox("Escolhe o sentido", options=sentidos, index=sentidos.index(0))

    feed = get_realtime_gtfs()
    df = organize_gtfs(feed)
    # #mapa_simp = mapasimples(df)
    static_feed = get_static_feed()
    #df = join_static(df, static_feed)
    df = join_static_filtro_pre(df, linha_selec, sentido_selec)
    df = lastseen(df)

    #df = filtro_pre(df, linha_selec, sentido_selec)

    mapa_linha = mapalinha(df)

    st_data = st_folium(mapa_linha, width=800, returned_objects=[])

if __name__ == "__main__":
    run()
