# ForgePoint Dimensional Intelligence — Final Demo Build (v4)

This is the latest demo package. It is a file-driven prototype for the ForgePoint GRP dimensional-inspection challenge. It starts with the two judge-supplied reference files loaded as the active sample pack. It does not preload sample inspection measurements. A newly processed upload batch replaces the active session and clears the prior model preview, drawing candidates, and inspection data.

## What this version does

- Upload one or more judge-provided `.step`, `.stp`, `.stl`, `.dwg`, `.dxf`, `.pdf`, or `.csv` files from the sidebar.
- Register and summarize the files in the current session.
- Attempt a 3D visual preview for STEP/STP using CadQuery; display STL directly.
- Read selected DXF modelspace dimensions and text as **unverified candidate annotations**.
- Accept DWG into the workflow and clearly explain that direct DWG parsing is not implemented; convert to DXF with compatible CAD software or ODA File Converter, then upload the DXF.
- Accept a CSV containing the expected inspection columns as user-supplied measurement data.
- Let an operator enter/review requirements and evaluate numeric values against entered lower/upper limits.
- Export CSV/JSON inspection data.
- Keep the 50 µm capability status explicitly **NOT VALIDATED**.
- Preload the judge-supplied STEP and DWG reference files for an immediate first demo.
- Include a preview mesh for the judge-supplied STEP as a fallback visual preview if STEP conversion is unavailable. This is only a visual preview of the supplied CAD part, not a measurement.
- Replace the active file batch when new uploads are processed; clear the previous model if the new batch has no supported model or model processing fails, preventing stale geometry from being shown.
- Provide a one-click action to restore the original judge-supplied files.
- Avoid reprocessing the same uploaded files on every normal Streamlit rerun in the same session.
- Use responsive hero/header styling and extra vertical spacing to prevent the title/header from clipping on narrower screens.

## Important engineering limitations

This is a prototype UI/workflow, not a completed metrology instrument.

- Importing a CAD model is not measuring a physical part.
- STEP geometry extents are preliminary CAD metadata, not sensor measurements.
- DXF extraction is partial. It does not fully interpret graphical GD&T symbols, special fonts, blocks, layouts, datum-feature associations or all GD&T semantics.
- DWG is accepted, but the app does not parse its proprietary binary format directly.
- PDF drawing OCR/extraction is not implemented.
- All drawing requirements must be checked against the original drawing before being used for inspection.
- PASS/FAIL is a numeric lower/upper-limit comparison only; it is not complete GD&T evaluation.
- No physical sensor connection is implemented.
- The prototype does not establish 50 µm accuracy. Independent traceable validation is required.
- AI Assistant is optional and requires an OpenAI API key. Other pages work without one. Do not hard-code API keys into the source.

## Windows setup (recommended)

Use **standard 64-bit Python 3.12**, not the experimental free-threading (`3.13t`) build. This does not uninstall or replace any other Python version.

Open PowerShell in this folder and run:

```powershell
py -3.12 --version
py -3.12 -m venv .venv-final
.\.venv-final\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell says Python 3.12 is unavailable, install the standard 64-bit version from the official Python website first. If script activation is blocked, open Command Prompt in this folder and use:

```bat
py -3.12 -m venv .venv-final
.venv-final\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Keep `.venv-final` for this version. Do not reuse the experimental Python 3.13 free-threaded environment.

## Judge-day workflow

1. Start the app with `python -m streamlit run app.py`.
2. The two original judge-supplied files are loaded as the initial active sample pack.
3. To test a new part, select one or more files in the sidebar and click **Process selected files · replace session**. This replaces the active batch and clears the prior model preview and inspection data.
4. To restore the original pair, click **Restore judge-supplied files**. Review processing status on **Import & Process**.
5. Open **Part Viewer** for a supported STEP/STP/STL preview.
6. If the drawing is DWG, convert it to DXF with compatible CAD software or ODA File Converter, then upload/process the DXF. Review all extracted candidates against the original drawing.
7. Open **Requirements Review** and enter only verified nominal dimensions and numeric limits. Leave unknown values blank rather than guessing.
8. Import actual measurements only from a defined measurement source or clearly identified user-supplied measurement CSV.
9. Review **Feature Inspection** and export the report data.
10. Describe the demo accurately: CAD preview and candidate extraction are demonstrated; physical measurement and 50 µm capability are not validated.

## DWG to DXF

ODA File Converter: https://www.opendesign.com/guestfiles/oda_file_converter

## Optional AI Assistant setup (PowerShell)

```powershell
$env:OPENAI_API_KEY="your_key_here"
$env:OPENAI_MODEL="gpt-4.1-mini"
python -m streamlit run app.py
```

AI API use may incur charges. The dashboard works without the AI key.

## Included judge-supplied references

The initial files are bundled and loaded as the starting active session:

- `D0153970-000_PC000600609.stp`
- `WL1130002-0-1.dwg`
- `ForgePoint_Challenge_Brief.pdf`
