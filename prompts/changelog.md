# Changelog prompt

| Tanggal | Prompt | Versi | Perubahan | Alasan |
|---|---|---|---|---|
| 2026-11-21 | b0_default | 1.0.0 | Versi awal | Baseline tanpa retrieval |
| 2026-11-22 | b0_default | 1.0.0 | Tambah placeholder pertanyaan dan kontrak output | B0 perlu pertanyaan aktual dan bentuk JSON eksplisit |
| 2026-11-22 | b0_default | 1.1.0 | Enum verdict dan status eksplisit | B0 memakai verdict di luar schema |
| 2026-11-21 | b1_structured_abstain | 1.0.0 | Versi awal | Skema JSON dan aturan abstain |
| 2026-11-22 | b1_structured_abstain | 1.1.0 | Aturan passage kondisional dan kontrak output | B1 tidak memakai retrieval, aturan lama memaksa abstain |
| 2026-11-22 | b1_structured_abstain | 1.2.0 | Larangan field tambahan, sitasi ketat, aturan abstain data berubah | B1 menjawab tanpa bukti dan memakai field sitasi liar |
| 2026-11-21 | b4_answer | 1.0.0 | Versi awal | Klaim atomik dan verifikasi |
| 2026-11-21 | b6_tool_system | 1.0.0 | Versi awal | Aturan tool read-only |
| 2026-11-21 | query_planner | 1.0.0 | Versi awal | Dekomposisi pertanyaan |
| 2026-11-21 | evidence_check | 1.0.0 | Versi awal | Kecukupan bukti |
| 2026-11-21 | claim_verifier | 1.0.0 | Versi awal | Verifikasi klaim |
| 2026-11-22 | format_repair | 1.0.0 | Versi awal | Perbaikan format satu kali setelah parse gagal |
