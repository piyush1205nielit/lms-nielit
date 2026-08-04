from django import template

register = template.Library()

@register.filter
def format_duration(total_seconds):
    if not total_seconds:
        return "—"
    total_seconds = int(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"

@register.filter
def get_item(dictionary, key):
    """Enables dict lookup by a variable key inside templates, e.g. {{ mydict|get_item:some_var }}."""
    if dictionary is None:
        return None
    return dictionary.get(str(key))