from envinorma.back_office.am_compare import CompareWith, _component_builder


def test_component_builder():
    for comp in CompareWith:
        _component_builder(comp)  # Ensuring always implemented
