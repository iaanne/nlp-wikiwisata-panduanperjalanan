# Scripts

- `check_tree.py`: memeriksa kelengkapan struktur.
- `check_env.py`: mencetak versi Python, torch, dan GPU.
- `check_config_delta.py`: membandingkan dua config dan mencetak field yang berubah.

Script yang belum diimplementasikan:
- `verify_corpus_repro.sh`: Elias.
- `run_3x_eval.sh`: Nad dan Ian.
- `run_red_team.py`: Jimly.
- `verify_trace_log.py`: Jimly.

Jangan menaruh logika eksperimen di shell script. Shell hanya memanggil Python.
