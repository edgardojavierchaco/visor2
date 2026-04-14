# Ruta a Sphinx
SPHINXOPTS    ?=  # Opciones para Sphinx (puede estar vacío)
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Objetivo por defecto: generar documentación HTML
html:
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html
	@echo "Documentación HTML generada en $(BUILDDIR)/html."

# Limpiar los archivos generados
clean:
	rm -rf $(BUILDDIR)/*
	@echo "Archivos de la documentación limpiados."

# Generar documentación en PDF (usando LaTeX)
pdf:
	$(SPHINXBUILD) -b latex $(SOURCEDIR) $(BUILDDIR)/latex
	@echo "Documentación en LaTeX generada en $(BUILDDIR)/latex."

# Regenerar la documentación (limpiar y generar de nuevo)
rebuild: clean html

.PHONY: html clean pdf rebuild

# Ayuda: Mostrar comandos disponibles
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

.PHONY: help Makefile

# Catch-all target: Redirige todos los objetivos desconocidos a Sphinx usando "make mode".
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
