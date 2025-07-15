from pathlib import Path
# import json
# import configparser
import pprint
pp = pprint.PrettyPrinter(indent=4);
import time
import math
from collections import namedtuple

# # pip install slicerio
# import slicerio.server

# # packages for 3d
# #   # for OCT 3D stuff and using in jupyter
# #   - trame-jupyter-extension
# #   - trame
# #   - trame-vtk
# #   - trame-vuetify
# #   - ipywidgets

import matplotlib.pyplot as plt
import plotly.express as px

# interactive panels
import panel as pn
pn.extension('plotly');

import numpy as np
import pandas as pd
import addict

import cv2
import skimage
import sklearn
import scipy.signal

import pyvista as pv
from PIL import Image
import SimpleITK as sitk

# with vedo
#from vedo import dataurl, Volume, Text2D
import vedo
vedo.settings.default_backend = 'vtk'
#from vedo.applications import Slicer3DPlotter
import naatos_oct_tools.plotters.vedo_plotters as vedo_plotters
import naatos_oct_tools.plotters.sitk_plotters as sitk_plotters

import naatos_oct_tools.thorlabs_oct_file_reading





# ------------------
# RGB CAMERA IMAGES
def process_rgbcamera_and_make_individual_images(octstudy : naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder):
    """Writes out the embedded rgb camera images as a .jpg file in the processed folder, if they do not exist

    Args:
        octstudy (naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder): _description_
    """
    if(octstudy.num_oct_files>=1):
        octstudy.folder_study_processed.mkdir(exist_ok=True);
        tmparrays = [];
        for count,octdata in enumerate(sorted(octstudy.octdatalist, key= lambda x: int(x.cfg_oct_xml.Ocity.Acquisition.Timestamp.etElem.text))):
            octdata_study = octdata.cfg_oct_xml.Ocity.MetaInfo.Study.etElem.text;
            octdata_timestr = time.strftime('%Y%m%dT%H%M%S',time.gmtime(int(octdata.cfg_oct_xml.Ocity.Acquisition.Timestamp.etElem.text)));
            
            #fname = '{:s}_{:02d}_{:s}'.format(octdata_study,count,octdata_timestr);
            fname = '{:s}_videocamera_{:04d}'.format(octdata_study,count);

            # save a .png in the processing folder
            destpath = octstudy.folder_study_processed/(fname+'.jpg')
            if(not destpath.exists()):
                # image in octstudy is rgba image

                # change to rgb then save
                octdata.image.convert('RGB').save(destpath);

                # write
                print(fname,octdata_timestr);

