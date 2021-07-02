from copy import copy

from envinorma.models import Annotations, Applicability, ArreteMinisteriel, StructuredText


def remove_null_attributes_in_section(paragraph: StructuredText) -> StructuredText:
    new_paragraph = copy(paragraph)
    del paragraph
    new_paragraph.annotations = new_paragraph.annotations or Annotations()
    new_paragraph.applicability = new_paragraph.applicability or Applicability()
    new_paragraph.sections = [remove_null_attributes_in_section(section) for section in new_paragraph.sections]
    return new_paragraph


def remove_null_attributes(am: ArreteMinisteriel) -> ArreteMinisteriel:
    am = copy(am)
    am.sections = [remove_null_attributes_in_section(section) for section in am.sections]
    return am
