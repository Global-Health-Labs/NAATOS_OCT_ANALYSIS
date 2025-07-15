metric_traces = [

    # old before 6/15 data
    # ('distances','pixels',['wax_top','wax_thickness1','wax_thickness2','wax_width_px']),
    # ('areas','pixels^2',['area','area_filled','area_convex','seg_area_holes']),
    # ('ratios','ratio',['seg_area_to_areafilled','seg_area_to_areaconvex','seg_areafilled_to_areaconvex']),
    # ('counts','counts',['num_paths']),

    # new after 6/15 data
    #('distances','pixels',['wax_top','wax_thickness1','wax_thickness2','wax_width_px']),
    ('distances','pixels',['wax_top','wax_thickness','wax_width_px']),
    ('areas','pixels^2',['seg_area','seg_area_filled','seg_area_convex','seg_area_holes']),
    ('ratios','ratio',['seg_r_area_to_areafilled','seg_r_area_to_areaconvex','seg_r_areafilled_to_areaconvex']),
    ('counts','counts',['num_paths','seg_euler_number']),
]

metrics = {};
for metric_type,metric_ylabel,metric_columns in metric_traces:
    for metric in metric_columns:
        metrics[metric] = (metric_type,metric_ylabel)