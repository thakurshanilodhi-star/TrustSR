from pathlib import Path
import subprocess
import qrcode

REPO = "thakurshanilodhi-star/TrustSR"
BRANCH = "main"

# Git se actual tracked notebooks collect karo
result = subprocess.run(
    ["git", "ls-files", "*.ipynb"],
    capture_output=True,
    text=True,
    check=True
)

notebooks = sorted(result.stdout.splitlines())

if not notebooks:
    raise RuntimeError("No tracked notebooks found.")

# Labs Index Markdown
lines = [
    "# TrustSR — Practical Labs",
    "",
    "Run the practical notebooks directly in Google Colab.",
    "",
    f"**Total notebooks: {len(notebooks)}**",
    "",
]

current_folder = None

for path in notebooks:
    folder = path.split("/")[1]

    if folder != current_folder:
        current_folder = folder
        lines.extend(["", f"## {folder.replace('_', ' ').title()}", ""])

    colab_url = (
        f"https://colab.research.google.com/github/"
        f"{REPO}/blob/{BRANCH}/{path}"
    )

    name = Path(path).stem.replace("_", " ")
    lines.append(f"- [{name}]({colab_url})")

lines.extend([
    "",
    "---",
    f"[Open TrustSR GitHub Repository](https://github.com/{REPO})",
])

Path("labs/README.md").write_text(
    "\n".join(lines), encoding="utf-8"
)

# QR output folder
out = Path("docs/qr")
out.mkdir(parents=True, exist_ok=True)

urls = {
    "TrustSR_All_Labs_QR.png":
        f"https://github.com/{REPO}/blob/{BRANCH}/labs/README.md",

    "TrustSR_GitHub_QR.png":
        f"https://github.com/{REPO}"
}

for filename, url in urls.items():
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4
    )
    qr.add_data(url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )
    image.save(out / filename)

print("SUCCESS")
print("Notebooks:", len(notebooks))
print("Labs Index: labs/README.md")
print("QR files:", out.resolve())