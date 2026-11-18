import cv2
import numpy as np

def observe_and_draw(image, persons, roi, *, draw=True):
    regions = roi.get('regions', {})
    reference = roi.get('image_size', [])
    size_matches = reference == [image.shape[1], image.shape[0]]
    calibrated = bool(roi.get('calibrated', False)) and size_matches
    for name, polygon in regions.items():
        points = np.asarray(polygon, dtype=np.int32)
        if len(points) < 3: continue
        if not size_matches: continue
        if draw:
            cv2.polylines(image,[points],True,(0,200,255),2)
            cv2.putText(image, name + ('' if calibrated else ' UNCALIBRATED'),tuple(points[0]),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,200,255),2)
    for person in persons:
        x1,y1,x2,y2 = person['bbox_xyxy']
        anchors={'person_bottom_center':[(x1+x2)/2,y2]}
        for idx,name in [(9,'left_wrist'),(10,'right_wrist')]:
            p = person['keypoints'][idx] if len(person['keypoints'])>idx else {}
            anchors[name]=[p['x'],p['y']] if p.get('x') is not None and p.get('y') is not None else None
        person['roi']={'calibrated':calibrated,'size_matches':size_matches,'regions':{}}
        for name, polygon in regions.items():
            if len(polygon)<3:continue
            points=np.asarray(polygon,dtype=np.float32)
            person['roi']['regions'][name]={key: (bool(cv2.pointPolygonTest(points,tuple(point),False)>=0) if point is not None and size_matches else None) for key,point in anchors.items()}
    return image
