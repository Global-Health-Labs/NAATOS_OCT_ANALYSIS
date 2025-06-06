import SimpleITK as sitk
import matplotlib.pyplot as plt

from ipywidgets import interact, interactive
from ipywidgets import widgets

import numpy as np
import ipywidgets as ipyw


def sitk_myshow(img, title=None, margin=0.05, dpi=80, cmap="gray", defaultslice=None):
    nda = sitk.GetArrayFromImage(img)

    spacing = img.GetSpacing()
    slicer = False

    if nda.ndim == 3:
        # fastest dim, either component or x
        c = nda.shape[-1]

        # the the number of components is 3 or 4 consider it an RGB image
        if not c in (3, 4):
            slicer = True

    elif nda.ndim == 4:
        c = nda.shape[-1]

        if not c in (3, 4):
            raise RuntimeError("Unable to show 3D-vector Image")

        # take a z-slice
        slicer = True

    if slicer:
        ysize = nda.shape[1]
        xsize = nda.shape[2]
    else:
        ysize = nda.shape[0]
        xsize = nda.shape[1]

    # Make a figure big enough to accommodate an axis of xpixels by ypixels
    # as well as the ticklabels, etc...
    figsize = (1 + margin) * ysize / dpi, (1 + margin) * xsize / dpi

    def callback(z=None):
        extent = (0, xsize * spacing[1], ysize * spacing[0], 0)

        fig = plt.figure(figsize=figsize, dpi=dpi)

        # Make the axis the right size...
        ax = fig.add_axes([margin, margin, 1 - 2 * margin, 1 - 2 * margin])

        if z is None:
            ax.imshow(nda, extent=extent, interpolation=None, cmap=cmap)
        else:
            ax.imshow(nda[z, ...], extent=extent, interpolation=None, cmap=cmap)

        if title:
            plt.title(title)

        plt.show()

    if slicer:
        if(defaultslice is None):
            interact(callback, z=(0, nda.shape[0] - 1))
        else:
            #interact(callback, z=(0, nda.shape[0] - 1, 1, defaultslice))
            interact(callback, z=widgets.IntSlider(min=0, max=nda.shape[0] - 1, value=defaultslice))
    else:
        callback()


def sitk_myshow3d(img, xslices=[], yslices=[], zslices=[], title=None, margin=0.05, dpi=80):
    size = img.GetSize()
    img_xslices = [img[s, :, :] for s in xslices]
    img_yslices = [img[:, s, :] for s in yslices]
    img_zslices = [img[:, :, s] for s in zslices]

    maxlen = max(len(img_xslices), len(img_yslices), len(img_zslices))

    img_null = sitk.Image([0, 0], img.GetPixelID(), img.GetNumberOfComponentsPerPixel())

    img_slices = []
    d = 0

    if len(img_xslices):
        img_slices += img_xslices + [img_null] * (maxlen - len(img_xslices))
        d += 1

    if len(img_yslices):
        img_slices += img_yslices + [img_null] * (maxlen - len(img_yslices))
        d += 1

    if len(img_zslices):
        img_slices += img_zslices + [img_null] * (maxlen - len(img_zslices))
        d += 1

    if maxlen != 0:
        if img.GetNumberOfComponentsPerPixel() == 1:
            img = sitk.Tile(img_slices, [maxlen, d])
        # TODO check in code to get Tile Filter working with VectorImages
        else:
            img_comps = []
            for i in range(0, img.GetNumberOfComponentsPerPixel()):
                img_slices_c = [sitk.VectorIndexSelectionCast(s, i) for s in img_slices]
                img_comps.append(sitk.Tile(img_slices_c, [maxlen, d]))
            img = sitk.Compose(img_comps)

    sitk_myshow(img, title, margin, dpi)




# def sitk_myshow_widget(sitk_image):


