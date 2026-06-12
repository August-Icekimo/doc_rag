from storage import VectorStore, collection_name_for

def build_vector_index(chunks, doc_id):
    safe_doc_id = str(doc_id).replace(" ", "_").replace("(", "-").replace(")", "-")
    collection_name = collection_name_for(safe_doc_id)

    seen_ids = set()
    unique_ids = []
    unique_documents = []
    unique_metadatas = []

    for chunk in chunks:
        c_id = chunk["id"]
        if c_id in seen_ids:
            continue

        seen_ids.add(c_id)
        unique_ids.append(c_id)
        unique_documents.append(chunk["text"])
        unique_metadatas.append(chunk["metadata"])

    if unique_ids:
        # 🌟 使用 upsert：相同的 chunk ID 寫入時會自動更新（覆蓋）而不會發生 ID 衝突報錯
        store = VectorStore()
        store.upsert(
            collection_name,
            ids=unique_ids,
            documents=unique_documents,
            metadatas=unique_metadatas
        )

    return len(unique_ids)
