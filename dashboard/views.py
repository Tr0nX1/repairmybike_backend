from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from .utils import get_dashboard_metrics, get_recent_activity

class DashboardHomeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/index.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metrics'] = get_dashboard_metrics()
        context['activities'] = get_recent_activity()
        context['title'] = "RepairMyBike - Staff Command Center"
        return context
