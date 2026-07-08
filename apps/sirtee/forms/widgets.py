from django import forms


# ==========================================================
# TEXT
# ==========================================================

class TextInput(forms.TextInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        attrs.setdefault("autocomplete", "off")

        super().__init__(*args, **kwargs)


# ==========================================================
# EMAIL
# ==========================================================

class EmailInput(forms.EmailInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        attrs.setdefault("autocomplete", "off")

        super().__init__(*args, **kwargs)


# ==========================================================
# NUMBER
# ==========================================================

class NumberInput(forms.NumberInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# PASSWORD
# ==========================================================

class PasswordInput(forms.PasswordInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# TEXTAREA
# ==========================================================

class TextArea(forms.Textarea):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        attrs.setdefault("rows", 4)

        attrs.setdefault("autocomplete", "off")

        super().__init__(*args, **kwargs)


# ==========================================================
# SELECT
# ==========================================================

class Select(forms.Select):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault(
            "class",
            "form-select select2"
        )

        attrs.setdefault(
            "data-placeholder",
            "Seleccione..."
        )

        attrs.setdefault(
            "style",
            "width:100%;"
        )

        super().__init__(*args, **kwargs)


# ==========================================================
# MULTISELECT
# ==========================================================

class SelectMultiple(forms.SelectMultiple):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault(
            "class",
            "form-select select2"
        )

        attrs.setdefault(
            "style",
            "width:100%;"
        )

        super().__init__(*args, **kwargs)


# ==========================================================
# DATE
# ==========================================================

class DateInput(forms.DateInput):

    input_type = "date"

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# DATETIME
# ==========================================================

class DateTimeInput(forms.DateTimeInput):

    input_type = "datetime-local"

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# TIME
# ==========================================================

class TimeInput(forms.TimeInput):

    input_type = "time"

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# FILE
# ==========================================================

class FileInput(forms.ClearableFileInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault("class", "form-control")

        super().__init__(*args, **kwargs)


# ==========================================================
# CHECKBOX
# ==========================================================

class CheckboxInput(forms.CheckboxInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault(
            "class",
            "form-check-input"
        )

        super().__init__(*args, **kwargs)


# ==========================================================
# URL
# ==========================================================

class URLInput(forms.URLInput):

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault(
            "class",
            "form-control"
        )

        super().__init__(*args, **kwargs)


# ==========================================================
# TEL
# ==========================================================

class TelInput(forms.TextInput):

    input_type = "tel"

    def __init__(self, *args, **kwargs):

        attrs = kwargs.setdefault("attrs", {})

        attrs.setdefault(
            "class",
            "form-control"
        )

        super().__init__(*args, **kwargs)


# ==========================================================
# HIDDEN
# ==========================================================

class HiddenInput(forms.HiddenInput):
    pass