from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView, DetailView, UpdateView

from core.constants import Permissions
from core.forms import ContractForm, ContractFormEdit, PartnerRoleForm
from core.forms.contract import KVForm
from core.forms.document import DocumentForm
from core.models import Contract, PartnerRole
from core.permissions import permission_required
from . import facet_view_utils

FACET_FIELDS = settings.FACET_FIELDS['contract']
from core.models.utils import COMPANY


class ContractCreateView(CreateView):
    model = Contract
    template_name = 'contracts/contract_form.html'
    form_class = ContractForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update({'user': self.request.user})
        return initial

    def get_success_url(self):
        return reverse_lazy('contract', kwargs={'pk': self.object.id})


class ContractListView(ListView):
    model = Contract
    template_name = 'contracts/contract_list.html'
    get_objects_for_user_extra_kwargs = {'use_groups': True}


class ContractDetailView(DetailView):
    model = Contract
    template_name = 'contracts/contract.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        the_user = self.request.user
        can_edit = the_user.can_edit_contract(self.object)
        context['can_edit'] = can_edit
        context['company_name'] = COMPANY
        pk = ContentType.objects.get(model='contract').pk
        context['content_type'] = pk
        context['object_id'] = self.object.pk
        context['datafiles'] = [d for d in self.object.legal_documents.all()]

        return context


class ContractEditView(UpdateView):
    model = Contract
    template_name = 'contracts/contract_form_edit.html'
    form_class = ContractFormEdit

    def dispatch(self, request, *args, **kwargs):
        the_contract = Contract.objects.get(id=kwargs.get('pk'))
        the_user = request.user
        can_edit = the_user.can_edit_contract(the_contract)
        if can_edit:
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_initial(self):
        initial = super().get_initial()
        initial.update({'user': self.request.user})
        return initial

    def get_success_url(self):
        return reverse_lazy('contract', kwargs={'pk': self.object.id})


def contract_list(request):
    query = request.GET.get('query')
    order_by = request.GET.get('order_by')
    contracts = facet_view_utils.search_objects(
        request,
        filters=request.GET.getlist('filters'),
        query=query,
        object_model=Contract,
        facets=FACET_FIELDS,
        order_by=order_by
    )
    return render(request, 'search/search_page.html', {
        'reset': True,
        'facets': facet_view_utils.filter_empty_facets(contracts.facet_counts()),
        'query': query or '',
        'title': 'Contracts',
        'help_text' : Contract.AppMeta.help_text,
        'search_url': 'contracts',
        'add_url': 'contract_add',
        'data': {'contracts': contracts},
        'results_template_name': 'search/_items/contracts.html',
        'company_name': COMPANY,
        'order_by_fields': [
            ('Contact', 'contact'),
            ('Project', 'project')
        ]
    })


class PartnerRoleCreateView(CreateView):
    model = PartnerRole
    template_name = 'contracts/partner_role_form.html'
    form_class = PartnerRoleForm

    def dispatch(self, request, *args, **kwargs):
        self.contract = Contract.objects.get(id=kwargs.get('pk'))
        the_user = request.user
        can_edit = the_user.can_edit_contract(self.contract)
        if can_edit:
            return super().dispatch(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_initial(self):
        initial = super().get_initial()
        contract_id = self.kwargs.get('pk')
        initial.update({'user': self.request.user})
        if contract_id:
            initial.update({'contract': contract_id})
        return initial

    def get_success_url(self):
        return reverse_lazy('contract', kwargs={'pk': self.contract.id})

    def form_valid(self, form):
        response = super().form_valid(form)
        return response


@require_http_methods(["DELETE"])
def partner_role_delete(request, pk):
    partner_role = get_object_or_404(PartnerRole, id=pk)
    partner_role.delete()
    return HttpResponse("Partner (signatory) removed from contract.")
