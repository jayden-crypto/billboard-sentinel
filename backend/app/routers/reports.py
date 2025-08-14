
import os, uuid, json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form
from ..db import SessionLocal
from .. import models, schemas
from ..util import redact_image, nearest_junction
router = APIRouter(tags=['reports'])
UPLOAD_DIR = os.getenv("STORAGE_DIR", "./data/uploads"); os.makedirs(UPLOAD_DIR, exist_ok=True)
with open(os.path.join(os.path.dirname(__file__), "..", "..", "data", "junctions.geojson")) as f:
    JUNCTIONS = json.load(f)
def get_db(): db = SessionLocal(); try: yield db
finally: db.close()
@router.post("/reports", response_model=schemas.ReportOut)
async def create_report(lat: float = Form(...), lon: float = Form(...), device_heading: float | None = Form(None), detections_json: str = Form(...), image: UploadFile = File(...)):
    rid = str(uuid.uuid4()); raw_path = os.path.join(UPLOAD_DIR, f"{rid}_raw_{image.filename}")
    with open(raw_path, "wb") as f: f.write(await image.read())
    redacted = os.path.join(UPLOAD_DIR, f"{rid}_redacted.jpg"); redact_image(raw_path, redacted, mode="mosaic")
    db = SessionLocal()
    rep = models.Report(id=rid, captured_at=datetime.utcnow(), lat=lat, lon=lon, img_uri=redacted, device_heading=device_heading or 0.0)
    db.add(rep); db.commit()
    dets = json.loads(detections_json); out=[] 
    for d in dets:
        did = str(uuid.uuid4())
        det = models.Detection(id=did, report_id=rid, bbox=json.dumps(d.get('bbox')), corners=json.dumps(d.get('corners')),
            est_width_m=float(d.get('est_width_m',0.0)), est_height_m=float(d.get('est_height_m',0.0)),
            qr_text=d.get('qr_text'), ocr_text=d.get('ocr_text'), license_id=d.get('license_id'), confidence=float(d.get('confidence',0.5)))
        db.add(det)
        # simple checks
        violations=[]
        # size
        if det.est_width_m * det.est_height_m > float(os.getenv('CITY_MAX_W','12')) * float(os.getenv('CITY_MAX_H','4')):
            violations.append(('size', f"Estimated {det.est_width_m}x{det.est_height_m} m exceeds cap", 4))
        # junction proximity
        j, distm = nearest_junction(lat, lon, JUNCTIONS)
        if distm < float(os.getenv('CITY_MIN_DIST','50')):
            violations.append(('placement', f"Near {j['properties']['name']} (~{int(distm)} m)", 3))
        # license
        if not det.license_id or det.license_id.strip()=='':
            violations.append(('license_missing','No license',5))
        else:
            # try registry
            reg = db.query(models.RegistryBillboard).filter(models.RegistryBillboard.license_id==det.license_id.strip()).first()
            if not reg:
                violations.append(('license_invalid', f"License {det.license_id} not found",5))
        vio_objs=[]
        for typ,reason,sev in violations:
            vid = str(uuid.uuid4()); db.add(models.Violation(id=vid, detection_id=did, type=typ, reason=reason, severity=sev)); vio_objs.append({'type':typ,'reason':reason,'severity':sev})
        out.append({'id':did, 'violations': vio_objs, 'confidence': det.confidence})
    db.commit(); return {'id': rid, 'detections': out}
@router.get("/reports/{report_id}")
def get_report(report_id: str):
    db = SessionLocal(); rep = db.query(models.Report).filter(models.Report.id==report_id).first()
    if not rep: return {'error':'not found'}
    dets = db.query(models.Detection).filter(models.Detection.report_id==report_id).all(); out=[]
    for d in dets:
        vios = db.query(models.Violation).filter(models.Violation.detection_id==d.id).all()
        out.append({'id':d.id,'bbox':d.bbox,'est_w':d.est_width_m,'est_h':d.est_height_m,'license_id':d.license_id,'violations':[{'type':v.type,'reason':v.reason,'severity':v.severity} for v in vios]})
    return {'id':rep.id,'img_uri':rep.img_uri,'lat':rep.lat,'lon':rep.lon,'detections':out}
@router.get("/heatmap")
def heatmap():
    db = SessionLocal(); reps = db.query(models.Report).all(); features=[]
    for r in reps:
        features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[r.lon,r.lat]},'properties':{'id':r.id,'captured_at':r.captured_at.isoformat()}})
    return {'type':'FeatureCollection','features':features}
