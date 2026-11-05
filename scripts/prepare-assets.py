#!/usr/bin/env python3
"""Copy approved Moodumi artwork and produce responsive website renditions.

Requires Pillow. No source image is changed. Run from any working directory:
  python3 scripts/prepare-assets.py --source-root ../Moodumi
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path('/Library/Fonts/SF-Pro-Rounded-Bold.otf' if bold else '/Library/Fonts/SF-Pro-Rounded-Regular.otf'),
        Path('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise SystemExit('Install a readable TrueType/OpenType font before generating the social image.')


def main() -> None:
    website = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=website.parent / 'Moodumi')
    parser.add_argument('--output', type=Path, default=website / 'assets')
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    output = args.output.resolve()
    sources = {
        'leo': source_root / 'Moodumi/Resources/JournalLeo/journal-leo-poster.png',
        'garden': source_root / 'Moodumi/Resources/GrowthLeo/growth-landscape.png',
        'icon': source_root / 'Moodumi/Assets.xcassets/AppIcon.appiconset/moodumi-app-icon.png',
        **{f'screenshot-{name}': source_root / f'Release/AppStore/en/raw/iphone-medium/{story}.png'
           for name, story in [('check-in', '01-check-in'), ('journal', '02-journal'),
                               ('insights', '03-insights'), ('growth', '04-growth')]},
        'screenshot-ipad': source_root / 'Release/AppStore/en/raw/ipad-13/03-insights.png',
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise SystemExit('Missing approved source files:\n' + '\n'.join(missing))
    source_hashes = {key: digest(path) for key, path in sources.items()}
    output.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict] = {}

    def record(key: str, path: Path, operation: str) -> None:
        with Image.open(path) as image:
            records[path.name] = {
                'source_key': key, 'operation': operation, 'width': image.width,
                'height': image.height, 'mode': image.mode, 'bytes': path.stat().st_size,
                'sha256': digest(path),
            }

    def copy(key: str, name: str) -> None:
        target = output / name
        shutil.copyfile(sources[key], target)
        record(key, target, 'Byte-for-byte copy of approved source')
        assert digest(target) == source_hashes[key]

    def resize_webp(key: str, width: int, name: str, quality: int = 88) -> None:
        with Image.open(sources[key]) as source:
            source = source.convert('RGBA' if 'A' in source.getbands() else 'RGB')
            height = round(source.height * width / source.width)
            image = source.resize((width, height), Image.Resampling.LANCZOS)
            target = output / name
            image.save(target, 'WEBP', quality=quality, method=6, exact=True)
            record(key, target, f'Proportional Lanczos resize, WebP quality {quality}, alpha retained where present')

    copy('leo', 'leo.png')
    copy('garden', 'garden.png')
    for width in (480, 800):
        resize_webp('leo', width, f'leo-{width}.webp', quality=91)
    resize_webp('garden', 1600, 'garden.webp', quality=89)
    for key in ('screenshot-check-in', 'screenshot-journal', 'screenshot-insights', 'screenshot-growth'):
        copy(key, f'{key}.png')
        for width in (480, 800):
            resize_webp(key, width, f'{key}-{width}.webp', quality=90)
    copy('screenshot-ipad', 'screenshot-ipad.png')
    for width in (900, 1400):
        resize_webp('screenshot-ipad', width, f'screenshot-ipad-{width}.webp', quality=90)
    with Image.open(sources['icon']) as icon_source:
        for size, name in ((32, 'favicon-32.png'), (192, 'favicon-192.png'), (180, 'apple-touch-icon.png')):
            icon = icon_source.convert('RGB').resize((size, size), Image.Resampling.LANCZOS)
            target = output / name
            icon.save(target, 'PNG', optimize=True)
            record('icon', target, 'Proportional Lanczos resize to square; no added corner mask')

    # Social metadata artwork uses the approved Leo, unchanged except scaling.
    social = Image.new('RGB', (1200, 630))
    pixels = social.load()
    top, bottom = (255, 248, 239), (255, 235, 214)
    for y in range(social.height):
        fraction = y / (social.height - 1)
        row_color = tuple(round(a + (b - a) * fraction) for a, b in zip(top, bottom))
        for x in range(social.width):
            pixels[x, y] = row_color
    draw = ImageDraw.Draw(social)
    brown, orange = '#59331F', '#C45B24'
    draw.text((76, 69), 'Moodumi', fill=orange, font=font(43, True))
    draw.text((76, 205), 'Make room for', fill=brown, font=font(65, True))
    draw.text((76, 280), 'every feeling.', fill=brown, font=font(65, True))
    draw.text((79, 402), 'Mood journal & gentle growth', fill=brown, font=font(27))
    draw.rounded_rectangle((79, 464, 155, 473), radius=4, fill='#E88C53')
    with Image.open(sources['leo']) as leo_source:
        leo = leo_source.convert('RGBA')
        leo.thumbnail((490, 530), Image.Resampling.LANCZOS)
        social.paste(leo, (680, 65 + (530 - leo.height) // 2), leo)
    social_path = output / 'social-preview.png'
    social.save(social_path, 'PNG', optimize=True)
    record('leo', social_path, 'Social composition with approved Leo, system rounded typography, and cream/peach gradient')

    source_records = {}
    for key, path in sources.items():
        with Image.open(path) as image:
            source_records[key] = {'path': str(path), 'sha256': source_hashes[key],
                                   'width': image.width, 'height': image.height,
                                   'unchanged_after_generation': digest(path) == source_hashes[key]}
        assert source_records[key]['unchanged_after_generation']
    manifest = {
        'purpose': 'Website-owned copies of approved Moodumi artwork and unmodified native app captures',
        'source_root': str(source_root), 'sources': source_records,
        'renditions': records,
        'generation': 'Pillow; proportional resizing, format optimization, and social typography only. No artwork redrawing.',
    }
    (output / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    total = sum(path.stat().st_size for path in output.iterdir() if path.is_file())
    print(json.dumps({'assets': len(records), 'total_bytes': total,
                      'critical_webp_bytes': {name: records[name]['bytes'] for name in ('leo-480.webp', 'leo-800.webp', 'garden.webp')},
                      'source_images_unchanged': True}, indent=2))


if __name__ == '__main__':
    main()
