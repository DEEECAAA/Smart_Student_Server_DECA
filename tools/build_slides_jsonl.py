import json
import re
from pathlib import Path

from PIL import Image
import pytesseract

IMG_DIR = Path("/mnt/c/Users/PCGAMING/Desktop/SENEM/SENEM_Metaverse-main/Mevaterse_Classroom_2/Assets/Resources/Images")
OUT = Path("rag_data/slides.jsonl")

def slide_key(p: Path):
    # prende "01" da "...-01.png"
    m = re.search(r"-(\d{2,})$", p.stem)
    if not m:
        return None
    return m.group(1)

def ocr_image(path: Path) -> str:
    img = Image.open(path).convert("RGB")
    return pytesseract.image_to_string(img, lang="ita+eng")

def clean(text: str) -> str:
    text = text.replace("\x0c", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    pngs = sorted([p for p in IMG_DIR.glob("*.png") if p.is_file() and not p.name.endswith(".meta")])

    rows = []
    seen = set()  # <-- deve stare QUI (fuori dal loop)

    for p in pngs:
        key = slide_key(p)
        if key is None:
            continue

        idx = int(key) - 1

        # dedup per indice slide
        if idx in seen:
            continue
        seen.add(idx)

        raw = ocr_image(p)
        txt = clean(raw)

        if not txt:
            txt = f"(Slide {key})"

        rows.append({
            "source": "slides",
            "slide_index": idx,
            "slide_name": key,
            "text": txt,
        })

    rows.sort(key=lambda r: r["slide_index"])

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} slides to {OUT}")

if __name__ == "__main__":
    main()
