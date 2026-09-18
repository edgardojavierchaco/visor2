(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var modal = document.querySelector('[data-biblioteca-guia-modal]');
        var triggers = document.querySelectorAll('[data-biblioteca-guia-abrir]');

        if (!modal || !triggers.length) {
            return;
        }

        var dialog = modal.querySelector('[data-biblioteca-guia-dialog]');
        var closeButtons = modal.querySelectorAll('[data-biblioteca-guia-cerrar]');
        var previousFocus = null;
        var bodyAlreadyLocked = false;
        var focusableSelector = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])'
        ].join(',');

        function getFocusableElements() {
            return Array.prototype.slice.call(modal.querySelectorAll(focusableSelector)).filter(function (element) {
                return element.offsetParent !== null;
            });
        }

        function openModal(event) {
            previousFocus = event.currentTarget;
            bodyAlreadyLocked = document.body.classList.contains('biblioteca-guia-modal-abierta');
            modal.hidden = false;
            modal.setAttribute('aria-hidden', 'false');
            document.body.classList.add('biblioteca-guia-modal-abierta');

            var focusableElements = getFocusableElements();
            if (focusableElements.length) {
                focusableElements[0].focus();
            }
        }

        function closeModal() {
            if (modal.hidden) {
                return;
            }

            modal.hidden = true;
            modal.setAttribute('aria-hidden', 'true');
            if (!bodyAlreadyLocked) {
                document.body.classList.remove('biblioteca-guia-modal-abierta');
            }

            if (previousFocus && document.contains(previousFocus)) {
                previousFocus.focus();
            }
        }

        function handleModalKeydown(event) {
            if (modal.hidden) {
                return;
            }

            if (event.key === 'Escape') {
                event.preventDefault();
                closeModal();
                return;
            }

            if (event.key !== 'Tab') {
                return;
            }

            var focusableElements = getFocusableElements();
            if (!focusableElements.length) {
                event.preventDefault();
                return;
            }

            var firstElement = focusableElements[0];
            var lastElement = focusableElements[focusableElements.length - 1];

            if (event.shiftKey && document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            } else if (!event.shiftKey && document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }

        Array.prototype.forEach.call(triggers, function (trigger) {
            trigger.addEventListener('click', openModal);
        });

        Array.prototype.forEach.call(closeButtons, function (button) {
            button.addEventListener('click', closeModal);
        });

        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });

        dialog.addEventListener('click', function (event) {
            event.stopPropagation();
        });

        document.addEventListener('keydown', handleModalKeydown);
    });
}());
