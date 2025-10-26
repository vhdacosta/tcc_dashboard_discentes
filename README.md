# CCET • Base 1 — Dashboard Interativo (Streamlit)

Dashboard para análise exploratória dos discentes do **CCET/UFSCar**, com foco em:
- volumes por curso/ano,
- modalidades de ingresso (SISU),
- status acadêmicos,
- **tempo entre ingresso–egresso**,
- e um módulo dedicado à **análise de cancelamentos** (pico 2007–2009).

> **Privacidade:** o app **não** inclui dados no repositório.  
> O arquivo `.xlsx` é **enviado pelo usuário em tempo de execução** (upload) e usado **apenas na sessão**.

---

## ✨ Funcionalidades

- **Filtros-mestre** (sidebar): `Campus` e `Tipo de Ingresso`, além de intervalo de anos.
- **Páginas**:
  1. Quantidade por curso por ano (**curso único**)
  2. Quantidade por curso por ano (**todos** — cores fixas + legenda + hover)
  3. Modalidades **SISU** por ano (filtrando **1+ cursos**)
  4. Comparar **1 modalidade SISU** entre cursos (total/ano)
  5. **Todos os Status** (curso único)
  6. **Comparar 1 Status** entre cursos (total/ano)
  7. **Tempo ingresso–egresso** (boxplot/strip; cores ou facetas por Status)
  8. **Análise de Cancelamentos** (percentual por curso/ano; por tipo de ingresso; por modalidade SISU)
  9. **Informações & Créditos**

---
