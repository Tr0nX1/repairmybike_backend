import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from vehicles.models import VehicleType, VehicleBrand, VehicleModel
from subscriptions.models import Plan
from spare_parts.models import SparePart
from services.models import Service


import json

results = {}

def check_model(model, field_name='image'):
    model_name = model.__name__
    print(f"Checking {model_name}...")
    try:
        qs = model.objects.exclude(**{f'{field_name}__startswith': 'http'}).exclude(**{f'{field_name}': ''})
        count = qs.count()
        items = []
        for obj in qs:
            val = getattr(obj, field_name)
            # handle if val is an ImageFieldFile
            path = val.name if hasattr(val, 'name') else str(val)
            items.append({'id': obj.id, 'path': path})
        
        results[model_name] = {
            'count': count,
            'items': items
        }
    except Exception as e:
        results[model_name] = {'error': str(e)}

check_model(VehicleType)
check_model(VehicleBrand)
check_model(VehicleModel)
check_model(Plan)

from spare_parts.models import SparePartImage, SparePartBrand, SparePartCategory
check_model(SparePartImage, 'image')
check_model(SparePartBrand, 'logo')
check_model(SparePartCategory, 'image')

check_model(Service, 'images')

with open('audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("Done.")
