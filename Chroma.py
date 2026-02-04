!git clone https://github.com/chroma-core/chroma.git

%cd chroma

!pip install chromadb

import chromadb

client = chromadb.Client()


collection = client.create_collection(name="demo_lim")

collection.add(
    documents=[
        "Chroma es una base de datos de embeddings open-source",
        "Se utiliza para búsqueda semántica en aplicaciones con LLM",
        "Es útil para sistemas RAG y chatbots inteligentes",
        "Permite encontrar información por significado y no por palabras exactas"
    ],
    ids=["1","2","3","4"]
)

print("Base de datos cargada correctamente")

pregunta = input("Escribe tu pregunta sobre Chroma: ")

# Consulta semántica
resultado = collection.query(
    query_texts=[pregunta],
    n_results=1
)

print("\n🔎 Resultado más relevante:")
print(resultado["documents"][0][0])