# https://github.com/mohakpatel/ImageSliceViewer3D
class ImageSliceViewer3DJupyter:
    """ 
    ImageSliceViewer3D is for viewing volumetric image slices in jupyter or
    ipython notebooks. 
    
    User can interactively change the slice plane selection for the image and 
    the slice plane being viewed. 

    Argumentss:
    Volume = 3D input image
    figsize = default(8,8), to set the size of the figure
    cmap = default('plasma'), string for the matplotlib colormap. You can find 
    more matplotlib colormaps on the following link:
    https://matplotlib.org/users/colormaps.html
    
    """
    
    def __init__(self, volume, figsize=(8,8), cmap='gray'):
        self.volume = volume
        self.figsize = figsize
        self.cmap = cmap
        self.v = [np.min(volume), np.max(volume)]
        
        # Call to select slice plane
        ipyw.interact(self.view_selection, view=ipyw.RadioButtons(
            options=['x-y','y-z', 'z-x'], value='x-y', 
            description='Slice plane selection:', disabled=False,
            style={'description_width': 'initial'}))
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        orient = {"y-z":[1,2,0], "z-x":[2,0,1], "x-y": [0,1,2]}
        self.vol = np.transpose(self.volume, orient[view])
        maxZ = self.vol.shape[2] - 1
        
        # Call to view a slice within the selected slice plane
        ipyw.interact(self.plot_slice, 
            z=ipyw.IntSlider(min=0, max=maxZ, step=1, continuous_update=False, 
            description='Image Slice:'))
        
    def plot_slice(self, z):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)
        plt.imshow(self.vol[:,:,z], cmap=plt.get_cmap(self.cmap), 
            vmin=self.v[0], vmax=self.v[1]);





class ImageSITKSliceViewer3DJupyter:
    """ 
    ImageSliceViewer3D is for viewing volumetric image slices in jupyter or
    ipython notebooks. 
    
    User can interactively change the slice plane selection for the image and 
    the slice plane being viewed. 

    Argumentss:
    Volume = 3D input image
    figsize = default(8,8), to set the size of the figure
    cmap = default('plasma'), string for the matplotlib colormap. You can find 
    more matplotlib colormaps on the following link:
    https://matplotlib.org/users/colormaps.html
    
    """

    # SLICE_OPTS = {
    #     "y-z [1,2,0]":[1,2,0],
    #     "z-x [2,0,1]":[2,0,1],
    #     "x-y [0,1,2]":[0,1,2]
    # };
    
    def __init__(self, sitk_image, figsize=(8,8), cmap='gray'):
        self.spacing = sitk_image.GetSpacing();

        self.volume = sitk.GetArrayViewFromImage(sitk_image);
        self.figsize = figsize
        self.cmap = cmap
        self.v = [np.min(self.volume), np.max(self.volume)]
        
        # Call to select slice plane
        ipyw.interact(
            self.view_selection,
            view=
                ipyw.RadioButtons(
                    #options=list(self.SLICE_OPTS.keys()), value=list(self.SLICE_OPTS.keys())[0],
                    options=["y-z","z-x","x-y"],value="z-x",
                    description='Slice plane selection (image was {:s}):'.format(str(sitk_image.GetSize())), disabled=False,
                    style={'description_width': 'initial'}
                )
        )
    
    def view_selection(self, view):
        # Transpose the volume to orient according to the slice plane selection
        #orient = {"y-z [1,2,0]":[1,2,0], "z-x [2,0,1]":[2,0,1], "x-y [0,1,2]": [0,1,2]}
        if(len(self.volume.shape)==3):
            if(view=="y-z"):
                self.transpose_indices = [1,2,0];
            elif(view=="z-x"):
                self.transpose_indices = [2,0,1];
            elif(view=="x-y"):
                self.transpose_indices = [0,1,2];
        elif(len(self.volume.shape)==4):
            if(view=="y-z"):
                self.transpose_indices = [1,2,0,3];
            elif(view=="z-x"):
                self.transpose_indices = [2,0,1,3];
            elif(view=="x-y"):
                self.transpose_indices = [0,1,2,3];
        self.vol = np.transpose(self.volume, self.transpose_indices)
        maxZ = self.vol.shape[2] - 1
        
        # Call to view a slice within the selected slice plane
        ipyw.interact(self.plot_slice, 
            z=ipyw.IntSlider(min=0, max=maxZ, step=1, continuous_update=False, 
            description='Image Slice:'))
        
    def plot_slice(self, z):
        # Plot slice for the given plane and slice
        self.fig = plt.figure(figsize=self.figsize)

        extent = (0, self.vol.shape[1] * self.spacing[1], self.vol.shape[0] * self.spacing[0], 0)

        plt.imshow(self.vol[:,:,z,...], extent=extent, cmap=plt.get_cmap(self.cmap), 
            interpolation=None, 
            vmin=self.v[0], vmax=self.v[1]
        );