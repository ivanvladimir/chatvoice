from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

#from  config import get_config

#Este archivo sirve para crear la base de datos
#Hay que que correr el script en un entorno virtual que tenga instalado el paquete qdrant-client

client = QdrantClient("localhost", port=6333)

client.create_collection(
    collection_name="face_descriptor",
    vectors_config=VectorParams(size=128, distance=Distance.EUCLID),
)