from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review
from services.models import Service
from spare_parts.models import SparePart

def update_aggregate_rating(content_type, object_id):
    if not content_type or not object_id:
        return

    # Filter all reviews for this target
    reviews = Review.objects.filter(content_type=content_type, object_id=object_id)
    stats = reviews.aggregate(avg_rating=Avg('rating'), count=Count('id'))
    
    avg = stats['avg_rating'] or 0
    cnt = stats['count'] or 0

    model_class = content_type.model_class()
    if model_class == Service:
        Service.objects.filter(id=object_id).update(rating=avg, reviews_count=cnt)
    elif model_class == SparePart:
        SparePart.objects.filter(id=object_id).update(rating_average=avg, rating_count=cnt)

@receiver(post_save, sender=Review)
def handle_review_save(sender, instance, **kwargs):
    update_aggregate_rating(instance.content_type, instance.object_id)

@receiver(post_delete, sender=Review)
def handle_review_delete(sender, instance, **kwargs):
    update_aggregate_rating(instance.content_type, instance.object_id)
