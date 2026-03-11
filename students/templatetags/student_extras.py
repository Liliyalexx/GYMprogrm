from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Look up a dict value by variable key: {{ my_dict|get_item:variable }}"""
    if not dictionary:
        return None
    return dictionary.get(key)
