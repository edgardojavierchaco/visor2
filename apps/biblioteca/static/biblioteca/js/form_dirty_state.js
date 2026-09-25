(function (window, document, $) {
    'use strict';

    var FORM_SELECTOR = '.biblioteca-crud--formulario .biblioteca-crud__form';
    var IGNORE_NAMES = {
        csrfmiddlewaretoken: true,
        action: true
    };

    function resolveForm(target) {
        if (!target) {
            return null;
        }

        if (target.tagName === 'FORM') {
            return target;
        }

        if (target.form) {
            return target.form;
        }

        return target.closest ? target.closest('form') : null;
    }

    function getSubmitButton(form) {
        return form ? form.querySelector('button[type="submit"], input[type="submit"]') : null;
    }

    function controlSignature(control) {
        var type = String(control.type || '').toLowerCase();

        if (type === 'checkbox' || type === 'radio') {
            return [control.name, type, String(control.value || ''), Boolean(control.checked)];
        }

        if (type === 'file') {
            var files = Array.prototype.map.call(control.files || [], function (file) {
                return [file.name, file.size, file.lastModified];
            });
            return [control.name, type, files];
        }

        if (control.tagName === 'SELECT' && control.multiple) {
            var selected = Array.prototype.filter.call(control.options || [], function (option) {
                return option.selected;
            }).map(function (option) {
                return option.value;
            });

            return [control.name, 'select-multiple', selected];
        }

        return [control.name, type, String(control.value == null ? '' : control.value)];
    }

    function formSignature(form) {
        var values = [];

        Array.prototype.forEach.call(form.elements || [], function (control) {
            if (!control || !control.name || control.disabled || IGNORE_NAMES[control.name]) {
                return;
            }

            var type = String(control.type || '').toLowerCase();

            if (
                type === 'submit' ||
                type === 'button' ||
                type === 'reset' ||
                type === 'image'
            ) {
                return;
            }

            values.push(controlSignature(control));
        });

        return JSON.stringify(values);
    }

    function applyEditState(state) {
        if (!state || !state.isEdit) {
            return;
        }

        state.dirty = formSignature(state.form) !== state.initialSignature;
        state.form.setAttribute(
            'data-biblioteca-edit-pristine',
            state.dirty ? 'false' : 'true'
        );

        state.submit.disabled = Boolean(
            state.initiallyDisabled ||
            state.validationBlocked ||
            !state.dirty
        );
    }

    function initForm(form) {
        if (!form || !form.matches(FORM_SELECTOR)) {
            return null;
        }

        if (form._bibliotecaFormState) {
            return form._bibliotecaFormState;
        }

        var actionInput = form.querySelector('input[name="action"]');
        var submit = getSubmitButton(form);

        if (!actionInput || !submit) {
            return null;
        }

        var state = {
            form: form,
            submit: submit,
            isEdit: actionInput.value === 'edit',
            initiallyDisabled: Boolean(submit.disabled),
            validationBlocked: false,
            dirty: false,
            initialSignature: ''
        };

        form._bibliotecaFormState = state;

        if (!state.isEdit) {
            return state;
        }

        state.initialSignature = formSignature(form);
        applyEditState(state);

        if ($ && $.fn) {
            $(form).on(
                'input.bibliotecaEditState change.bibliotecaEditState',
                ':input',
                function () {
                    applyEditState(state);
                }
            );
        } else {
            form.addEventListener('input', function () {
                applyEditState(state);
            });
            form.addEventListener('change', function () {
                applyEditState(state);
            });
        }

        return state;
    }

    function initAll() {
        document.querySelectorAll(FORM_SELECTOR).forEach(initForm);
    }

    window.biblioteca_form_state = {
        setValidationValid: function (target, valid) {
            var form = resolveForm(target);
            var state = initForm(form);
            var submit = state ? state.submit : getSubmitButton(form);

            if (!submit) {
                return;
            }

            if (!state || !state.isEdit) {
                submit.disabled = !valid;
                return;
            }

            state.validationBlocked = !valid;
            applyEditState(state);
        },

        refresh: function (target) {
            var form = resolveForm(target);
            var state = initForm(form);

            if (state && state.isEdit) {
                applyEditState(state);
            }
        },

        isDirty: function (target) {
            var form = resolveForm(target);
            var state = initForm(form);

            if (!state || !state.isEdit) {
                return false;
            }

            applyEditState(state);
            return state.dirty;
        }
    };

    document.addEventListener('submit', function (event) {
        var form = event.target;
        var state = initForm(form);

        if (!state || !state.isEdit) {
            return;
        }

        applyEditState(state);

        if (
            !state.dirty ||
            state.validationBlocked ||
            state.initiallyDisabled
        ) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    }, true);

    initAll();
})(window, document, window.jQuery);
