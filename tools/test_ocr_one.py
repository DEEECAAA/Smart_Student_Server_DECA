from pathlib import Path
from PIL import Image
import pytesseract

p = Path("/mnt/c/Users/PCGAMING/Desktop/SENEM/SENEM_Metaverse-main/Mevaterse_Classroom_2/Assets/Resources/Images/slidesgo-pizza-party-101-crafting-your-perfect-slice-of-happiness-2025010717360851ky-01.png")  # cambia se il nome è diverso
img = Image.open(p).convert("RGB")
txt = pytesseract.image_to_string(img, lang="ita+eng")
print(txt[:800])
