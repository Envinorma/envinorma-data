from back_office.am_compare import _component_builder, CompareWith


def test_component_builder():
    for comp in CompareWith:
        _component_builder(comp)  # Ensuring always implemented
