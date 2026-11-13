# Implemented local pipeline

Thư mục này chứa implementation đã chạy của bài lab. Backend là persistent Chroma 1.5.9; các file Docker/pgvector ban đầu được giữ để tham khảo nhưng không được pipeline sử dụng.

## Luồng xử lý

```text
PyMuPDF blocks → NFKC/whitespace normalization → A/B/C chunks
→ all-MiniLM-L6-v2 normalized embeddings (384 dimensions)
→ Chroma cosine HNSW → top-3 trace → exact evidence metrics
```

- A: fixed 800 characters, overlap 120.
- B: paragraph/block aware, maximum 1000 characters.
- C: giống B; chỉ áp dụng caller-supplied `category` filter cho câu có filter.
- Metadata: `document_id`, `source`, physical `page`, `category`, `release`, extraction status và chunk offsets/group.

## Lệnh chạy từ thư mục `starter/`

```powershell
..\.venv\Scripts\python.exe scripts\check_setup.py
..\.venv\Scripts\python.exe scripts\validate_benchmark.py
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m src.run --reindex
..\.venv\Scripts\python.exe scripts\audit_results.py
```

`--reindex` tạo embedding và upsert toàn bộ. Không có cờ này, pipeline tái sử dụng collection khi stored count khớp; thay đổi source/chunk IDs được xử lý bởi upsert và xóa ID lỗi thời. `--skip-test` dùng trong giai đoạn dev. Lần đầu chạy cần mạng để tải model; các lần sau dùng cache local. Không có mock-vector fallback.

## Modules

- `src/ingestion.py`: đọc từng trang vật lý, giữ block/paragraph, ghi trạng thái lỗi/rỗng.
- `src/chunking.py`: fixed-window và paragraph-aware chunking với ID ổn định.
- `src/embeddings.py`: Sentence Transformers adapter dùng cùng model cho query/document.
- `src/store.py`: Chroma persistence, cosine search, upsert và whitelist filter.
- `src/evaluation.py`: kiểm tra source/page/full evidence và tổng hợp Hit@1/Hit@3.
- `src/run.py`: orchestration và ghi trace/metrics.
- `scripts/`: manifest inspection, benchmark validation, chunk profiling và audit.

Thư mục `.chroma/` không commit. Các kết quả nhỏ đã chạy nằm tại `../results/` để người chấm kiểm chứng mà không cần tải lại model.
