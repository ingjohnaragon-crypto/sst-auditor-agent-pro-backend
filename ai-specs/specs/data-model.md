# Modelo de datos — SST Auditor Agent Pro

Aún no hay entidades persistidas (la capa de base de datos llega en tickets
posteriores). Este documento se irá completando a medida que se modelen los
dominios.

## Fuente de referencia del dominio

El modelado de cualquier entidad SST debe partir de la referencia normativa
[`.sst-agent-document.md`](../../.sst-agent-document.md) (raíz del repo), que define:

- El ciclo **PHVA** y los componentes del SG-SST (política, objetivos, matriz
  legal, plan anual, COPASST, capacitación).
- La **gestión de peligros y riesgos (GTC 45)**: clasificación de actividades,
  identificación de peligros, cálculo del nivel de riesgo (`NR = NP × NC` con
  sus tablas de ND, NE y NC) y niveles de aceptabilidad.
- La **jerarquía de controles** (eliminación, sustitución, ingeniería,
  administrativos, EPP).
- Las **reglas normativas específicas** (Decreto 1072 de 2015, Resolución 312
  de 2019) con sus artículos y acciones exigidas al agente.

Las entidades, enumeraciones y rangos de valores (por ejemplo, los valores
válidos de ND/NE/NC o los niveles de riesgo I–IV) deben coincidir con las
tablas de ese documento.
