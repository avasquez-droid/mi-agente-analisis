# Preguntas frecuentes

**¿De dónde salen las cifras del análisis?**
De la ficha de cada empresa en el informe de investigación. El cuadro resumen solo se usa para
detectar discrepancias, que se listan aparte.

**¿Los honorarios son oficiales?**
No todavía. `conocimiento/tarifario.yaml` tiene valores por defecto y el rango observado en los
contratos 2024-2026. Los marcados `# PROV` deben validarse.

**¿Puedo subir informes o contratos reales al repositorio?**
No. Contienen datos personales. Guárdalos en `privado/` (ignorado por Git) o fuera del repo.

**El informe trae una sección nueva o con otro formato.**
Pásale el archivo al agente: la lectura está en `core/informe_reader.py` (`CAMPOS` y `SECCIONES_FICHA`).

**Un servicio no tiene contrato tipo.**
Ver "Agregar el contrato tipo de un servicio" en `docs/guia-uso.md`.

**¿Dónde están las diferencias entre contratos?**
En `docs/revision-contratos.md`.
