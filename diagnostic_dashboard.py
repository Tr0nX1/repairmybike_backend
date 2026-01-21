import os
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from dashboard.utils import get_dashboard_metrics, get_recent_activity

def diagnostic_test():
    print("--- Dashboard Logic Diagnostic ---")
    try:
        metrics = get_dashboard_metrics()
        print("\n[METRICS DATA]")
        print(json.dumps(metrics, indent=4))
        
        # Test the specific values used in "Today's Progress"
        today_view = metrics.get('today_view', {})
        print("\n[TODAY'S PROGRESS SECTION]")
        print(f"Completed: {today_view.get('completed')}")
        print(f"Total Bookings: {today_view.get('total_bookings')}")
        print(f"Progress %: {today_view.get('progress_percent')}%")
        
        activities = get_recent_activity()
        print("\n[RECENT ACTIVITY FEED]")
        print(f"Item Count: {len(activities)}")
        if activities:
            print("First Item Sample:")
            print(json.dumps(activities[0], indent=4, default=str))

    except Exception as e:
        print(f"\n[ERROR] diagnostic failed: {e}")

if __name__ == "__main__":
    diagnostic_test()
