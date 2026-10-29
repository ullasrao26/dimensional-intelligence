import io, os, re, json, math, shutil, subprocess, tempfile, hashlib
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

APP_TITLE = 'ForgePoint | Dimensional Intelligence — Final Demo'
st.set_page_config(page_title=APP_TITLE, page_icon='◈', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--line:#263650;--muted:#98a9c2;--cyan:#68e0d0} html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:radial-gradient(ellipse at 80% 0%,#152643 0%,#0b1020 45%);color:#edf3ff}
.block-container{padding-top:2.15rem;padding-bottom:3rem;max-width:1500px;overflow:visible}
[data-testid="stAppViewContainer"] .main .block-container{padding-left:clamp(1rem,3vw,2.5rem);padding-right:clamp(1rem,3vw,2.5rem)}
[data-testid="stHeader"]{background:rgba(11,16,32,.82);height:3.5rem}
[data-testid="stToolbar"]{right:1rem;top:.55rem}
.hero{overflow:visible;box-sizing:border-box;width:100%;min-width:0}
.hero-title{font-size:clamp(1.55rem,3vw,2.15rem);line-height:1.28;overflow-wrap:anywhere;word-break:normal;padding-bottom:.08rem}
.hero-sub{overflow-wrap:anywhere}
@media(max-width:700px){.hero{padding:20px 18px;border-radius:16px}.hero-title{font-size:1.55rem;line-height:1.3}.pill{margin-bottom:6px}.metric-value{font-size:1.25rem}}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.03em;color:#f5f8ff!important}
[data-testid="stSidebar"]{background:#0a0f1d;border-right:1px solid var(--line)}
.hero{padding:25px 28px;border:1px solid #2a3c58;border-radius:22px;background:linear-gradient(115deg,rgba(22,40,68,.96),rgba(16,27,47,.88));margin-bottom:18px}
.eyebrow{color:#68e0d0;font-size:.76rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
.hero-title{font-family:'Manrope',sans-serif;font-size:2.15rem;font-weight:800;line-height:1.15;margin:.5rem 0}
.hero-sub{color:#b5c3d9;max-width:950px;font-size:1rem;line-height:1.6}
.pill{display:inline-block;padding:5px 10px;border-radius:999px;font-size:.75rem;font-weight:700;border:1px solid #39506e;background:#172841;color:#b9d4ff;margin-right:6px}
.metric{background:linear-gradient(145deg,#141f33,#101827);border:1px solid var(--line);border-radius:16px;padding:17px 18px;min-height:108px}
.metric-label{color:#91a3bd;font-size:.76rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.metric-value{font-family:'Manrope',sans-serif;color:#f3f7ff;font-size:1.55rem;font-weight:800;margin-top:6px;overflow-wrap:anywhere}
.metric-note,.small{color:var(--muted);font-size:.8rem}.section-card{border:1px solid var(--line);border-radius:16px;padding:18px 20px;background:rgba(17,26,45,.78)}
.stButton>button,.stDownloadButton>button{border-radius:10px;border:1px solid #42617f;background:#17304b;color:#f2f7ff;font-weight:700}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#68e0d0;color:#68e0d0}
</style>''', unsafe_allow_html=True)

APP_DIR = Path(__file__).resolve().parent
JUDGE_STEP = 'D0153970-000_PC000600609.stp'
JUDGE_DWG = 'WL1130002-0-1.dwg'
JUDGE_PREVIEW = 'judge_sample_preview.stl'
FEATURE_COLUMNS = ['Feature ID','Feature','Characteristic','Nominal (mm)','Lower limit (mm)','Upper limit (mm)','Actual (mm)','Data source','Measurement method']

def bundled_judge_files():
    result = {}
    for name in (JUDGE_STEP, JUDGE_DWG):
        path = APP_DIR / name
        if path.exists():
            raw = path.read_bytes()
            result[name] = {'bytes': raw, 'suffix': path.suffix.lower(), 'size': len(raw), 'origin': 'JUDGE-SUPPLIED SAMPLE'}
    return result

if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = bundled_judge_files()
    st.session_state['active_file_pack'] = 'Judge-supplied sample files'
if 'features' not in st.session_state: st.session_state.features = pd.DataFrame(columns=FEATURE_COLUMNS)
if 'extract_rows' not in st.session_state: st.session_state.extract_rows = []
if 'extract_texts' not in st.session_state: st.session_state.extract_texts = []
if 'extract_message' not in st.session_state: st.session_state.extract_message = ''
if 'processed_file_keys' not in st.session_state: st.session_state.processed_file_keys = set()
if 'processing_errors' not in st.session_state: st.session_state.processing_errors = {}
if 'active_model_name' not in st.session_state:
    st.session_state['active_model_name'] = JUDGE_STEP if (APP_DIR / JUDGE_STEP).exists() else ''
if 'mesh_bytes' not in st.session_state and (APP_DIR / JUDGE_PREVIEW).exists():
    st.session_state['mesh_bytes'] = (APP_DIR / JUDGE_PREVIEW).read_bytes()
    st.session_state['mesh_extents'] = {'X': 118.0, 'Y': 40.0, 'Z': 45.0}
if 'flash_message' not in st.session_state: st.session_state['flash_message'] = ''

def reset_inspection_state(clear_model=True):
    st.session_state.extract_rows = []
    st.session_state.extract_texts = []
    st.session_state.extract_message = ''
    st.session_state.processed_file_keys = set()
    st.session_state.processing_errors = {}
    st.session_state.features = pd.DataFrame(columns=FEATURE_COLUMNS)
    st.session_state.pop('processing_summary', None)
    if clear_model:
        st.session_state.pop('mesh_bytes', None)
        st.session_state.pop('mesh_extents', None)
        st.session_state['active_model_name'] = ''

def activate_uploaded_files():
    picked = st.session_state.get('judge_uploads') or []
    if not picked:
        st.session_state['flash_message'] = 'Choose at least one file before replacing the active inspection session.'
        return
    st.session_state.uploaded_files = {f.name: {'bytes': f.getvalue(), 'suffix': Path(f.name).suffix.lower(), 'size': len(f.getvalue()), 'origin': 'USER UPLOAD'} for f in picked}
    st.session_state['active_file_pack'] = 'User-uploaded inspection files'
    reset_inspection_state(clear_model=True)
    st.session_state['workspace_page'] = 'Import & Process'
    st.session_state['flash_message'] = f'Loaded {len(st.session_state.uploaded_files)} new file(s). Previous model and inspection data were cleared.'

def restore_judge_files():
    st.session_state.uploaded_files = bundled_judge_files()
    st.session_state['active_file_pack'] = 'Judge-supplied sample files'
    reset_inspection_state(clear_model=True)
    preview = APP_DIR / JUDGE_PREVIEW
    if preview.exists() and JUDGE_STEP in st.session_state.uploaded_files:
        st.session_state['mesh_bytes'] = preview.read_bytes()
        st.session_state['mesh_extents'] = {'X': 118.0, 'Y': 40.0, 'Z': 45.0}
        st.session_state['active_model_name'] = JUDGE_STEP
    st.session_state['workspace_page'] = 'Import & Process'
    st.session_state['flash_message'] = 'Restored the two judge-supplied files as the active inspection session.'


def metric(label, value, note=''):
    st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

def evaluate(df):
    out = df.copy()
    for c in ['Nominal (mm)','Lower limit (mm)','Upper limit (mm)','Actual (mm)']:
        if c not in out: out[c] = None
        out[c] = pd.to_numeric(out[c], errors='coerce')
    out['Deviation (mm)'] = out['Actual (mm)'] - out['Nominal (mm)']
    out['Deviation (µm)'] = out['Deviation (mm)'] * 1000
    out['Status'] = out.apply(lambda r: 'UNEVALUATED' if pd.isna(r['Actual (mm)']) or pd.isna(r['Lower limit (mm)']) or pd.isna(r['Upper limit (mm)']) else ('PASS' if r['Lower limit (mm)'] <= r['Actual (mm)'] <= r['Upper limit (mm)'] else 'FAIL'), axis=1)
    return out

def load_mesh(path):
    try:
        import trimesh
        mesh = trimesh.load_mesh(str(path), force='mesh')
        if isinstance(mesh, trimesh.Scene): mesh = mesh.dump(concatenate=True)
        if mesh.is_empty: return None, 'Mesh is empty.'
        return mesh, None
    except Exception as e: return None, f'Could not load mesh: {e}'

def mesh_figure(mesh):
    v, f = mesh.vertices, mesh.faces
    fig = go.Figure(data=[go.Mesh3d(x=v[:,0], y=v[:,1], z=v[:,2], i=f[:,0], j=f[:,1], k=f[:,2], color='#68e0d0', opacity=1, flatshading=False, lighting=dict(ambient=.55,diffuse=.8,specular=.35,roughness=.6), hoverinfo='skip')])
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#dce7f8', margin=dict(l=0,r=0,t=8,b=0), scene=dict(bgcolor='rgba(0,0,0,0)', aspectmode='data', xaxis_title='X (model units)', yaxis_title='Y (model units)', zaxis_title='Z (model units)', xaxis=dict(gridcolor='#263650'), yaxis=dict(gridcolor='#263650'), zaxis=dict(gridcolor='#263650')), height=560)
    return fig

def dxf_extract(file_bytes):
    import ezdxf
    doc = ezdxf.read(io.BytesIO(file_bytes)); msp = doc.modelspace(); rows=[]; texts=[]
    for ent in msp:
        typ = ent.dxftype()
        try:
            if typ == 'DIMENSION':
                dim = ent.dxf
                rows.append({'Entity type':typ, 'Layer':dim.layer, 'Extracted value':str(getattr(dim,'text','') or ''), 'Raw measurement':str(getattr(dim,'actual_measurement','') or ''), 'Review status':'UNVERIFIED — review on drawing'})
            elif typ in ('TEXT','MTEXT','ATTRIB','ATTDEF'):
                txt = ent.dxf.text if typ in ('TEXT','ATTRIB','ATTDEF') else ent.text
                txt = str(txt).replace('\\P',' ')
                if txt.strip():
                    texts.append(txt)
                    if re.search(r'⌀|%%c|\+/-|±|GD&T|POSITION|FLATNESS|PERPENDICULAR|PARALLEL|PROFILE|DATUM|TRUE POSITION|\d+\s*[xX]\s*\d+|\d+\.\d+', txt, re.I):
                        rows.append({'Entity type':typ, 'Layer':ent.dxf.layer, 'Extracted value':txt, 'Raw measurement':'', 'Review status':'CANDIDATE TEXT — verify against drawing'})
        except Exception: pass
    return rows, texts, len(msp)

def parse_step_to_mesh(file_name, file_bytes):
    try:
        import cadquery as cq
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / Path(file_name).name
            out = Path(td) / 'uploaded_model.stl'
            src.write_bytes(file_bytes)
            shape = cq.importers.importStep(str(src))
            bb = shape.val().BoundingBox()
            cq.exporters.export(shape, str(out), exportType='STL', tolerance=0.05, angularTolerance=0.05)
            mesh, err = load_mesh(out)
            extents = {'X':float(bb.xlen),'Y':float(bb.ylen),'Z':float(bb.zlen)}
            return mesh, extents, None if not err else err
    except Exception as e:
        return None, None, f'STEP preview conversion failed: {type(e).__name__}: {e}. Install CadQuery or export this STEP to STL using CAD software and upload the STL alongside it.'

def parse_dwg(file_name, file_bytes):
    # DWG is a proprietary binary format. Try a locally installed ODA converter if discoverable; otherwise guide user to DXF conversion.
    exe = shutil.which('ODAFileConverter') or shutil.which('ODAFileConverter.exe')
    if not exe:
        return 'DWG received, but no compatible DWG-to-DXF converter was detected on this computer. The import is registered; to extract drawing entities, convert this DWG to DXF with ODA File Converter or CAD software, then upload the DXF. No dimensions have been guessed.'
    return 'DWG received. ODA File Converter was detected, but automatic conversion has not been enabled in this prototype; convert the drawing to DXF and upload the DXF for candidate extraction.'

with st.sidebar:
    st.markdown('## ◈ ForgePoint'); st.caption('DIMENSIONAL INTELLIGENCE'); st.markdown('---')
    page = st.radio('WORKSPACE', ['Import & Process','Part Viewer','Drawing Extraction','Requirements Review','Feature Inspection','50 µm Validation','AI Assistant','Reports'], key='workspace_page', label_visibility='collapsed')
    st.markdown('---'); st.markdown('### Universal file import')
    st.caption('Active pack: ' + st.session_state.get('active_file_pack', 'Inspection session'))
    uploads = st.file_uploader('Choose new file(s) to replace the active session', type=['step','stp','stl','dwg','dxf','csv','pdf'], accept_multiple_files=True, key='judge_uploads', help='Select one model, one drawing, or both. Processing a new batch clears the previous model preview and inspection data so stale results cannot carry over.')
    st.button('Process selected files · replace session', type='primary', use_container_width=True, disabled=not uploads, on_click=activate_uploaded_files)
    st.button('Restore judge-supplied files', use_container_width=True, on_click=restore_judge_files, help='Reload the STEP and DWG files provided with this project.')
    if st.session_state.get('flash_message'):
        st.info(st.session_state['flash_message'])
        st.session_state['flash_message'] = ''
    st.markdown('---'); st.markdown('<div class="small">Drawing candidates require review · CAD preview is visual-only · 50 µm capability not validated</div>', unsafe_allow_html=True)

files = st.session_state.uploaded_files
cad_files = [(n,v) for n,v in files.items() if v['suffix'] in ('.step','.stp','.stl')]
drawing_files = [(n,v) for n,v in files.items() if v['suffix'] in ('.dwg','.dxf','.pdf')]
csv_files = [(n,v) for n,v in files.items() if v['suffix']=='.csv']

st.markdown('''<div class="hero"><div class="eyebrow">ForgePoint · Digital dimensional inspection</div><div class="hero-title">Import the part.<br><span style="color:#68e0d0">Start the inspection workflow.</span></div><div class="hero-sub">Universal file-driven inspection workflow. The two files supplied by the judges are loaded as the starting sample pack; importing a new batch replaces the active session and clears the previous model preview.</div><div style="margin-top:16px"><span class="pill">Universal file intake</span><span class="pill">2D + 3D workflow concept</span><span class="pill">50 µm validation gate</span></div></div>''', unsafe_allow_html=True)

if page == 'Import & Process':
    st.markdown('## Import status & next steps')
    st.caption('Active session: ' + st.session_state.get('active_file_pack', 'Inspection session'))
    if not files:
        st.info('No active files are loaded. Restore the judge-supplied files or choose a new batch in the sidebar.')
        c1,c2,c3=st.columns(3)
        with c1: metric('CAD model','Waiting','STEP / STP / STL')
        with c2: metric('Drawing','Waiting','DWG / DXF / PDF')
        with c3: metric('Inspection data','Waiting','No simulated defaults')
    else:
        c1,c2,c3=st.columns(3)
        with c1: metric('Files registered',str(len(files)),'Current inspection session')
        with c2: metric('CAD/model files',str(len(cad_files)),'STEP / STP / STL')
        with c3: metric('Drawing files',str(len(drawing_files)),'DWG / DXF / PDF')
        st.markdown('### Uploaded files')
        st.dataframe(pd.DataFrame([{'File':n,'Type':v['suffix'].upper().lstrip('.'),'Size (KB)':round(v['size']/1024,1),'Intake status':'RECEIVED', 'Source':v.get('origin','CURRENT SESSION')} for n,v in files.items()]), hide_index=True, use_container_width=True)
        st.markdown('### Automatic processing')
        for name,item in files.items():
            ext=item['suffix']
            file_key = hashlib.sha256((name + ':').encode('utf-8') + item['bytes']).hexdigest()
            if file_key in st.session_state.processed_file_keys:
                st.markdown(f'**{name}** · already processed in this session')
                if file_key in st.session_state.processing_errors:
                    st.warning(st.session_state.processing_errors[file_key])
                continue
            st.markdown(f'**{name}**')
            try:
                if ext in ('.step','.stp'):
                    with st.spinner(f'Creating visual preview for {name}…'):
                        mesh, extents, err = parse_step_to_mesh(name,item['bytes'])
                    if mesh is not None:
                        st.session_state['mesh_bytes'] = mesh.export(file_type='stl')
                        st.session_state['mesh_extents'] = extents
                        st.session_state['active_model_name'] = name
                        st.success('STEP file opened and preview mesh generated. Geometry extents are preliminary CAD metadata, not a verified inspection result.')
                        st.json({'Approximate CAD extents (model units)':extents})
                    else: st.warning(err)
                elif ext == '.stl':
                    mesh,err = None,None
                    with tempfile.NamedTemporaryFile(suffix='.stl',delete=False) as tmp:
                        tmp.write(item['bytes']); tmp_path=tmp.name
                    mesh,err=load_mesh(tmp_path)
                    try: os.unlink(tmp_path)
                    except Exception: pass
                    if mesh is not None:
                        st.session_state['mesh_bytes'] = mesh.export(file_type='stl')
                        st.session_state['active_model_name'] = name
                        bb=mesh.bounds; ext=bb[1]-bb[0]; st.session_state['mesh_extents']={'X':float(ext[0]),'Y':float(ext[1]),'Z':float(ext[2])}
                        st.success('STL mesh loaded. STL contains triangulated surface geometry and may not retain original CAD feature/tolerance data.')
                    else: st.error(err)
                elif ext == '.dxf':
                    try:
                        rows,texts,count=dxf_extract(item['bytes']); st.session_state.extract_rows.extend(rows); st.session_state.extract_texts.extend(texts)
                        st.session_state.extract_message=f'DXF parsed: {count} modelspace entities; {len(rows)} candidate annotations; {len(texts)} text entities.'
                        st.success(st.session_state.extract_message)
                    except Exception as e: st.error(f'DXF parser failed: {type(e).__name__}: {e}')
                elif ext == '.dwg': st.warning(parse_dwg(name,item['bytes']))
                elif ext == '.pdf': st.warning('PDF received. PDF drawing extraction/OCR is not implemented in this prototype. Use the PDF as a visual reference and upload DXF for candidate entity extraction.')
                elif ext == '.csv':
                    try:
                        df=pd.read_csv(io.BytesIO(item['bytes']))
                        st.dataframe(df.head(20),use_container_width=True)
                        required={'Feature ID','Feature','Characteristic','Nominal (mm)','Lower limit (mm)','Upper limit (mm)','Actual (mm)'}
                        if required.issubset(df.columns):
                            if 'Data source' not in df: df['Data source']='UPLOADED CSV — user supplied'
                            if 'Measurement method' not in df: df['Measurement method']='User supplied; not independently verified'
                            st.session_state.features=df
                            st.success('Measurement CSV loaded. These are user-supplied values, not independently validated sensor readings.')
                        else: st.warning('CSV previewed, but required inspection columns were not found; it was not loaded as measurement data.')
                    except Exception as e: st.error(f'CSV could not be read: {e}')
            except Exception as e:
                msg = f'Processing failed for {name}: {type(e).__name__}: {e}'
                st.error(msg)
                st.session_state.processing_errors[file_key] = msg
            finally:
                st.session_state.processed_file_keys.add(file_key)
        st.markdown('### Workflow state')
        state_rows=[{'Stage':'File intake','Status':'COMPLETE','Meaning':'Files registered for this session'}, {'Stage':'CAD preview','Status':'READY' if 'mesh_bytes' in st.session_state else ('NEEDS CONVERSION / CAD SUPPORT' if cad_files else 'WAITING FOR MODEL'),'Meaning':'Visual geometry preview only'}, {'Stage':'Drawing extraction','Status':'CANDIDATES FOUND' if st.session_state.extract_rows else ('CONVERSION REQUIRED' if any(x[1]['suffix']=='.dwg' for x in drawing_files) else ('WAITING FOR DXF' if not drawing_files else 'NO VERIFIED REQUIREMENTS')),'Meaning':'Candidate annotations only; manual review required'}, {'Stage':'Actual measurement','Status':'NOT PROVIDED','Meaning':'No sensor connection or physical measurements in this prototype'}, {'Stage':'50 µm validation','Status':'NOT VALIDATED','Meaning':'Requires traceable reference and independent testing'}]
        st.dataframe(pd.DataFrame(state_rows),hide_index=True,use_container_width=True)
        st.info('Next: inspect the model in Part Viewer, review candidate callouts in Drawing Extraction, then enter/verify requirements. Do not treat file import or a CAD preview as a physical measurement.')

elif page == 'Part Viewer':
    st.markdown('## Interactive 3D part viewer')
    if st.session_state.get('active_model_name'):
        st.caption('Active model: ' + st.session_state['active_model_name'])
    if 'mesh_bytes' not in st.session_state:
        st.info('No active 3D model preview. Upload a STEP/STP or STL file and process it. If you uploaded only a drawing, the previous model is intentionally cleared rather than shown as if it belonged to the new file.')
    else:
        try:
            import trimesh
            mesh=trimesh.load_mesh(io.BytesIO(st.session_state['mesh_bytes']),file_type='stl',force='mesh')
            if isinstance(mesh,trimesh.Scene): mesh=mesh.dump(concatenate=True)
            a,b,c=st.columns(3)
            with a: metric('Vertices',f'{len(mesh.vertices):,}','Triangulated preview')
            with b: metric('Faces',f'{len(mesh.faces):,}','Surface mesh')
            with c: metric('Preview status','VISUAL ONLY','Not a metrology result')
            st.plotly_chart(mesh_figure(mesh),use_container_width=True)
            st.caption('Tessellation and display are for visual identification only. Do not use this mesh preview to establish 50 µm accuracy.')
            if st.session_state.get('mesh_extents'): st.dataframe(pd.DataFrame([{'Axis':k,'Approximate span (model units)':v} for k,v in st.session_state['mesh_extents'].items()]),hide_index=True,use_container_width=True)
            st.download_button('Download generated preview mesh (STL)',st.session_state['mesh_bytes'],file_name='forgepoint_uploaded_preview.stl',mime='model/stl')
        except Exception as e: st.error(f'Could not display uploaded mesh: {e}')

elif page == 'Drawing Extraction':
    st.markdown('## Drawing dimensions & GD&T candidate extraction')
    st.write('This module reads some DXF modelspace dimension and text entities. It does not fully interpret GD&T or prove extracted values are correct.')
    if st.session_state.extract_message: st.success(st.session_state.extract_message)
    if st.session_state.extract_rows:
        ann=pd.DataFrame(st.session_state.extract_rows)
        st.dataframe(ann,use_container_width=True,hide_index=True)
        st.download_button('Download candidate annotations CSV',ann.to_csv(index=False).encode(),file_name='drawing_annotation_candidates.csv',mime='text/csv')
    else:
        st.info('No DXF annotation candidates are currently loaded. If the judge provides DWG, convert it to DXF using compatible CAD software or ODA File Converter, then upload the DXF and click Process selected files · replace session.')
    if st.session_state.extract_texts:
        with st.expander('Extracted text entities (unverified)'): st.text('\n'.join(st.session_state.extract_texts[:500]))
    st.markdown('### Known limitations')
    st.markdown('- DWG is accepted into the workflow but requires conversion to DXF; direct binary DWG parsing is not implemented.\n- GD&T symbols can be stored as blocks, special fonts or graphics and may not appear as ordinary text.\n- Datum-feature mapping, geometric tolerance interpretation and automated feature association are not implemented.\n- Verify all candidate callouts against the original drawing before using them as inspection requirements.')

elif page == 'Requirements Review':
    st.markdown('## Verified inspection requirements')
    st.caption('This table starts empty intentionally. Enter only dimensions/tolerances verified against the drawing. No sample values are inserted.')
    cols=['Feature ID','Feature','Characteristic','Nominal (mm)','Lower limit (mm)','Upper limit (mm)','Actual (mm)','Data source','Measurement method']
    if st.session_state.features.empty:
        base=pd.DataFrame([{'Feature ID':'','Feature':'','Characteristic':'','Nominal (mm)':None,'Lower limit (mm)':None,'Upper limit (mm)':None,'Actual (mm)':None,'Data source':'MANUAL ENTRY — verify drawing','Measurement method':'Not measured'}])
    else: base=st.session_state.features.copy()
    edited=st.data_editor(base,use_container_width=True,num_rows='dynamic',key='requirements_editor')
    if st.button('Save reviewed requirements',type='primary'):
        st.session_state.features=edited
        st.success('Saved in this running session. Confirm each value against the original drawing before use.')
    st.download_button('Export requirements template (CSV)',base.to_csv(index=False).encode(),file_name='inspection_requirements_template.csv',mime='text/csv')

elif page == 'Feature Inspection':
    st.markdown('## Feature inspection results')
    st.caption('PASS/FAIL is computed only from the numeric limits entered here. This is not complete GD&T evaluation.')
    if st.session_state.features.empty:
        st.info('No inspection requirements or measurements loaded. First review requirements, or upload a measurement CSV from the sidebar.')
    else:
        edited=st.data_editor(st.session_state.features,use_container_width=True,num_rows='dynamic',key='inspection_editor')
        result=evaluate(edited)
        st.markdown('### Calculated numeric-limit results')
        st.dataframe(result,use_container_width=True,hide_index=True)
        st.download_button('Download evaluated results (CSV)',result.to_csv(index=False).encode(),file_name='forgepoint_inspection_results.csv',mime='text/csv')
        st.caption('Actual values are only as trustworthy as their stated source. CAD nominal geometry is not a physical measurement.')

elif page == '50 µm Validation':
    st.markdown('## 50 µm capability & validation')
    st.markdown('The challenge brief identifies 50 µm (0.05 mm) as the tightest tolerance. That does not establish this system\'s measurement accuracy.')
    a,b,c=st.columns(3)
    with a: metric('Challenge tolerance','50 µm','0.05 mm')
    with b: metric('Reference evidence','NOT PROVIDED','No calibrated comparison uploaded')
    with c: metric('System capability','NOT VALIDATED','Physical testing required')
    checks=pd.DataFrame([{'Validation item':'Traceable calibration artefact','Status':'Not provided','Purpose':'Reference traceability'},{'Validation item':'Sensor calibration','Status':'Not provided','Purpose':'Sensor scale and response'},{'Validation item':'Axis geometry and positioning','Status':'Not provided','Purpose':'Full-envelope coordinate errors'},{'Validation item':'Repeatability study','Status':'Not performed','Purpose':'Variation across repeated scans'},{'Validation item':'Reference comparison over envelope','Status':'Not performed','Purpose':'Local and full-scale errors'},{'Validation item':'Feature-level uncertainty budget','Status':'Not calculated','Purpose':'Defensible acceptance decisions'}])
    st.dataframe(checks,use_container_width=True,hide_index=True)

elif page == 'AI Assistant':
    st.markdown('## AI inspection assistant')
    st.info('Optional. The assistant can only discuss data loaded into the current session. It must not invent dimensions, tolerances, measurements or validation evidence.')
    question=st.text_area('Ask about the current inspection',placeholder='Example: Summarize the current verified requirements and identify missing evidence.',height=100)
    if st.button('Ask inspection assistant',type='primary'):
        key=os.getenv('OPENAI_API_KEY','').strip(); model=os.getenv('OPENAI_MODEL','gpt-4.1-mini').strip()
        if not key: st.warning('AI is not connected. Set OPENAI_API_KEY in your environment and restart the app. Other pages work without it.')
        elif not question.strip(): st.warning('Enter a question first.')
        else:
            try:
                from openai import OpenAI
                rows=st.session_state.features.to_dict(orient='records') if not st.session_state.features.empty else []
                context={'uploaded_files':list(files.keys()),'candidate_annotations':st.session_state.extract_rows[:200],'feature_data':rows,'validation':'NOT VALIDATED'}
                client=OpenAI(api_key=key)
                response=client.chat.completions.create(model=model,messages=[{'role':'system','content':'You are ForgePoint inspection assistant. Use only provided context. Do not invent dimensions, GD&T, sensor readings, calibration or validation evidence. Explain that candidate drawing annotations require verification and that PASS/FAIL from simple numeric limits is not complete GD&T. Never claim 50 µm capability without independent validation.'},{'role':'user','content':json.dumps({'context':context,'question':question},default=str)}],temperature=.2)
                st.markdown(response.choices[0].message.content)
            except Exception as e: st.error(f'AI request failed: {type(e).__name__}: {e}')

elif page == 'Reports':
    st.markdown('## Inspection report data')
    if st.session_state.features.empty:
        st.info('No requirements/measurement data is loaded. Import a valid measurement CSV or enter verified requirements first. No fabricated report will be generated.')
    else:
        report=evaluate(st.session_state.features.copy())
        report.insert(0,'Inspection run',datetime.now().strftime('FP-%Y%m%d-%H%M%S'))
        report['System validation']='50 µm capability NOT VALIDATED'
        report['Report note']=report['Data source'].astype(str).apply(lambda x:'User supplied; not independently verified' if x else 'Source not recorded')
        st.dataframe(report,use_container_width=True,hide_index=True)
        st.download_button('Download inspection report data (CSV)',report.to_csv(index=False).encode(),file_name='forgepoint_inspection_report.csv',mime='text/csv')
        st.download_button('Download inspection report data (JSON)',report.to_json(orient='records',indent=2).encode(),file_name='forgepoint_inspection_report.json',mime='application/json')
        st.warning('This is a prototype data report, not a certified inspection certificate. It is not a substitute for physical measurement or verified GD&T evaluation.')

st.markdown('---')
st.markdown('<div class="small">ForgePoint prototype · Uploaded files drive the session · Drawing candidates require review · CAD preview is visual-only · 50 µm capability not validated</div>',unsafe_allow_html=True)
