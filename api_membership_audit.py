import os
import django
import json
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.test import Client

def audit_membership_api():
    client = Client()
    
    endpoints = [
        '/api/subscriptions/plans/',
        '/api/subscriptions/subscriptions/',
    ]
    
    results = {
        "audit_title": "Membership API Audit",
        "endpoints": []
    }
    
    for url in endpoints:
        endpoint_result = {
            "request": f"GET {url}",
            "status_code": None,
            "headers": {},
            "body": None,
            "error": None
        }
        
        try:
            response = client.get(url)
            endpoint_result["status_code"] = response.status_code
            
            # Use response.headers if available (Django 3.2+), else response.items()
            headers = getattr(response, 'headers', response)
            for key, value in headers.items():
                endpoint_result["headers"][key] = str(value)
            
            try:
                # Try to parse as JSON
                endpoint_result["body"] = response.json()
            except Exception:
                try:
                    endpoint_result["body"] = json.loads(response.content.decode('utf-8'))
                except:
                    endpoint_result["body"] = response.content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            endpoint_result["error"] = str(e)
            
        results["endpoints"].append(endpoint_result)

    # Write results to a UTF-8 JSON file
    output_file = 'membership_api_audit_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dumps(results, indent=4, ensure_ascii=False)
        # Wait, I need to actually write it
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Audit completed. Results written to {output_file}")

if __name__ == "__main__":
    audit_membership_api()
