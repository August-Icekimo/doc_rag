# 待辦任務清單

> 來源：`docs/architecture_review.md`  
> 建立日期：2026-06-12  
> 狀態說明：✅ 程式邏輯全數完成（2026-06-12，四個獨立 commit）；本環境僅能做邏輯開發與編譯驗證，尚待實際環境（含 ChromaDB 資料、本地 LLM 服務）整體測試

---

## ⚠️ P5 — Provider 正規化邏輯仍重複

**問題**：`app_flask.py:239-245` 的 `background_query_worker` 自行做 `provider.lower().strip()` 分支映射，`model/llm.py:21` 也再做一次，雙重 normalize 仍然存在。

**目標**：刪除 `app_flask.py` 中的 provider 分支映射，直接把原始字串傳入 `query_llm()`，由 `llm.py` 統一處理。

**異動範圍**
- [x] `app_flask.py:239-245`：刪除 `p_clean`、`p_val` 變數及分支，直接傳 `provider`
- [x] `model/llm.py:21`：確認 `p_clean = provider.lower().strip()` 能正確覆蓋所有 case（含 VLM 路徑）
- [x] `indexer/ocr_loader.py`：確認 `reconstruct_pages_via_vlm` 中 `provider_clean` 邏輯一致

---

## ⚠️ 問題#7 — VLM `requests.post(timeout=None)` 仍可永久掛住

**問題**：`ocr_loader.py:434` 與 `:455` 的 `requests.post(..., timeout=None)` 若 LLM 服務在傳輸中途當掉，worker thread 會無限期阻塞；`_vlm_timeout_monitor` 僅在 600s 後印出警告，**不中斷** 阻塞的 thread。

**目標**：將 `timeout=None` 改為有限值（建議 600s），並在 `requests.post` 前後補 cancel token 檢查。

**異動範圍**
- [x] `ocr_loader.py:434`：`timeout=None` → `timeout=600`
- [x] `ocr_loader.py:455`：`timeout=None` → `timeout=600`
- [x] 在每次 `requests.post` **之前**加一次 `if not worker_thread.is_running: return` cancel 檢查
- [x] （選用）`_vlm_timeout_monitor`：timeout 後改為呼叫 `worker_thread.is_running = False` 主動取消，而非只印警告

---

## ❌ 問題#8 — Flask 以 `debug=True` 啟動

**問題**：`app_flask.py:740` 的 `debug=True` 啟動 Werkzeug reloader，產生父子兩個 Python process，`TASK_STATUS` 存在兩份獨立副本，前端輪詢可能對到錯誤的 process，導致狀態顯示異常。

**目標**：以環境變數控制 debug 模式，預設關閉。

**異動範圍**
- [x] `app_flask.py:740`：改為
  ```python
  debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
  app.run(host="127.0.0.1", port=5000, debug=debug_mode)
  ```
- [x] 確認 `import os` 已在檔案頂部（目前已存在）

---

## ❌ Backlog — 無 Storage 抽象層

**問題**：`import chromadb` 散落於 `retriever/retriever.py`、`indexer/indexer.py`、`indexer/ocr_loader.py`、`app_flask.py`（共 8 處）。換 vector backend（如 pgvector）需逐一修改多個模組。

**目標**：新增 `storage/` 模組，提供統一的 `VectorStore` 介面，隔離 chromadb 細節。

**異動範圍**
- [x] 新增 `storage/__init__.py`
- [x] 新增 `storage/vector_store.py`：封裝 `get_collection`、`upsert`、`query`、`delete_collection` 四個操作
- [x] 重構 `indexer/indexer.py`：改用 `storage.vector_store`
- [x] 重構 `retriever/retriever.py`：改用 `storage.vector_store`
- [x] 重構 `indexer/ocr_loader.py` 中的 chromadb 直接呼叫
- [x] 重構 `app_flask.py` 中的 chromadb 直接呼叫（merge DB、list collections 等）
- [x] 更新 `requirements.txt` 若有異動
