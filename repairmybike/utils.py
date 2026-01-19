from django.conf import settings

def build_absolute_media_url(url, request=None):
    """
    Ensures a media URL is absolute.
    Handles Cloudinary URLs and local media paths.
    """
    if not url:
        return None
    
    # 1. Already absolute
    if url.startswith('http://') or url.startswith('https://') or url.startswith('data:'):
        return url
        
    # 2. Check if we should use Cloudinary base
    use_cloudinary = getattr(settings, 'USE_CLOUDINARY', False)
    media_url = getattr(settings, 'MEDIA_URL', '/')
    
    if use_cloudinary and media_url.startswith('http'):
        # Prepend Cloudinary base if URL is relative
        return f"{media_url.rstrip('/')}/{url.lstrip('/')}"

    # 3. Fallback to Request-based absolute URI
    if request:
        try:
            return request.build_absolute_uri(url)
        except Exception:
            pass
            
    # 4. Final fallback to MEDIA_URL
    if media_url.startswith('http'):
        return f"{media_url.rstrip('/')}/{url.lstrip('/')}"
        
    return url
