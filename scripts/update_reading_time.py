"""
Script: update_reading_time.py
- Recorre la carpeta actual (y subcarpetas) buscando archivos .md
- Calcula el tiempo de lectura a 200 wpm y añade/actualiza `reading_time_min` en el frontmatter YAML
- Hace una copia de seguridad del archivo original con extensión .bak antes de sobrescribir

Uso:
    python scripts/update_reading_time.py [ruta_base]
Si no se pasa ruta, usa el directorio actual.
"""
import sys
from pathlib import Path
import re
import math

WPM = 200

FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def compute_reading_time(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    return max(1, math.ceil(words / WPM))


def parse_frontmatter(content: str):
    m = FRONT_RE.match(content)
    if not m:
        return None, content
    fm = m.group(1)
    body = content[m.end():]
    return fm, body


def frontmatter_to_dict(fm: str) -> dict:
    # Simple YAML-ish parser for our limited fields (no dependencies)
    data = {}
    for line in fm.splitlines():
        if not line.strip() or line.strip().startswith('#'):
            continue
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            # remove surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            # simple list
            if val.startswith('[') and val.endswith(']'):
                items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',') if v.strip()]
                data[key] = items
            else:
                # try int
                try:
                    data[key] = int(val)
                except Exception:
                    if val.lower() in ('true','false'):
                        data[key] = val.lower()=='true'
                    else:
                        data[key] = val
    return data


def dict_to_frontmatter(d: dict) -> str:
    lines = []
    for k, v in d.items():
        if isinstance(v, list):
            liststr = '[' + ','.join(f'"{i}"' for i in v) + ']'
            lines.append(f"{k}: {liststr}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {str(v).lower()}")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: \"{v}\"")
    return "\n".join(lines)


def process_file(path: Path):
    text = path.read_text(encoding='utf-8')
    fm_text, body = parse_frontmatter(text)
    if fm_text is None:
        # build minimal frontmatter
        title_line = path.stem.replace('-', ' ')
        # try to extract year from first line of file
        first_line = text.splitlines()[0] if text.splitlines() else ''
        year_match = re.search(r"(19\d{2}|20\d{2})", first_line)
        film_year = int(year_match.group(0)) if year_match else ''
        fm = {
            'title': first_line.strip() if first_line else title_line,
            'review_year': path.parent.name if path.parent.name.isdigit() else '' ,
            'film_year': film_year,
            'rating': '',
            'reading_time_min': compute_reading_time(text),
            'slug': path.stem,
        }
        new_fm_text = dict_to_frontmatter(fm)
        new_content = '---\n' + new_fm_text + '\n---\n\n' + text
    else:
        fm = frontmatter_to_dict(fm_text)
        rt = compute_reading_time(body)
        fm['reading_time_min'] = rt
        new_fm_text = dict_to_frontmatter(fm)
        new_content = '---\n' + new_fm_text + '\n---\n\n' + body

    # backup
    backup = path.with_suffix(path.suffix + '.bak')
    path.replace(backup)
    path.write_text(new_content, encoding='utf-8')
    print(f"Updated {path} (backup: {backup.name}) - reading_time_min={fm.get('reading_time_min')}")


def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    if not base.exists():
        print('Ruta no encontrada:', base)
        return
    md_files = list(base.rglob('*.md'))
    if not md_files:
        print('No se encontraron archivos .md en', base)
        return
    for p in md_files:
        try:
            process_file(p)
        except Exception as e:
            print('Error procesando', p, e)


if __name__ == '__main__':
    main()
