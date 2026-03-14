import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.conf import settings
from descope import DescopeClient

def debug_descope_mgmt():
    try:
        project_id = settings.DESCOPE_PROJECT_ID
        mgmt_key = settings.DESCOPE_MANAGEMENT_KEY
        
        client = DescopeClient(project_id=project_id, management_key=mgmt_key)
        
        print("--- Loading All Roles ---")
        roles_resp = client.mgmt.role.load_all()
        print(json.dumps(roles_resp, indent=2))
        
        print("\n--- Loading All Permissions ---")
        perms_resp = client.mgmt.permission.load_all()
        print(json.dumps(perms_resp, indent=2))
        
        # Testing with the specific user ID we found earlier
        user_id = "U35qReEXYDHb4hycSwccinTsNQlK"
        print(f"\n--- Loading User Details for {user_id} ---")
        user_resp = client.mgmt.user.load(user_id=user_id)
        print(json.dumps(user_resp, indent=2))
        
    except Exception as e:
        print(f"Error debugging Descope: {e}")

if __name__ == "__main__":
    debug_descope_mgmt()
