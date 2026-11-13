# Python Tutorial Data Ingestion Benchmark

Bài làm cá nhân Day 06 của Nguyễn Công Quân (`2A202603675`). Pipeline đọc Python Tutorial 3.13.7, so sánh fixed-window với paragraph-aware chunking và metadata filtering, tạo embedding local bằng `all-MiniLM-L6-v2`, rồi lưu/tìm kiếm bằng Chroma.

## Kết quả chính

| Strategy | Chunking / filter | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Coherence |
|---|---|---:|---:|---:|---:|---:|
| A | 800 ký tự, overlap 120 | 6/15 | 10/15 | 4/5 | 5/5 | 1.1/2 |
| B | PDF paragraph blocks, max 1000 | 9/15 | 13/15 | 3/5 | 5/5 | 1.8/2 |
| C | Như B + `category` filter | 9/15 | 13/15 | 3/5 | 5/5 | 1.8/2 |

B được chọn theo tiêu chí đã chốt trên dev: Evidence Hit@3 trước, sau đó Hit@1, grounding và tài nguyên. Test chỉ có năm câu nên không dùng để tuyên bố ưu thế tổng quát.

## Dữ liệu

- Nguồn: Python Tutorial 3.13.7, Python Software Foundation License Version 2.
- PDF: 167 trang vật lý; 101 trang nội dung hợp lệ theo quy tắc trong `data/manifest.json`.
- SHA-256, URL, giấy phép, page inventory và category nằm trong manifest.
- `data/source/tutorial.pdf` được giữ trong repo để chạy lại đúng snapshot.

## Cài đặt và chạy

Yêu cầu Python 3.11–3.14 và kết nối Internet trong lần đầu để tải model embedding. Không cần Docker hoặc API key.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r starter\requirements.txt
.venv\Scripts\python.exe starter\scripts\check_setup.py
.venv\Scripts\python.exe starter\scripts\validate_benchmark.py
cd starter
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m src.run --reindex
..\.venv\Scripts\python.exe scripts\audit_results.py
```

Sau khi model đã có trong Hugging Face cache, có thể chặn kiểm tra mạng bằng:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
```

`--skip-test` chỉ chạy dev trong giai đoạn thử nghiệm. Không dùng test để chỉnh tham số. Chroma lưu bền vững tại `starter/.chroma/` (không commit); stable chunk IDs và upsert ngăn nhân bản.

## Artifacts

- Corpus manifest: [`data/manifest.json`](data/manifest.json)
- Benchmark/gold: [`benchmark/questions.json`](benchmark/questions.json)
- Cấu hình: [`artifacts/experiment_log.csv`](artifacts/experiment_log.csv)
- Top-3 trace: [`results/traces.jsonl`](results/traces.jsonl)
- Metrics: [`results/metrics.json`](results/metrics.json)
- Audit labels: [`results/manual_audit.json`](results/manual_audit.json)
- Phân tích năm khía cạnh: [`results/analysis.md`](results/analysis.md)
- Báo cáo cá nhân: [`report/individual/2A202603675_NguyenCongQuan.md`](report/individual/2A202603675_NguyenCongQuan.md)

Chi tiết implementation và tham số nằm trong [`starter/README.md`](starter/README.md). Định nghĩa metric gốc vẫn xem tại [`GUIDE.md`](GUIDE.md) và [`BENCHMARK.md`](BENCHMARK.md).
