from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from .forms import DynamicForm, FormFieldFormSet, FormForm
from .models import Form, FormResponse, FormResponseFile
from .utils import export_excel, export_pdf

# Only staff users may reach the admin-side views. Redirects to settings.LOGIN_URL.
staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff)


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ---------------------------------------------------------------------------
# ADMIN SIDE
# ---------------------------------------------------------------------------
@login_required
@staff_required
def form_list(request):
    forms = Form.objects.all()
    return render(request, "formbuilder/form_list.html", {"forms": forms})


@login_required
@staff_required
def form_create(request):
    if request.method == "POST":
        form = FormForm(request.POST)
        formset = FormFieldFormSet(request.POST, instance=Form())
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                obj = form.save()
                formset.instance = obj
                _save_fields(formset)
            messages.success(request, "Form created.")
            return redirect("formbuilder:form_list")
    else:
        form = FormForm()
        formset = FormFieldFormSet(instance=Form())
    return render(
        request,
        "formbuilder/form_form.html",
        {"form": form, "formset": formset, "mode": "create"},
    )


@login_required
@staff_required
def form_edit(request, pk):
    obj = get_object_or_404(Form, pk=pk)
    if request.method == "POST":
        form = FormForm(request.POST, instance=obj)
        formset = FormFieldFormSet(request.POST, instance=obj)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                _save_fields(formset)
            messages.success(request, "Form updated.")
            return redirect("formbuilder:form_list")
    else:
        form = FormForm(instance=obj)
        formset = FormFieldFormSet(instance=obj)
    return render(
        request,
        "formbuilder/form_form.html",
        {"form": form, "formset": formset, "mode": "edit", "object": obj},
    )


def _save_fields(formset):
    """Persist fields and rewrite `order` from their position on the page.

    `order` is kept in a hidden input maintained by the drag/add JS.
    """
    instances = formset.save(commit=False)
    for obj in formset.deleted_objects:
        obj.delete()
    # set order on every live form (same object refs as `instances`)
    for f in formset.forms:
        if f in formset.deleted_forms:
            continue
        if (f.instance.label or "").strip():
            f.instance.order = f.cleaned_data.get("order") or 0
    for inst in instances:
        if (inst.label or "").strip():
            inst.save()
    formset.save_m2m()


@login_required
@staff_required
@require_POST
def form_toggle_publish(request, pk):
    obj = get_object_or_404(Form, pk=pk)
    obj.is_published = not obj.is_published
    obj.save(update_fields=["is_published", "updated_at"])
    state = "published" if obj.is_published else "unpublished"
    messages.success(request, f"“{obj.title}” {state}.")
    return redirect("formbuilder:form_list")


@login_required
@staff_required
def form_delete(request, pk):
    obj = get_object_or_404(Form, pk=pk)
    if request.method == "POST":
        title = obj.title
        obj.delete()
        messages.success(request, f"“{title}” deleted.")
        return redirect("formbuilder:form_list")
    return render(request, "formbuilder/form_confirm_delete.html", {"object": obj})


@login_required
@staff_required
def form_data(request, pk):
    obj = get_object_or_404(Form, pk=pk)
    fields = list(obj.ordered_fields)
    responses = obj.responses.all().prefetch_related("files")

    # Build display rows: each cell knows its field so the template stays simple
    rows = []
    for resp in responses:
        cells = [
            {"value": resp.value_for(f), "is_file": f.is_file} for f in fields
        ]
        rows.append({"resp": resp, "cells": cells})

    # Simple analytics for choice fields
    analytics = []
    for f in fields:
        if f.is_choice:
            counter = Counter()
            for resp in responses:
                val = resp.data.get(f.field_name)
                if isinstance(val, list):
                    counter.update(val)
                elif val:
                    counter.update([val])
            total = sum(counter.values()) or 1
            analytics.append(
                {
                    "label": f.label,
                    "items": [
                        {"name": k, "count": v, "pct": round(v * 100 / total, 1)}
                        for k, v in counter.most_common()
                    ],
                }
            )
    analytics_json = json.dumps(analytics)

    return render(
        request,
        "formbuilder/form_data.html",
        {
            "object": obj,
            "fields": fields,
            "rows": rows,
            "count": responses.count(),
            "analytics": analytics,
            "analytics_json": analytics_json, 
        },
    )


@login_required
@staff_required
def response_delete(request, pk, resp_pk):
    obj = get_object_or_404(Form, pk=pk)
    resp = get_object_or_404(FormResponse, pk=resp_pk, form=obj)
    if request.method == "POST":
        resp.delete()
        messages.success(request, "Response deleted.")
    return redirect("formbuilder:form_data", pk=pk)


@login_required
@staff_required
def form_export(request, pk, fmt):
    obj = get_object_or_404(Form, pk=pk)
    if fmt == "xlsx":
        return export_excel(obj)
    if fmt == "pdf":
        return export_pdf(obj)
    messages.error(request, "Unknown export format.")
    return redirect("formbuilder:form_data", pk=pk)


# ---------------------------------------------------------------------------
# PUBLIC SIDE
# ---------------------------------------------------------------------------
def form_fill(request, slug):
    obj = get_object_or_404(Form, slug=slug)

    if not obj.is_published:
        return render(request, "formbuilder/public/form_closed.html", {"object": obj})

    if request.method == "POST":
        dform = DynamicForm(request.POST, request.FILES, form_instance=obj)
        if dform.is_valid():
            _save_response(request, obj, dform)
            return redirect("formbuilder:form_success", slug=obj.slug)
    else:
        dform = DynamicForm(form_instance=obj)

    constraints = {}
    for f in obj.ordered_fields:
        constraints[f.field_name] = {
            "required": f.required,
            "min_length": f.min_length,
            "max_length": f.max_length,
            "validation_type": f.validation_type,   # none | numeric | alpha | alphanumeric
            "field_type": f.field_type,
        }

    return render(
        request,
        "formbuilder/public/form_fill.html",
        {"object": obj, "dform": dform, "constraints_json": json.dumps(constraints)},
    )


@transaction.atomic
def _save_response(request, obj, dform):
    data = {}
    file_map = {}
    for f in obj.ordered_fields:
        val = dform.cleaned_data.get(f.field_name)
        if f.is_file:
            if val:
                file_map[f] = val
            continue
        if hasattr(val, "isoformat"):  # date / datetime
            val = val.isoformat()
        data[f.field_name] = val

    resp = FormResponse.objects.create(
        form=obj, data=data, ip_address=_client_ip(request)
    )
    for field, uploaded in file_map.items():
        FormResponseFile.objects.create(response=resp, field=field, file=uploaded)


def form_success(request, slug):
    obj = get_object_or_404(Form, slug=slug)
    return render(request, "formbuilder/public/form_success.html", {"object": obj})

@login_required
@staff_required
@require_POST
def form_toggle_pin(request, pk):
    obj = get_object_or_404(Form, pk=pk)
    obj.is_pinned = not obj.is_pinned
    obj.save(update_fields=["is_pinned", "updated_at"])
    state = "pinned" if obj.is_pinned else "unpinned"
    messages.success(request, f"“{obj.title}” {state}.")
    return redirect("formbuilder:form_list")