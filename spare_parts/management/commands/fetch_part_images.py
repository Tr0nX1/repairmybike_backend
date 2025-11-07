import os
import logging
import mimetypes
import pathlib
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from ...models import SparePart, SparePartImage


logger = logging.getLogger(__name__)


def _safe_filename(base: str, ext: str) -> str:
    base = base.strip().replace(' ', '_')
    # Remove characters not suitable for filenames
    keep = "-_.()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    base = ''.join(c for c in base if c in keep)
    if not ext.startswith('.'):
        ext = f'.{ext}'
    return f"{base}{ext}".lower()


def _detect_extension(url: str, content_type: str | None) -> str:
    # Prefer MIME type
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(';')[0].strip())
        if guessed:
            return guessed
    # Fallback to URL
    path = pathlib.PurePosixPath(url)
    ext = path.suffix
    if ext:
        return ext
    # Default to .jpg
    return '.jpg'


class Command(BaseCommand):
    help = "Fetch product images for SparePart records using Bing Image Search and store them in DB"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Max number of parts to process')
        parser.add_argument('--all', action='store_true', help='Process all parts, not only those missing images')
        parser.add_argument('--dry-run', action='store_true', help='Search but do not download/save')
        parser.add_argument('--query-template', type=str, default='{brand} {name} {sku} product',
                            help='Template for search query')
        parser.add_argument('--count', type=int, default=3, help='Max images to fetch per part (1-3 recommended)')

    def handle(self, *args, **options):
        api_key = os.getenv('BING_SEARCH_KEY')
        if not api_key:
            raise CommandError('BING_SEARCH_KEY environment variable is required')

        query_template: str = options['query_template']
        limit: int = options['limit']
        process_all: bool = options['all']
        dry_run: bool = options['dry_run']
        count: int = max(1, min(int(options['count']), 5))

        qs = SparePart.objects.all()
        if not process_all:
            qs = qs.filter(images__isnull=True)
        qs = qs.order_by('id')[:limit]

        if not qs.exists():
            self.stdout.write(self.style.WARNING('No parts to process. Use --all to consider every part.'))
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            raise CommandError('MEDIA_ROOT must be configured to save images')

        save_dir = os.path.join(media_root, 'spare_parts', 'images')
        os.makedirs(save_dir, exist_ok=True)

        for part in qs:
            brand = part.brand.name if part.brand else ''
            query = query_template.format(brand=brand, name=part.name, sku=part.sku)
            self.stdout.write(f"Searching images for: {query}")

            try:
                results = self._bing_image_search(api_key, query, count=count)
            except Exception as e:
                logger.exception('Search failed: %s', e)
                self.stdout.write(self.style.ERROR(f"Search failed: {e}"))
                continue

            if not results:
                self.stdout.write(self.style.WARNING('No images found'))
                continue

            # If images already exist, don't mark additional as primary
            has_images = part.images.exists()

            for idx, item in enumerate(results):
                url = item.get('contentUrl') or item.get('thumbnailUrl')
                if not url:
                    continue

                if dry_run:
                    self.stdout.write(f"[dry-run] Found: {url}")
                    continue

                try:
                    resp = requests.get(url, timeout=15)
                    resp.raise_for_status()
                except Exception as e:
                    logger.warning('Download failed for %s: %s', url, e)
                    continue

                ext = _detect_extension(url, resp.headers.get('Content-Type'))
                fname = _safe_filename(f"{part.slug or part.sku}_{idx}", ext)
                dest_path = os.path.join(save_dir, fname)

                with open(dest_path, 'wb') as f:
                    f.write(resp.content)

                # Save to model (FileField requires relative path under MEDIA_ROOT)
                rel_path = os.path.join('spare_parts', 'images', fname).replace('\\', '/')
                img = SparePartImage(spare_part=part, is_primary=False, sort_order=idx)
                img.image.save(fname, ContentFile(resp.content), save=True)
                # The above save sets correct storage; ensure path aligns
                if not img.image.name:
                    img.image.name = rel_path
                    img.save(update_fields=['image'])

                self.stdout.write(self.style.SUCCESS(f"Saved image: {rel_path}"))

            # Mark first image as primary if none existed
            if not has_images and part.images.exists():
                first = part.images.order_by('sort_order').first()
                if first:
                    first.is_primary = True
                    first.save(update_fields=['is_primary'])
                    self.stdout.write(self.style.SUCCESS('Marked first image as primary'))

    def _bing_image_search(self, api_key: str, query: str, count: int = 3):
        url = f"https://api.bing.microsoft.com/v7.0/images/search?q={quote_plus(query)}&safeSearch=Strict&count={count}&imageType=Photo"
        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get('value', [])