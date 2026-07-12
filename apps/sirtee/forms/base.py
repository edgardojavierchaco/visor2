from django import forms


class SirteeBaseForm(forms.ModelForm):
    """
    Formulario base institucional SIRTEE.

    Características

    ✔ Bootstrap 5 automático
    ✔ Select2 automático
    ✔ Placeholders
    ✔ autocomplete="off"
    ✔ readonly
    ✔ autofocus
    ✔ Helpers reutilizables
    ✔ Bootstrap Validation
    """

    REQUIRED_CLASS = "required"

    SELECT2_CLASS = "select2"

    readonly_fields = []

    fieldsets = ()

    helper = None

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Evitar querysets cacheados
        for field in self.fields.values():

            if hasattr(field, "queryset") and field.queryset is not None:

                field.queryset = field.queryset.all()

        # IMPORTANTE:
        # configure_fields() NO se ejecuta aquí.
        #
        # Los formularios hijos pueden modificar choices,
        # querysets, widgets, etc.
        #
        # Deben llamar manualmente a:
        #
        #     self.configure_fields()
        #
        # al FINAL de su __init__.

        self.configure_readonly_fields()

        self.configure_autofocus()

    # =====================================================
    # CONFIGURACIÓN GENERAL
    # =====================================================

    def configure_fields(self):

        for name, field in self.fields.items():

            widget = field.widget

            attrs = widget.attrs.copy()

            attrs.setdefault(
                "autocomplete",
                "off"
            )

            # --------------------------------------------
            # PLACEHOLDER
            # --------------------------------------------

            if isinstance(

                widget,

                (
                    forms.TextInput,
                    forms.EmailInput,
                    forms.NumberInput,
                    forms.URLInput,
                    forms.PasswordInput,
                ),

            ):

                if field.label:

                    attrs.setdefault(
                        "placeholder",
                        str(field.label)
                    )

            # --------------------------------------------
            # CHECKBOX
            # --------------------------------------------

            if isinstance(
                widget,
                forms.CheckboxInput
            ):

                css = "form-check-input"

            # --------------------------------------------
            # SELECT
            # --------------------------------------------

            elif isinstance(

                widget,

                (
                    forms.Select,
                    forms.SelectMultiple,
                ),

            ):

                css = f"form-select {self.SELECT2_CLASS}"

                attrs.setdefault(
                    "data-placeholder",
                    "Seleccione..."
                )

                attrs.setdefault(
                    "data-width",
                    "100%"
                )

                attrs.setdefault(
                    "data-allow-clear",
                    "true"
                )

            # --------------------------------------------
            # TEXTAREA
            # --------------------------------------------

            elif isinstance(
                widget,
                forms.Textarea
            ):

                css = "form-control"

                attrs.setdefault(
                    "rows",
                    4
                )

            # --------------------------------------------
            # FILE
            # --------------------------------------------

            elif isinstance(

                widget,

                (
                    forms.FileInput,
                    forms.ClearableFileInput,
                ),

            ):

                css = "form-control"

            # --------------------------------------------
            # DATE
            # --------------------------------------------

            elif isinstance(

                widget,

                (
                    forms.DateInput,
                    forms.DateTimeInput,
                ),

            ):

                css = "form-control"

            # --------------------------------------------
            # NUMBER
            # --------------------------------------------

            elif isinstance(
                widget,
                forms.NumberInput
            ):

                css = "form-control"

            # --------------------------------------------
            # EMAIL
            # --------------------------------------------

            elif isinstance(
                widget,
                forms.EmailInput
            ):

                css = "form-control"

            # --------------------------------------------
            # URL
            # --------------------------------------------

            elif isinstance(
                widget,
                forms.URLInput
            ):

                css = "form-control"

            # --------------------------------------------
            # DEFAULT
            # --------------------------------------------

            else:

                css = "form-control"

            actual = attrs.get(
                "class",
                ""
            )

            attrs["class"] = (
                f"{actual} {css}"
            ).strip()

            # --------------------------------------------
            # REQUIRED
            # --------------------------------------------

            if field.required:

                attrs["required"] = True

                attrs["class"] += (
                    f" {self.REQUIRED_CLASS}"
                )

            # --------------------------------------------
            # HELP TEXT
            # --------------------------------------------

            if field.help_text:

                attrs.setdefault(

                    "aria-describedby",

                    f"id_{name}_help"

                )

            widget.attrs = attrs

        # --------------------------------------------
        # Bootstrap Validation
        #
        # IMPORTANTE:
        # Sólo agregar clases cuando Django
        # ya generó errores
        # --------------------------------------------
        errors = getattr(self, "_errors", None)

        if errors:

            for field_name in errors:

                if field_name in self.fields:

                    css = self.fields[field_name].widget.attrs.get(
                        "class",
                        ""
                    )

                    self.fields[field_name].widget.attrs[
                        "class"
                    ] = f"{css} is-invalid"
        

    # =====================================================
    # READONLY
    # =====================================================

    def configure_readonly_fields(self):

        for field_name in self.readonly_fields:

            if field_name in self.fields:

                self.fields[field_name].disabled = True

    # =====================================================
    # AUTOFOCUS
    # =====================================================

    def configure_autofocus(self):

        for field in self.fields.values():

            if not field.disabled:

                field.widget.attrs.setdefault(
                    "autofocus",
                    True
                )

                break

    # =====================================================
    # HELPERS
    # =====================================================

    def add_css(self, field_name, css):

        if field_name not in self.fields:
            return

        actual = self.fields[field_name].widget.attrs.get(
            "class",
            ""
        )

        self.fields[field_name].widget.attrs["class"] = (
            f"{actual} {css}"
        ).strip()

    def remove_css(self, field_name, css):

        if field_name not in self.fields:
            return

        clases = self.fields[field_name].widget.attrs.get(
            "class",
            ""
        ).split()

        clases = [

            c

            for c in clases

            if c != css

        ]

        self.fields[field_name].widget.attrs["class"] = " ".join(clases)

    def set_placeholder(self, field_name, text):

        if field_name in self.fields:

            self.fields[field_name].widget.attrs["placeholder"] = text

    def set_help(self, field_name, text):

        if field_name in self.fields:

            self.fields[field_name].help_text = text

    def autofocus(self, field_name):

        if field_name in self.fields:

            self.fields[field_name].widget.attrs["autofocus"] = True

    def readonly(self, field_name):

        if field_name in self.fields:

            self.fields[field_name].widget.attrs["readonly"] = True

    def disable(self, field_name):

        if field_name in self.fields:

            self.fields[field_name].disabled = True

    def disable_all(self):

        for field in self.fields.values():

            field.disabled = True

    def hide(self, field_name):

        if field_name in self.fields:

            self.fields[field_name].widget = forms.HiddenInput()

    def set_rows(self, field_name, rows=4):

        if field_name in self.fields:

            widget = self.fields[field_name].widget

            if isinstance(widget, forms.Textarea):

                widget.attrs["rows"] = rows

    def set_cols(self, field_name, cols=50):

        if field_name in self.fields:

            widget = self.fields[field_name].widget

            if isinstance(widget, forms.Textarea):

                widget.attrs["cols"] = cols

    def set_required(self, field_name, required=True):

        if field_name in self.fields:

            self.fields[field_name].required = required

    def initial_value(self, field_name, value):

        if field_name in self.fields:

            self.fields[field_name].initial = value

    def empty_label(self, field_name, text="---------"):

        if field_name in self.fields:

            field = self.fields[field_name]

            if hasattr(field, "empty_label"):

                field.empty_label = text

    def order_fields(self, field_order):

        if not field_order:
            return

        self.fields = {

            k: self.fields[k]

            for k in field_order

            if k in self.fields

        }

    def set_select2(self, field_name):

        if field_name not in self.fields:
            return

        widget = self.fields[field_name].widget

        css = widget.attrs.get(
            "class",
            ""
        )

        widget.attrs["class"] = (
            f"{css} {self.SELECT2_CLASS}"
        ).strip()

    def required_fields(self):

        return [

            name

            for name, field in self.fields.items()

            if field.required

        ]

    # =====================================================
    # VALIDACIÓN GENERAL
    # =====================================================

    def clean(self):

        return super().clean()