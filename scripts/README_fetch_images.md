# Fetching Product Images for Spare Parts

This project includes a Django management command to source product images from a third-party API and store them in the database.

## Prerequisites

- Configure `MEDIA_ROOT` in Django settings and ensure the directory is writable.
- Obtain a Bing Image Search API key and set it in your environment:

```
export BING_SEARCH_KEY=your_bing_key_here
```

On Windows PowerShell:

```
$env:BING_SEARCH_KEY = "your_bing_key_here"
```

## Run the command

From the backend project directory (where `manage.py` lives):

```
python manage.py fetch_part_images --limit 100
```

Useful flags:

- `--all`: process all parts, not just those missing images
- `--dry-run`: show search results without downloading/saving
- `--query-template`: customize search keywords (default: `"{brand} {name} {sku} product"`)
- `--count`: number of images to fetch per part (default: 3)

## What it does

- Searches Bing Images using brand, name, and SKU.
- Downloads images to `MEDIA_ROOT/spare_parts/images/`.
- Creates `SparePartImage` records and marks the first image as primary when none exist.

## Notes

- Respect API rate limits; prefer smaller `--limit` batches.
- Validate results visually and adjust `--query-template` if needed for better relevance.
- If you later add a dedicated catalog image API, you can swap out the search provider inside `fetch_part_images.py`.