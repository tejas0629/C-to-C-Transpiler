# C to C++ Transpiler (7 Compiler Phases) 🚀

This project demonstrates a mini compiler pipeline that transpiles **C code to C++ code** and visualizes all **7 phases of compilation** with an animated parse-tree UI.

## Tech Stack
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python Flask (`app.py`, `transpiler.py`)

## Team Members & Work Split
1. **Tejas (Team Lead)**
   - Planned architecture and compiler pipeline sequence.
   - Defined team workflow and integration checkpoints.
2. **Mayank**
   - Implemented Flask backend endpoints and error handling.
   - Implemented lexical, syntax, and semantic phases.
3. **Devesh**
   - Built intermediate code generation, optimization simulation, and C→C++ conversion rules.
4. **Megha (Frontend)**
   - Designed user-friendly animated UI.
   - Built phase visualization cards and interactive parse-tree rendering.

## 7 Compiler Phases Demonstrated
1. Lexical Analysis
2. Syntax Analysis (Parse Tree)
3. Semantic Analysis
4. Intermediate Code Generation
5. Code Optimization
6. Code Generation (C++ output)
7. Symbol Table & Compilation Report

## Run Locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install flask
python app.py
```

Open: `http://127.0.0.1:5000`

## Notes
- This is an educational transpiler and supports a practical subset of C syntax.
- Parse tree is interactive and animated for improved readability.
