from django.db import connection, reset_queries
from spare_parts.models import SparePart
from spare_parts.serializers import SparePartListSerializer

# Reset query counter
reset_queries()

# Fetch spare parts with optimized queryset
parts = SparePart.objects.select_related('brand', 'category').prefetch_related('images').all()

# Serialize (this is where N+1 would happen without prefetch)
serializer = SparePartListSerializer(parts, many=True)
data = serializer.data

# Print query count
print(f"\n{'='*60}")
print(f"QUERY COUNT TEST")
print(f"{'='*60}")
print(f"Total queries executed: {len(connection.queries)}")
print(f"Total spare parts: {len(data)}")
print(f"\nExpected: ~3 queries (1 for parts, 1 for select_related, 1 for prefetch)")
print(f"Before fix: ~13 queries (1 + 10 for each part's images)")
print(f"{'='*60}\n")

# Show first few queries
if len(connection.queries) <= 5:
    print("Queries executed:")
    for i, query in enumerate(connection.queries, 1):
        print(f"\n{i}. {query['sql'][:200]}...")
