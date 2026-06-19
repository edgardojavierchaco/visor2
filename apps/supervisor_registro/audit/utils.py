from django.forms.models import model_to_dict


def snapshot(instance):
    if not instance:
        return None

    return model_to_dict(instance)

