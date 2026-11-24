#!/usr/bin/env bash
# Assemble the GitHub Pages site in site/ and publish it.
#   pages/*.html  full pages with a <!--MENU--> marker (landing page, Mac FLUX page)
#   kanban.html / effort.html  artifact pages written without <!doctype>/<head> (the artifact
#                 host adds those); here they get a document wrapper
#   pages/menu.html  the one shared menu, inserted into every page; the current page's link
#                 gets aria-current="page"
# usage: tools/build_site.sh            build only
#        tools/build_site.sh --publish  build, commit site/ and push main; the Pages workflow
#                                       (.github/workflows/static.yml) deploys site/ and tests it live
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=video/out
mkdir -p site
python3 - <<'EOF'
from pathlib import Path
menu = Path("pages/menu.html").read_text()

def with_menu(html: str, page: str) -> str:
    m = menu.replace(f'class="tdm-l" href="{page}"', f'class="tdm-l" href="{page}" aria-current="page"')
    assert "<!--MENU-->" in html, page
    return html.replace("<!--MENU-->", m, 1)

for src in sorted(Path("pages").glob("*.html")):
    if src.name != "menu.html":
        Path("site", src.name).write_text(with_menu(src.read_text(), src.name))

head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>*{box-sizing:border-box}body{margin:0}img{max-width:100%}</style>\n</head>\n<body>\n'
        '<!--MENU-->\n')
for name in ("kanban.html", "effort.html"):
    Path("site", name).write_text(with_menu(head + Path(name).read_text() + "\n</body>\n</html>\n", name))
EOF
cp "$OUT/task-decomposition.mp4" "$OUT/task-decomposition.srt" "$OUT/task-decomposition.qa.json" \
   "$OUT/task-decomposition.description.md" "$OUT/qa_sheet.jpg" site/
ffmpeg -loglevel error -y -i "$OUT/task-decomposition.srt" site/task-decomposition.vtt
ffmpeg -loglevel error -y -ss 1.5 -i "$OUT/task-decomposition.mp4" -frames:v 1 -q:v 3 site/poster.jpg
touch site/.nojekyll
echo "site/ ready: $(ls site | tr '\n' ' ')"
if [ "${1:-}" = "--publish" ]; then
  git add site pages
  git commit -q -m "Update GitHub Pages site" || true
  git push -q origin HEAD:main
  echo "pushed main; GitHub Actions deploys site/ to Pages"
fi
