import cv2
import numpy as np
from ultralytics import YOLO
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ==========================================
# Iteration 86: Greedy-First IoU Tracker
# - Goal: 16/16 Pass Rate
# - High IoU matches are assigned greedily first
# - Remaining matches use Hungarian algorithm
# ==========================================

def iou(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    xi1, yi1 = max(x1, x2), max(y1, y2)
    xi2, yi2 = min(x1+w1, x2+w2), min(y1+h1, y2+h2)
    inter = max(0, xi2-xi1) * max(0, yi2-yi1)
    union = w1*h1 + w2*h2 - inter
    return inter / union if union > 0 else 0

class KalmanTrack:
    def __init__(self, tid, b):
        self.tid = tid
        self.cx, self.cy = b[0]+b[2]/2, b[1]+b[3]/2
        self.w, self.h = b[2], b[3]
        self.vx, self.vy = 0, 0
        self.last_det_x = self.cx  # Track last matched detection x position
        
    def update(self, ncx, ncy, b):
        nvx, nvy = ncx - self.cx, ncy - self.cy
        self.vx = 0.6 * nvx + 0.4 * self.vx
        self.vy = 0.6 * nvy + 0.4 * self.vy
        self.cx, self.cy = ncx, ncy
        self.w, self.h = b[2], b[3]
        self.last_det_x = ncx  # Update last matched detection position
        
    def pred_box(self):
        return (int(self.cx + self.vx - self.w/2), 
                int(self.cy + self.vy - self.h/2), 
                self.w, self.h)
    
    def pred_center(self):
        return (self.cx + self.vx, self.cy + self.vy)

class Tracker:
    def __init__(self, n=4):
        self.n = n
        self.ts = []
        self.init = False
        
    def update(self, ds):
        if not self.init:
            if len(ds) >= self.n:
                ds = sorted(ds, key=lambda b: b[0]+b[2]/2)[:self.n]
                self.ts = [KalmanTrack(i+1, b) for i, b in enumerate(ds)]
                self.init = True
            return
        
        preds_box = [t.pred_box() for t in self.ts]
        pred_centers = [t.pred_center() for t in self.ts]
        
        # Allow matching even when we have fewer detections than tracks
        if len(ds) == 0:
            for t in self.ts: t.cx, t.cy = t.cx + t.vx, t.cy + t.vy
            return

        num_dets = len(ds)
        det_centers = [(ds[j][0] + ds[j][2]/2, ds[j][1] + ds[j][3]/2) for j in range(num_dets)]
        
        # Compute IoU matrix and distance matrix
        iou_matrix = np.zeros((self.n, num_dets))
        dist_matrix = np.zeros((self.n, num_dets))
        for i in range(self.n):
            pred_cx, pred_cy = pred_centers[i]
            for j in range(num_dets):
                iou_matrix[i, j] = iou(preds_box[i], ds[j])
                det_cx, det_cy = det_centers[j]
                dist_matrix[i, j] = np.sqrt((pred_cx - det_cx)**2 + (pred_cy - det_cy)**2)
        
        assignments = {}
        assigned_dets = set()
        assigned_tracks = set()
        
        # Phase 1: High IoU matches (greedy by IoU)
        HIGH_IOU = 0.6
        high_pairs = []
        for i in range(self.n):
            for j in range(num_dets):
                if iou_matrix[i, j] >= HIGH_IOU:
                    high_pairs.append((i, j, iou_matrix[i, j]))
        high_pairs.sort(key=lambda x: -x[2])
        
        for i, j, score in high_pairs:
            if i not in assigned_tracks and j not in assigned_dets:
                assignments[i] = j
                assigned_tracks.add(i)
                assigned_dets.add(j)
        
        # Phase 2: Order-preserving greedy matching
        MED_IOU = 0.3
        remaining_tracks = [i for i in range(self.n) if i not in assigned_tracks]
        remaining_dets = [j for j in range(num_dets) if j not in assigned_dets]
        
        if remaining_tracks and remaining_dets:
            remaining_tracks_sorted = sorted(remaining_tracks, 
                                             key=lambda i: self.ts[i].last_det_x)
            remaining_dets_sorted = sorted(remaining_dets, 
                                           key=lambda j: det_centers[j][0])
            
            used_dets = set()
            for i in remaining_tracks_sorted:
                best_j = None
                best_iou = MED_IOU
                for j in remaining_dets_sorted:
                    if j not in used_dets and iou_matrix[i, j] >= best_iou:
                        best_iou = iou_matrix[i, j]
                        best_j = j
                if best_j is not None:
                    assignments[i] = best_j
                    assigned_tracks.add(i)
                    assigned_dets.add(best_j)
                    used_dets.add(best_j)
        
        # Phase 3: Low IoU - greedy remaining
        remaining_tracks = [i for i in range(self.n) if i not in assigned_tracks]
        remaining_dets = [j for j in range(num_dets) if j not in assigned_dets]
        
        if remaining_tracks and remaining_dets:
            pairs = [(i, j, iou_matrix[i, j]) for i in remaining_tracks for j in remaining_dets]
            pairs.sort(key=lambda x: -x[2])
            for i, j, score in pairs:
                if i not in assignments and j not in assigned_dets:
                    assignments[i] = j
                    assigned_dets.add(j)
        
        # Apply assignments
        for i in range(self.n):
            if i in assignments:
                j = assignments[i]
                cost = 1.0 - iou_matrix[i, j]
                if cost < 0.98:
                    self.ts[i].update(ds[j][0]+ds[j][2]/2, ds[j][1]+ds[j][3]/2, ds[j])
                else:
                    self.ts[i].cx += self.ts[i].vx
                    self.ts[i].cy += self.ts[i].vy
            else:
                self.ts[i].cx += self.ts[i].vx
                self.ts[i].cy += self.ts[i].vy
                        
    def order(self):
        if not self.init: return []
        return [t.tid for t in sorted(self.ts, key=lambda t: t.cx)]
