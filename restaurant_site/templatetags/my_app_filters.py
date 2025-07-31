from django import template

register = template.Library()

@register.filter
def split(value, key):
    return value.split(key)


@register.filter
def multiplier(value, arg):
    try:
        return float(value) * float(arg)
    except:
        return ''
