"""Diagnostic retained-stem width estimator; source binding is a separate gate.

Sample the connected normal section containing each source-defined station.
Disconnected fragments across a red-owned junction do not define stem width.
No candidate-derived station selection, rescaling, tolerance or palette tuning.
"""
import numpy as np
from scipy.ndimage import map_coordinates

def measure(before_fringe, after_fringe, before_core, start_px, end_px, normal_extent_px):
    start=np.asarray(start_px,float);end=np.asarray(end_px,float)
    vector=end-start;length=float(np.linalg.norm(vector))
    if not np.isfinite(length) or length<=0 or normal_extent_px<=0:
        raise ValueError('Invalid source-bound retained segment')
    direction=vector/length;normal=np.array([-direction[1],direction[0]])
    offsets=np.arange(-normal_extent_px,normal_extent_px+.025,.05)
    mid=int(np.argmin(abs(offsets)));rows=[]
    for station in np.arange(0,length,.25):
        point=start+direction*station;xy=(point-.5).round().astype(int)
        if not (0<=xy[1]<before_core.shape[0] and 0<=xy[0]<before_core.shape[1]):
            raise ValueError('Source station outside actual render')
        if not before_core[xy[1],xy[0]]:
            continue
        coords=point[:,None]+normal[:,None]*offsets;widths=[]
        for mask in (before_fringe,after_fringe):
            samples=map_coordinates(mask.astype(float),[coords[1]-.5,coords[0]-.5],order=0,mode='constant')>.5
            if not samples[mid]:
                widths.append(0.);continue
            left=right=mid
            while left>0 and samples[left-1]:left-=1
            while right<len(samples)-1 and samples[right+1]:right+=1
            if left==0 or right==len(samples)-1:
                raise ValueError('Normal profile clipped before both stroke edges')
            widths.append(round((right-left+1)*.05,6))
        rows.append({'station_px':float(station),'before_width_px':widths[0],'after_width_px':widths[1],'absolute_delta_px':abs(widths[0]-widths[1])})
    if len(rows)<3:
        raise ValueError('Insufficient original-core retained-stem stations')
    maximum=float(max(r['absolute_delta_px'] for r in rows))
    return {'method':'source_bound_connected_normal_cross_sections','sample_step_px':.25,'normal_step_px':.05,'source_station_selection_only':True,'maximum_width_delta_px':maximum,'median_width_delta_px':float(np.median([r['absolute_delta_px'] for r in rows])),'unchanged_width_limit_px':1.25,'passed':maximum<=1.25,'stations':rows}
