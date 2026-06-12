"""
向量資料庫抽象層。

將 chromadb 的細節（PersistentClient、collection 物件、HNSW 設定）封裝在此模組，
所有呼叫端一律以「collection 名稱 + 純資料」操作。日後更換 vector backend
（如 pgvector）時，只需改寫本檔案。
"""
import chromadb

from config.settings import CHROMADB_DIR


def collection_name_for(doc_id):
    """由 doc_id 組出 collection 名稱（全系統統一規則）。"""
    return f"collection_{doc_id}"


class VectorStore:
    def __init__(self, path=None):
        """path 預設為系統主資料庫 CHROMADB_DIR；匯入合併時可指向外部解壓目錄。"""
        self._client = chromadb.PersistentClient(path=path or CHROMADB_DIR)

    def _default_embedding(self):
        # 延遲載入，避免 import storage 時就觸發 SentenceTransformer 權重載入
        from model.embeddings import embedding_instance
        return embedding_instance

    def _collection(self, name, embedding_function=None):
        return self._client.get_collection(
            name=name,
            embedding_function=embedding_function or self._default_embedding()
        )

    # ------------------------------------------------------------------
    # Collection 管理
    # ------------------------------------------------------------------

    def list_collection_names(self):
        return [c.name for c in self._client.list_collections()]

    def has_collection(self, name):
        return name in self.list_collection_names()

    def count(self, name):
        return self._collection(name).count()

    def get_collection_metadata(self, name):
        return self._collection(name).metadata or {}

    def delete_collection(self, name):
        self._client.delete_collection(name=name)

    # ------------------------------------------------------------------
    # 資料操作
    # ------------------------------------------------------------------

    def upsert(self, name, ids, documents=None, metadatas=None, embeddings=None,
               embedding_function=None):
        """寫入（或覆蓋）資料；collection 不存在時自動以 cosine 距離建立。"""
        collection = self._client.get_or_create_collection(
            name=name,
            embedding_function=embedding_function or self._default_embedding(),
            metadata={"hnsw:space": "cosine"}
        )
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )

    def get(self, name, ids=None, where=None, limit=None, include=None,
            embedding_function=None):
        kwargs = {}
        if ids is not None:
            kwargs["ids"] = ids
        if where is not None:
            kwargs["where"] = where
        if limit is not None:
            kwargs["limit"] = limit
        if include is not None:
            kwargs["include"] = include
        return self._collection(name, embedding_function).get(**kwargs)

    def query(self, name, query_embeddings, n_results=10, where=None, include=None,
              embedding_function=None):
        kwargs = {"query_embeddings": query_embeddings, "n_results": n_results}
        if where is not None:
            kwargs["where"] = where
        if include is not None:
            kwargs["include"] = include
        return self._collection(name, embedding_function).query(**kwargs)
