from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from .models import Course, Domain


def _resync(domains_qs):
    for domain in domains_qs:
        domain.sync_active_status()


@receiver(m2m_changed, sender=Course.domains.through)
def sync_domains_on_m2m_change(sender, instance, action, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if pk_set:
        _resync(Domain.objects.filter(id__in=pk_set))
    else:
        # post_clear gives no pk_set (we don't know which domains were removed) —
        # re-syncing everything is cheap at this scale and always correct
        _resync(Domain.objects.all())


@receiver(post_save, sender=Course)
def sync_domains_on_course_save(sender, instance, **kwargs):
    # covers a course flipping between active/inactive status
    _resync(instance.domains.all())


@receiver(post_delete, sender=Course)
def sync_domains_on_course_delete(sender, instance, **kwargs):
    _resync(Domain.objects.all())