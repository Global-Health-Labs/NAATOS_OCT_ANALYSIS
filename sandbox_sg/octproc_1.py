#%%
from pathlib import Path
import json
import configparser

# pip install slicerio
import slicerio.server

# packages for 3d
#   # for OCT 3D stuff and using in jupyter
#   - trame-jupyter-extension
#   - trame
#   - trame-vtk
#   - trame-vuetify
#   - ipywidgets
import pyvista as pv

#%% Load OCT study information
folder_octexport_root = Path(r'G:\Projects\RemediReader\NAATOS_OCT_TEMP\OCTExport')
# this is also folder name
study_name = 'GHL_pyapp_20250320T1317'
folder_study = folder_octexport_root/study_name;
if not folder_study.exists:
    raise RuntimeError("Study not found")

#%% Load OCT study information And Check
# read the .json file we wrote on the OCT system
with open((folder_octexport_root/study_name)/'info.json',mode='r') as file:
    info = json.load(file);

# read the .ini settings file from Thorlabs OCT software
fileinipath = folder_study/(study_name+'_TS_DS_Parameters.ini')
if not fileinipath.exists():
    raise RuntimeError("INI file not found that should have been found")
config = configparser.ConfigParser();
config.read(fileinipath)
oct_conf = {k:dict(v) for k,v in config.items()};

# check that the expected files exist
for filoct in info['datanames']:
    filevtkpath = folder_study/((Path(filoct).stem)+'.vtk');
    if not filevtkpath.exists():
        raise RuntimeError("VTK file not found that should have been found")
    
    fileimagepath = folder_study/((Path(filoct).stem)+'_VideoImage.jpg');
    if not fileimagepath.exists():
        raise RuntimeError("Camera file not found that should have been found")
    
#%% READ the 3D images with pyvista
vols = [];
for filoct in info['datanames']:
    filevtkpath = folder_study/((Path(filoct).stem)+'.vtk');
    print('Loading VTK volume',filevtkpath.name);
    vol = pv.read(filevtkpath);
    vols.append(vol);
    #break;

#%
#%%
# # Set/enable the backed
# #pv.set_jupyter_backend("trame")
# pl = pv.Plotter()
# # opacity = [0, 0, 0, 0.1, 0.3, 0.6, 1]
# # pl.add_volume(vol, cmap="viridis", opacity=opacity)
# pl.add_volume(vol,opacity=[]);
# #pl.add_mesh(pv.ParametricKlein())
# pl.show(jupyter_backend='trame')

#%% write
# for cnt,(vol,filoct) in enumerate(zip(vols[0:],info['datanames'][:])):
#     stacked_distance = info['FOV_Y']*(cnt+1)
#     filevtkpath = folder_study/((Path(filoct).stem)+'.vtk');
#     print('VTK volume',filevtkpath.name,'at',stacked_distance,'mm');

#     #vol = vol.translate((0,0,stacked_distance));
#     #volmerged += vol;
#     #volmerged
#     #vol.save(r'C:\TEMP\TESTIMG_{:02d}.vtk'.format(cnt))
#     #volt = vol.translate((0,0,stacked_distance));
#     #volt = vol;
#     #volt.save(r'C:\TEMP\TESTIMG_T_{:02d}.vtk'.format(cnt))
    

#     # stack along
#     #vol = pv.read(filevtkpath);
#     #vols.append(vol);
#     break;

#%% Combine All Of The Volume Image Data
import numpy as np

#merged_scalars = np.concatenate([v['volume_scalars'] for v in vols],axis=0);
newdims = (
    vols[0].dimensions[0],
    vols[0].dimensions[1],
    sum([v.dimensions[2] for v in vols])
);
spacing = vols[0].spacing;
print('Merging {:d} volumes each with dims/spacing {:s}/{:s}'.format(
    len(vols),str(vols[0].dimensions),str(spacing)
))
print('Resulting 1 volume with dims/spacing {:s}/{:s}'.format(
    str(newdims),str(spacing)
))

#%% Combine All Of The Volume Image Data
mergedvol = pv.ImageData(dimensions=newdims,spacing=spacing);
# assign the scalar values which we concatenated from all volumes
mergedvol['volume_scalars'] = np.concatenate([v['volume_scalars'] for v in vols],axis=0);
# write to new vtk file
mergedvol.save(r'C:\TEMP\TESTIMG_STACKEDZ.vtk')


#%% Load the camera image data
from PIL import Image
imgs = [];
for filoct in info['datanames']:
    fileimgpath = folder_study/((Path(filoct).stem)+'_VideoImage.jpg');
    print('Loading image',fileimgpath.name);
    #imgs.append( pv.ImageData(fileimgpath) );
    imgs.append( Image.open(fileimgpath) );


#%% Combine and merge the image data
# newdims2 = (
#     #imgs[0].dimensions[0],
    
#     imgs[0].dimensions[0],
#     sum([i.dimensions[1] for i in imgs]),

#     # sum([i.dimensions[0] for i in imgs]),
#     # imgs[0].dimensions[1],
#     1
# );
# mergedimg = pv.ImageData(dimensions=newdims2);
# mergedimg['JPEGImage'] = np.concatenate([i['JPEGImage'] for i in imgs],axis=0);
#imgcombined = Image.fromarray(np.concatenate(imgs,axis=1))
imgcombined = np.concatenate(imgs,axis=1);
mergedimg = pv.ImageData(
    dimensions=(imgcombined.shape[0],imgcombined.shape[1],1)
)
#mergedimg['JPEGImage'] = imgcombined.ravel().reshape((imgcombined.shape[0]*imgcombined.shape[1],3),order="F");
mergedimg['JPEGImage'] = imgcombined.reshape((imgcombined.shape[0]*imgcombined.shape[1],3),order="F");
mergedimg.plot(rgb=True)

#%% Plot
pl = pv.Plotter()
#pl.add_volume(vol,opacity=[]);
#pl.add_mesh(imgs[0],rgb=True)
pl.add_mesh(mergedimg,rgb=True)
pl.show(jupyter_backend='trame')
#imgs[0].plot(rgb=True)