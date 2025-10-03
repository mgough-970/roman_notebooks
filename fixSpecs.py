#!/usr/bin/env python3
import nbformat as nbf
import pathlib
import gzip
import io
import sys
import json

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
changed = skipped = errored = 0

def is_gzip(p: pathlib.Path) -> bool:
    try:
        with p.open("rb") as f:
            return f.read(2) == b"\x1f\x8b"
    except Exception:
        return False

def read_nb_from_bytes(raw: bytes):
    # Try to read JSON notebook from bytes
    text = raw.decode("utf-8")
    return nbf.reads(text, as_version=4)

def write_nb_to_bytes(nb) -> bytes:
    text = nbf.writes(nb)
    return text.encode("utf-8")

for p in ROOT.rglob("*.ipynb"):
    # skip checkpoints
    if ".ipynb_checkpoints" in p.parts:
        skipped += 1
        continue

    try:
        if p.name.endswith(".ipynb.gz") or is_gzip(p):
            # notebook is gzipped → read/decompress
            with p.open("rb") as fh:
                gzraw = fh.read()
            try:
                raw = gzip.decompress(gzraw)
            except OSError:
                # Not actually gzip; skip
                skipped += 1
                continue
            nb = read_nb_from_bytes(raw)
            # strip kernelspec
            if "kernelspec" in nb.metadata:
                del nb.metadata["kernelspec"]
                changed += 1
                # recompress and write back
                out = write_nb_to_bytes(nb)
                with p.open("wb") as fh:
                    fh.write(gzip.compress(out))
            else:
                skipped += 1
        else:
            # regular .ipynb
            with p.open("r", encoding="utf-8") as fh:
                nb = nbf.read(fh, as_version=4)
            if "kernelspec" in nb.metadata:
                del nb.metadata["kernelspec"]
                with p.open("w", encoding="utf-8") as fh:
                    nbf.write(nb, fh)
                changed += 1
            else:
                skipped += 1
    except (UnicodeDecodeError, json.JSONDecodeError, nbf.validator.NotebookValidationError):
        errored += 1
    except Exception:
        errored += 1

print(f"Done. Changed: {changed}, Skipped: {skipped}, Errored: {errored}")