def process_rgbcamera_and_make_montage_image(octstudy : naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder):
    """If does not exist, makes a montage of rgb camera image cropped to scan area, and writes it to processed folder

    Args:
        octstudy (naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder): _description_
    """
    filename_montage = octstudy.folder_study_processed/('{:s}_montaged.jpg'.format(octstudy.name))

    if(octstudy.num_oct_files>=1 and not filename_montage.exists()):
        # pick first octdata file
        octdata = octstudy.octdatalist[0];
        octstudy.folder_study_processed.mkdir(exist_ok=True);


        # Determine RGB CAMERA relationship/spacing to OCT scan spacing from embedded header information
        px_per_mm_X = float(octdata.cfg_oct_probe['camerascalingx']);
        px_per_mm_Y = float(octdata.cfg_oct_probe['camerascalingy']);
        print('millimeters Per Pixel X:{:} Y:{:}'.format(px_per_mm_X,px_per_mm_Y))
        # vol_dimensions = (
        #     int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[0].text),
        #     int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[1].text),
        #     int(octdata.cfg_oct_xml.Ocity.Image.SizePixel.etElem[2].text),
        # );
        # vol_spacing_mm = (
        #     float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[0].text),
        #     float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[1].text),
        #     float(octdata.cfg_oct_xml.Ocity.Image.PixelSpacing.etElem[2].text),
        # );
        # print()
        rotation = float(octdata.cfg_oct_xml.Ocity.Image.Angle.etElem.text);
        oct_scan_mm_center_X = float(octdata.cfg_oct_xml.Ocity.Image.CenterX.etElem.text) 
        oct_scan_mm_center_Y = float(octdata.cfg_oct_xml.Ocity.Image.CenterY.etElem.text)
        if(rotation==0.0):
            # normal / march settings
            oct_scan_mm_size_X = float(octdata.cfg_oct_xml.Ocity.Image.SizeReal.etElem[1].text) # 1 = X
            oct_scan_mm_size_Y = float(octdata.cfg_oct_xml.Ocity.Image.SizeReal.etElem[2].text) # 2 = Y
        elif(rotation==-90.0):
            # scans with rotation set to -90 are a bit confused, so swap dimensions
            oct_scan_mm_size_X = float(octdata.cfg_oct_xml.Ocity.Image.SizeReal.etElem[2].text) # 2 = X
            oct_scan_mm_size_Y = float(octdata.cfg_oct_xml.Ocity.Image.SizeReal.etElem[1].text) # 1 = Y
        else:
            raise NotImplementedError(f'rotation={rotation} which support has not be properly checked for')

        print('OCT Scan Center Was @ [mm]:',oct_scan_mm_center_X,oct_scan_mm_center_Y)
        print('OCT Scan FOV    Was @ [mm]:',oct_scan_mm_size_X,oct_scan_mm_size_Y)

        camera_scan_px_X = px_per_mm_X*oct_scan_mm_size_X;
        camera_scan_px_Y = px_per_mm_Y*oct_scan_mm_size_Y;
        print('Video Camera Scan Pixel Width  [px]:',camera_scan_px_X);
        print('Video Camera Scan Pixel Height [px]:',camera_scan_px_Y);

        camera_scan_center_px_X = px_per_mm_X*oct_scan_mm_center_X;
        camera_scan_center_px_Y = px_per_mm_Y*oct_scan_mm_center_Y;
        print('Video Camera Scan Pixel Center X [px]:',camera_scan_center_px_X);
        print('Video Camera Scan Pixel Center Y [px]:',camera_scan_center_px_Y);

        # --
        # debug output
        imgarr = np.array(octdata.image)[:,:,0:3];
        # plt.imshow(imgarr[:,:,:])
        # print(imgarr.shape)

        # --
        # debug output
        #slice_x = slice( imgarr.shape[0]//2+0, imgarr.shape[0]//2+imgarr.shape[0]//2);
        #plt.imshow(imgarr[slice_x,:,:])


        # determine image slicing for each image to correspond to oct area
        px_origin_x = imgarr.shape[1]//2-int(camera_scan_center_px_X);
        px_origin_y = imgarr.shape[0]//2-int(camera_scan_center_px_Y);

        camera_x_slice = slice(px_origin_x-(camera_scan_px_X/2) , px_origin_x+(camera_scan_px_X/2))
        camera_y_slice = slice(px_origin_y-(camera_scan_px_Y/2) , px_origin_y+(camera_scan_px_Y/2))
        print(' SliceX  :',camera_x_slice)
        print(' SliceY  :',camera_y_slice)

        camera_x_sliceint = slice(int(camera_x_slice.start),int(camera_x_slice.stop));
        camera_y_sliceint = slice(int(camera_y_slice.start),int(camera_y_slice.stop));
        print('SliceXint:', camera_x_sliceint )
        print('SliceYint:', camera_y_sliceint )

        # debug output
        # plt.imshow(imgarr[ camera_y_sliceint , camera_x_sliceint , : ])


        # Generate the montage
        tmparrays = [];
        for count,octdata in enumerate(sorted(octstudy.octdatalist, key= lambda x: int(x.cfg_oct_xml.Ocity.Acquisition.Timestamp.etElem.text))):
            imgarr = np.array(octdata.image)[:,:,0:3];
            # slice using pre-determined areas corresponding to the oct scan
            tmparrays.append(imgarr[ camera_y_sliceint , camera_x_sliceint , : ]);

        # write image montage to .png in processed folder
        img_camera_montage = Image.fromarray(np.concatenate(tmparrays,axis=1))
        img_camera_montage.save(filename_montage)

# ------------------
# 3D IMAGE ANALYSIS




# ------------------
# METRICS ALONG DATAFRAME
def process_along_strip_data_frame(df : pd.DataFrame):
    if('slice' not in df.columns):
        slice_centers = df.index;
        df['slice'] = df.index;
    else:
        slice_centers = df['slice'];

    # # Wax Thickness
    df['wax_top'] = df['wax_top_seed_candidate_px'].apply(lambda x: x[0]);
    df['wax_thickness'] = df['seg_bbox-3'];
    df['wax_thickness1'] = df['wax_thickness'];
    df['wax_thickness2'] = df['wax_thickness'];
    df['wax_width_px'] = df['seg_bbox-2'] - df['seg_bbox-0'];

    # df['wax_thickness1'] = wax_bot-wax_top;
    # df['wax_thickness2'] = wax_bot-df['pixel_depth_strip_top'];
    # df['wax_width_px'] = df['px_wax_transverse_edges'].apply(lambda x: np.diff(x)[0]);
    # df['wax_top'] = df['wax_top_seed_candidate_px'].apply(lambda x: x[0]);


    # df['seg_area'] = df['area'];
    # df['seg_area_filled'] = df['area_filled'];
    # df['seg_area_holes'] = df['area_filled']-df['area'];

    # df['seg_area_to_areafilled'] = df['area']/df['seg_area_filled'];
    # df['seg_area_to_areaconvex'] = df['area']/df['area_convex'];
    # df['seg_areafilled_to_areaconvex'] = df['seg_area_filled']/df['area_convex'];

    # area calcs
    df['seg_area_holes'] = df['seg_area_filled']-df['seg_area'];

    # area ratios
    df['seg_r_area_to_areafilled'] = df['seg_area']/df['seg_area_filled'];
    df['seg_r_area_to_areaconvex'] = df['seg_area']/df['seg_area_convex'];
    df['seg_r_areafilled_to_areaconvex'] = df['seg_area_filled']/df['seg_area_convex'];

    return df;