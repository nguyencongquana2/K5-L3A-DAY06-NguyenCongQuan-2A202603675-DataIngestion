# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang: Python Tutorial 3.13.7 của Python Software Foundation, PSF License Version 2. PDF có 167 trang vật lý. Chỉ xét phần tutorial trang 9–122 và tính trang có ít nhất 500 ký tự sau chuẩn hóa; loại bìa, mục lục, glossary, license và index, còn 101 trang nội dung. Manifest, SHA-256 và page inventory: `data/manifest.json`.
- Chuẩn hóa, lỗi và giới hạn: PyMuPDF 2.1 đọc text blocks theo từng trang; chuẩn hóa NFKC, bỏ soft hyphen, nối từ bị ngắt bởi `-` cuối dòng, chuẩn hóa whitespace và bỏ running header/footer. Không có trang lỗi/rỗng trong 101 trang được tính. Giới hạn: block layout phụ thuộc PDF; một số trang bắt đầu bằng “continued from previous page”.
- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí: local `sentence-transformers/all-MiniLM-L6-v2`, sentence-transformers 6.3.0, 384 chiều, normalized embeddings; persistent Chroma 1.5.9, cosine HNSW (approximate). Chạy `cd starter` rồi `..\.venv\Scripts\python.exe -m src.run --reindex`. Chi phí API: USD 0; lần đầu cần tải model.
- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn: `document_id`, `source`, physical `page`; thêm `category`, `release`, `extraction_status` và chunk offset/group. `category` lấy từ chapter/page ranges đã khai báo trong script manifest, giúp giới hạn truy xuất theo phần như `modules`, `exceptions`, `virtual_environments`.

## Cấu hình và benchmark
- A / B / C (tham số cụ thể, khác biệt duy nhất B–C): A fixed-size 800 ký tự, overlap 120, không filter; B PDF paragraph blocks, max 1000, không filter; C chunk/vector giống B và chỉ thêm `category` filter do benchmark cung cấp. Cả ba dùng cùng corpus/model/store/cosine.
- ≥20 câu: 20 câu được chốt trước retrieval, 15 dev và 5 test. q07, q10, q18 có filter; q18 thuộc test. Mỗi evidence được `validate_benchmark.py` kiểm tra tồn tại đúng physical page sau canonical whitespace.
- Tiêu chí chọn chiến lược đã chốt trước khi xem test: tối đa dev Evidence Hit@3, sau đó dev Hit@1, rồi manual grounding và chi phí/tài nguyên. Không chỉnh cấu hình theo test.

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian ingest/upsert | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 6/15 | 10/15 | 381 | 10.762 s | USD 0 |
| A | test | 4/5 | 5/5 | 381 | dùng cùng index | USD 0 |
| B | dev | 9/15 | 13/15 | 308 | 8.519 s | USD 0 |
| B | test | 3/5 | 5/5 | 308 | dùng cùng index | USD 0 |
| C | dev | 9/15 | 13/15 | 308 | 0.467 s (tái dùng vector B, upsert collection C) | USD 0 |
| C | test | 3/5 | 5/5 | 308 | dùng cùng index | USD 0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1.1/2 (10) | 15/15 | N/A | 0/0/5; 2.0/2 |
| B | 1.8/2 (10) | 15/15 | N/A | 0/0/5; 2.0/2 |
| C | 1.8/2 (10) | 15/15 | 3/3 records, 1/1 câu filter | 0/0/5; 2.0/2 |

Đường dẫn trace, nhãn thủ công và cách chọn mẫu: `results/traces.jsonl`, `results/manual_audit.json`, `results/metrics.json`. Coherence dùng midpoint của 10 page ID nội dung đầu tiên đã sắp xếp; metadata kiểm tra toàn bộ 5 test × top-3 × 3 strategy; grounding chấm 5 test mỗi strategy. Nhãn được review có hỗ trợ AI, không độc lập với người hiện thực và có nguy cơ lạc quan; học viên cần xác nhận trước khi nộp.

## Phân tích và kết luận
- So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn: A→B giảm 381 xuống 308 chunks, tăng dev Hit@3 từ 10/15 lên 13/15 và coherence 1.1 lên 1.8. B→C không đổi aggregate exact-hit vì chỉ ba câu có filter; q18 loại được hit sai category nhưng q10 vẫn miss. q14: A lấy đúng page 70 nhưng fixed boundary bỏ đầu evidence; B/C nhầm với loop `else`/`finally`. q10: filter `modules` thu hẹp phạm vi nhưng không đưa đoạn `__init__.py`/`__all__` vào top-3.
- Chiến lược chọn, đánh đổi, điều kiện áp dụng: chọn B theo tiêu chí dev. B tốt hơn trên corpus PDF có block/paragraph rõ, ít chunk hơn và không đòi caller cung cấp filter. Dùng C khi ứng dụng có category đáng tin; filter không thay thế semantic ranking.
- Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí: chỉ một sách tiếng Anh và 5 test; gold dựa trên một evidence; audit có hỗ trợ AI và không độc lập; HNSW/library version có thể đổi ranking; timing là một lần chạy CPU và C tái dùng vector B nên không so trực tiếp như embedding độc lập. Grounding 2/2 chỉ nói evidence đủ, không phải LLM answer accuracy.
- Nếu làm lại hoặc mở rộng, cải tiến gì? Tăng test và nhiều nguồn/version để filter có ý nghĩa hơn; thêm heading-aware overlap cho đoạn qua page boundary; đo nhiều lần với warm/cold cache; thử hybrid BM25+dense trên dev rồi kiểm tra bằng holdout mới.

AI được dùng để đọc đề, viết/kiểm thử code, soạn benchmark và hỗ trợ audit/phân tích. Evidence được kiểm tra máy với PDF; không tạo kết quả giả và không dùng mock embedding. Học viên chịu trách nhiệm đọc lại câu hỏi, gold và nhãn trước khi nộp.
