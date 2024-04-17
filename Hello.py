import streamlit as st
from streamlit.logger import get_logger
LOGGER = get_logger(__name__)

import biogeme
from google.transit import gtfs_realtime_pb2

feed_url = 'https://gateway.carris.pt/gateway/gtfs/api/v2.11/GTFS/realtime/vehiclepositions'
response = requests.get(feed_url, allow_redirects=True)
feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

def run():
    st.set_page_config(
        page_title="Hello",
        page_icon="👋",
    )

    st.write("# Onde está (o meu autocarro d')a Carris?")

    st.sidebar.success("Select a demo above.")

    st.markdown(
      """
      Oi
      """
    )


if __name__ == "__main__":
    run()
