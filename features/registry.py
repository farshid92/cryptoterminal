"""Feature registry source of truth."""

FEATURE_LIST = []


def register_feature(name):
    FEATURE_LIST.append(name)
    return name
