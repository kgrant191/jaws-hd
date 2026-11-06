"""Package the installable Mesen pack and the four README comparisons."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'HdPacks' / 'Jaws (USA)'
ASSETS = ROOT / 'docs' / 'images'
VERSION = '1.0.0'
COMPARISONS = ('01-title-screen.jpg', '02-coastal-map.jpg',
               '03-shark-encounter.jpg', '04-final-breach.jpg')


def runtime_files():
    names = {'hires.txt'}
    for line in (PACK / 'hires.txt').read_text().splitlines():
        for directive in ('<img>', '<background>', '<patch>'):
            if directive in line:
                name = line.split(directive, 1)[1].split(',', 1)[0].strip()
                if Path(name).name != name or name in ('', '.', '..'):
                    raise ValueError(f'Unexpected pack resource {name!r}')
                names.add(name)
    return [PACK / name for name in sorted(names)]


def archive(path, files, prefix=''):
    with ZipFile(path, 'w') as output:
        for item in files:
            # Fixed ZIP metadata makes local and GitHub builds comparable.
            info = ZipInfo(prefix + item.name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            output.writestr(info, item.read_bytes(), compress_type=ZIP_DEFLATED,
                            compresslevel=6)
    with ZipFile(path) as output:
        if output.testzip() is not None:
            raise ValueError(f'Invalid ZIP: {path.name}')
        print(f'{path.name}: {len(output.namelist())} files')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    dest = parser.parse_args().output
    dest.mkdir(parents=True, exist_ok=True)
    archive(dest / f'Jaws_HD_v{VERSION}.zip', runtime_files(), PACK.name + '/')
    archive(dest / f'Jaws_HD_v{VERSION}_Comparisons.zip', [ASSETS / n for n in COMPARISONS])
