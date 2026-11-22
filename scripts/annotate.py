"""Isi satu paket dev dari terminal. Jalankan dari root repo."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def save(path, rows):
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        for row in rows:
            temp.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(temp.name, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--annotator", required=True, choices=["nad", "elias"])
    args = parser.parse_args()
    packet = read(args.packet)
    path = Path("data/annotations/blind") / f"{args.annotator}_dev.jsonl"
    rows = read(path) if path.exists() else [dict(r) for r in packet]
    fields = ("question_id", "chunk_id", "corpus_hash", "question", "text")
    def identity(records):
        return [tuple(row[k] for k in fields) for row in records]
    if identity(rows) != identity(packet):
        parser.exit(1, "Berkas penilai berbeda dari paket. Periksa versi paket.\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    for pos, row in enumerate(rows, 1):
        if row["relevance"] is not None:
            continue
        print(f"\n[{pos}/{len(rows)}] {row['question']}\n\n{row['text']}\n")
        while True:
            score = input("Skor 0/1/2 (q untuk berhenti): ").strip().lower()
            if score == "q":
                return
            if score in ("0", "1", "2"):
                break
        reason = ""
        while not reason:
            reason = input("Alasan singkat: ").strip()
        row.update(relevance=int(score), reason=reason, annotator=args.annotator)
        save(path, rows)
        print("Tersimpan.")
    print(f"Selesai: {path}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBerhenti. Isian yang sudah tersimpan bisa dilanjutkan.")
