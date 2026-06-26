# myapp/templatetags/filters.py

from django import template

register = template.Library()
@register.filter
def to_range(start, end):
    return range(start, end)

@register.filter
def get_option(question, letter):
    if letter == "A":
        return question.option_a
    elif letter == "B":
        return question.option_b
    elif letter == "C":
        return question.option_c
    elif letter == "D":
        return question.option_d
    return ""
