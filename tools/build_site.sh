#!/usr/bin/env bash
# Assemble the GitHub Pages site in site/ and publish it to the gh-pages branch.
#   site/index.html is the landing page (kept in git on main).
#   kanban.html / effort.html are artifact pages written without <!doctype>/<head>
#   (the artifact host adds those); here they get a proper document wrapper.
# usage: tools/build_site.sh            build only
#        tools/build_site.sh --publish  build, commit site/ on main, push site/ to gh-pages
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=video/out
for f in kanban effort; do
  { printf '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    printf '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    printf '<style>*{box-sizing:border-box}body{margin:0}img{max-width:100%%}</style>\n</head>\n<body>\n'
    cat "$f.html"
    printf '\n</body>\n</html>\n'; } > "site/$f.html"
done
cp "$OUT/task-decomposition.mp4" "$OUT/task-decomposition.srt" "$OUT/task-decomposition.qa.json" \
   "$OUT/task-decomposition.description.md" "$OUT/qa_sheet.jpg" site/
ffmpeg -loglevel error -y -i "$OUT/task-decomposition.srt" site/task-decomposition.vtt
ffmpeg -loglevel error -y -ss 1.5 -i "$OUT/task-decomposition.mp4" -frames:v 1 -q:v 3 site/poster.jpg
touch site/.nojekyll
echo "site/ ready: $(ls site | tr '\n' ' ')"
if [ "${1:-}" = "--publish" ]; then
  git add site
  git commit -q -m "Update GitHub Pages site" || true
  git push -q origin "$(git subtree split --prefix site HEAD)":refs/heads/gh-pages --force
  echo "pushed site/ to gh-pages"
fi
