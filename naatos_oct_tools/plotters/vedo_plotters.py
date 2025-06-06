"""_summary_
vedo_plotters.py

Simon Ghionea

4-2-2025


Contains helper vedo applets to use for our analysis
"""

import vedo

from vedo.utils import mag
from vedo.pyplot import CornerHistogram, histogram

import vedo.vtkclasses as vtki

import numpy as np

class SimonSlicer3DPlotter(vedo.Plotter):
    """
    Generate a rendering window with slicing planes for the input Volume.

    Based off the VEDO example at:
    https://vedo.embl.es/docs/vedo/applications.html#Slicer3DPlotter
    """

    def __init__(
        self,
        volume: vedo.Volume,
        cmaps=("gist_ncar_r", "hot_r", "bone", "bone_r", "jet", "Spectral_r"),
        clamp=False,
        use_slider3d=False,
        show_histo=True,
        show_icon=True,
        draggable=False,
        slice_X=True,
        slice_Y=False,
        slice_Z=False,
        scalar_range:tuple=None,
        at=0,
        **kwargs,
    ):
        """
        Generate a rendering window with slicing planes for the input Volume.

        Arguments:
            cmaps : (list)
                list of color maps names to cycle when clicking button
            clamp : (bool)
                clamp scalar range to reduce the effect of tails in color mapping
            use_slider3d : (bool)
                show sliders attached along the axes
            show_histo : (bool)
                show histogram on bottom left
            show_icon : (bool)
                show a small 3D rendering icon of the volume
            draggable : (bool)
                make the 3D icon draggable
            at : (int)
                subwindow number to plot to
            **kwargs : (dict)
                keyword arguments to pass to Plotter.

        Examples:
            - [slicer1.py](https://github.com/marcomusy/vedo/tree/master/examples/volumetric/slicer1.py)

            <img src="https://vedo.embl.es/images/volumetric/slicer1.jpg" width="500">
        """
        ################################
        super().__init__(**kwargs)
        self.at(at)
        ################################

        cx, cy, cz, ch = "dr", "dg", "db", (0.3, 0.3, 0.3)
        if np.sum(self.renderer.GetBackground()) < 1.5:
            cx, cy, cz = "lr", "lg", "lb"
            ch = (0.8, 0.8, 0.8)

        if len(self.renderers) > 1:
            # 2d sliders do not work with multiple renderers
            use_slider3d = True

        self.volume = volume
        box = volume.box().alpha(0.2)
        self.add(box)

        if show_icon:
            volume_axes_inset = vedo.addons.Axes(
                box,
                xtitle=" ",
                ytitle=" ",
                ztitle=" ",
                yzgrid=False,
                xlabel_size=0,
                ylabel_size=0,
                zlabel_size=0,
                tip_size=0.08,
                axes_linewidth=3,
                xline_color="dr",
                yline_color="dg",
                zline_color="db",
            )

            self.add_inset(
                volume,
                volume_axes_inset,
                pos=(0.9, 0.9),
                size=0.15,
                c="w",
                draggable=draggable,
            )

        # inits
        la, ld = 0.7, 0.3  # ambient, diffuse
        dims = volume.dimensions()
        data = volume.pointdata[0]
        if(scalar_range is None):
            rmin, rmax = volume.scalar_range()
        else:
            rmin, rmax = scalar_range;
        if clamp:
            hdata, edg = np.histogram(data, bins=50)
            logdata = np.log(hdata + 1)
            # mean  of the logscale plot
            meanlog = np.sum(np.multiply(edg[:-1], logdata)) / np.sum(logdata)
            rmax = min(rmax, meanlog + (meanlog - rmin) * 0.9)
            rmin = max(rmin, meanlog - (rmax - meanlog) * 0.9)
            # print("scalar range clamped to range: ("
            #       + precision(rmin, 3) + ", " + precision(rmax, 3) + ")")

        self.cmap_slicer = cmaps[0]

        self.current_i = int(dims[0] / 2)
        self.current_j = int(dims[1] / 2)
        self.current_k = int(dims[2] / 2)

        self.xslice = None
        self.yslice = None
        self.zslice = None

        if(slice_X):
            self.xslice = volume.xslice(self.current_i).lighting("", la, ld, 0)
            self.xslice.name = "XSlice"
            self.xslice.cmap(self.cmap_slicer, vmin=rmin, vmax=rmax)
            self.add(self.xslice)

        self.histogram = None
        data_reduced = data
        if show_histo:
            # try to reduce the number of values to histogram
            dims = self.volume.dimensions()
            n = (dims[0] - 1) * (dims[1] - 1) * (dims[2] - 1)
            n = min(1000000, n)
            if data.ndim == 1:
                data_reduced = np.random.choice(data, n)
                self.histogram = histogram(
                    data_reduced,
                    # title=volume.filename,
                    bins=20,
                    logscale=True,
                    c=self.cmap_slicer,
                    bg=ch,
                    alpha=1,
                    axes=dict(text_scale=2),
                ).clone2d(pos=[-0.925, -0.88], size=0.4)
                self.add(self.histogram)

        #################
        def slider_function_x(widget, event):
            i = int(self.xslider.value)
            if i == self.current_i:
                return
            self.current_i = i
            self.xslice = volume.xslice(i).lighting("", la, ld, 0)
            self.xslice.cmap(self.cmap_slicer, vmin=rmin, vmax=rmax)
            self.xslice.name = "XSlice"
            self.remove("XSlice")  # removes the old one
            if 0 < i < dims[0]:
                self.add(self.xslice)
            self.render()

        def slider_function_y(widget, event):
            j = int(self.yslider.value)
            if j == self.current_j:
                return
            self.current_j = j
            self.yslice = volume.yslice(j).lighting("", la, ld, 0)
            self.yslice.cmap(self.cmap_slicer, vmin=rmin, vmax=rmax)
            self.yslice.name = "YSlice"
            self.remove("YSlice")
            if 0 < j < dims[1]:
                self.add(self.yslice)
            self.render()

        def slider_function_z(widget, event):
            k = int(self.zslider.value)
            if k == self.current_k:
                return
            self.current_k = k
            self.zslice = volume.zslice(k).lighting("", la, ld, 0)
            self.zslice.cmap(self.cmap_slicer, vmin=rmin, vmax=rmax)
            self.zslice.name = "ZSlice"
            self.remove("ZSlice")
            if 0 < k < dims[2]:
                self.add(self.zslice)
            self.render()

        if not use_slider3d:
            if(slice_X):
                self.xslider = self.add_slider(
                    slider_function_x,
                    0,
                    dims[0],
                    value=self.current_i,
                    title="slice @ x voxel",
                    title_size=0.5,
                    pos=[(0.8, 0.12), (0.95, 0.12)],
                    show_value=True,
                    c=cx,
                )
            if(slice_Y):
                self.yslider = self.add_slider(
                    slider_function_y,
                    0,
                    dims[1],
                    value=self.current_j,
                    title="slice @ y voxel",
                    title_size=0.5,
                    pos=[(0.8, 0.08), (0.95, 0.08)],
                    show_value=True,
                    c=cy,
                )
            if(slice_Z):
                self.zslider = self.add_slider(
                    slider_function_z,
                    0,
                    dims[2],
                    value=self.current_k,
                    title="slice @ z voxel",
                    title_size=0.6,
                    pos=[(0.8, 0.04), (0.95, 0.04)],
                    show_value=True,
                    c=cz,
                )

        else:  # 3d sliders attached to the axes bounds
            bs = box.bounds()
            slider_tube_scaling = 10.0;
            if(slice_X):
                self.xslider = self.add_slider3d(
                    slider_function_x,
                    pos1=(bs[0], bs[2], bs[4]),
                    pos2=(bs[1], bs[2], bs[4]),
                    xmin=0,
                    xmax=dims[0],
                    value=self.current_i,
                    #t=box.diagonal_size() / mag(box.xbounds()) * 0.6,
                    t=slider_tube_scaling,
                    c=cx,
                    show_value=True,
                )
            if(slice_Y):
                self.yslider = self.add_slider3d(
                    slider_function_y,
                    pos1=(bs[1], bs[2], bs[4]),
                    pos2=(bs[1], bs[3], bs[4]),
                    xmin=0,
                    xmax=dims[1],
                    value=self.current_j,
                    t=box.diagonal_size() / mag(box.ybounds()) * 0.6,
                    c=cy,
                    show_value=False,
                )
            if(slice_Z):
                self.zslider = self.add_slider3d(
                    slider_function_z,
                    pos1=(bs[0], bs[2], bs[4]),
                    pos2=(bs[0], bs[2], bs[5]),
                    xmin=0,
                    xmax=dims[2],
                    #value=int(dims[2] / 2),
                    value=self.current_k,
                    t=box.diagonal_size() / mag(box.zbounds()) * 0.6,
                    c=cz,
                    show_value=False,
                )

        #################
        def button_func(obj, ename):
            bu.switch()
            self.cmap_slicer = bu.status()
            for m in self.objects:
                if "Slice" in m.name:
                    m.cmap(self.cmap_slicer, vmin=rmin, vmax=rmax)
            self.remove(self.histogram)
            if show_histo:
                self.histogram = histogram(
                    data_reduced,
                    # title=volume.filename,
                    bins=20,
                    logscale=True,
                    c=self.cmap_slicer,
                    bg=ch,
                    alpha=1,
                    axes=dict(text_scale=2),
                ).clone2d(pos=[-0.925, -0.88], size=0.4)
                self.add(self.histogram)
            self.render()

        if len(cmaps) > 1:
            bu = self.add_button(
                button_func,
                states=cmaps,
                c=["k9"] * len(cmaps),
                bc=["k1"] * len(cmaps),  # colors of states
                size=16,
                bold=True,
            )
            if bu:
                bu.pos([0.04, 0.01], "bottom-left")


def _my_vedo_volume_clone(oldvol, deep=True):
    """Return a clone copy of the Volume. Alias of `copy()`."""
    if deep:
        newimg = vtki.vtkImageData()
        newimg.CopyStructure(oldvol.dataset)
        newimg.CopyAttributes(oldvol.dataset)
        newvol = vedo.Volume(newimg)
    else:
        newvol = vedo.Volume(oldvol.dataset)

    prop = vtki.vtkVolumeProperty()
    #prop = vtki.vtkImageProperty();
    prop.DeepCopy(oldvol.properties)
    newvol.actor.SetProperty(prop)
    newvol.properties = prop

    newvol.pipeline = vedo.utils.OperationNode("clone", parents=[oldvol], c="#bbd0ff", shape="diamond")
    return newvol

class SimonSlicer2DPlotter(vedo.Plotter):
    """
    A single slice of a Volume which always faces the camera,
    but at the same time can be oriented arbitrarily in space.
    """

    def __init__(self, vol: vedo.Volume, levels=(None, None), histo_color="red4", **kwargs):
        """
        A single slice of a Volume which always faces the camera,
        but at the same time can be oriented arbitrarily in space.

        Arguments:
            vol : (Volume)
                the Volume object to be isosurfaced.
            levels : (list)
                window and color levels
            histo_color : (color)
                histogram color, use `None` to disable it
            **kwargs : (dict)
                keyword arguments to pass to `Plotter`.

        <img src="https://vedo.embl.es/images/volumetric/read_volume3.jpg" width="500">
        """

        if "shape" not in kwargs:
            custom_shape = [  # define here the 2 rendering rectangle spaces
                dict(bottomleft=(0.0, 0.0), topright=(1, 1), bg="k9"),  # the full window
                dict(bottomleft=(0.8, 0.8), topright=(1, 1), bg="k8", bg2="lb"),
            ]
            kwargs["shape"] = custom_shape

        if "interactive" not in kwargs:
            kwargs["interactive"] = True

        super().__init__(**kwargs)

        self.user_mode("image")
        self.add_callback("KeyPress", self.on_key_press)

        #orig_volume = vol.clone(deep=False)
        print('test')
        orig_volume = _my_vedo_volume_clone(vol,deep=False);
        print('test2')
        # newvol = vedo.Volume(vol.dataset)
        # prop = vtki.vtkImageProperty();
        # prop.DeepCopy(vol.properties)
        # newvol.actor.SetProperty(prop)
        # newvol.properties = prop
        # newvol.pipeline = vedo.utils.OperationNode("clone", parents=[vol], c="#bbd0ff", shape="diamond")
        # orig_volume = newvol;

        self.volume = vol

        self.volume.actor = vtki.new("ImageSlice")

        self.volume.properties = self.volume.actor.GetProperty()
        self.volume.properties.SetInterpolationTypeToLinear()

        self.volume.mapper = vtki.new("ImageResliceMapper")
        self.volume.mapper.SetInputData(self.volume.dataset)
        #self.volume.mapper.SliceFacesCameraOn()
        #self.volume.mapper.SliceAtFocalPointOn()
        self.volume.mapper.SetAutoAdjustImageQuality(False)
        self.volume.mapper.BorderOff()

        # no argument will grab the existing cmap in vol (or use build_lut())
        self.lut = None
        self.cmap()

        if levels[0] and levels[1]:
            self.lighting(window=levels[0], level=levels[1])

        self.usage_txt = (
            "ESC                :rightarrow Quit/close window\n"
            "H                  :rightarrow Toggle this banner on/off\n"
            "Left click & drag  :rightarrow Modify luminosity and contrast\n"
            "SHIFT-Left click   :rightarrow Slice image obliquely\n"
            "SHIFT-Middle click :rightarrow Slice image perpendicularly\n"
            "SHIFT-R            :rightarrow Fly to closest cartesian view\n"
            "SHIFT-U            :rightarrow Toggle parallel projection"
        )

        self.usage = vedo.Text2D(
            self.usage_txt, font="Calco", pos="top-left", s=0.8, bg="yellow", alpha=0.25
        )

        hist = None
        if histo_color is not None:
            data = self.volume.pointdata[0]
            arr = data
            if data.ndim == 1:
                # try to reduce the number of values to histogram
                dims = self.volume.dimensions()
                n = (dims[0] - 1) * (dims[1] - 1) * (dims[2] - 1)
                n = min(1_000_000, n)
                arr = np.random.choice(self.volume.pointdata[0], n)
                hist = vedo.pyplot.histogram(
                    arr,
                    bins=12,
                    logscale=True,
                    c=histo_color,
                    ytitle="log_10 (counts)",
                    axes=dict(text_scale=1.9),
                ).clone2d(pos="bottom-left", size=0.4)

        axes = kwargs.pop("axes", 7)
        axe = None
        if axes == 7:
            axe = vedo.addons.RulerAxes(
                orig_volume, xtitle="x - ", ytitle="y - ", ztitle="z - "
            )

        box = orig_volume.box().alpha(0.25)

        # volume_axes_inset = vedo.addons.Axes(
        #     box,
        #     yzgrid=False,
        #     xlabel_size=0,
        #     ylabel_size=0,
        #     zlabel_size=0,
        #     tip_size=0.08,
        #     axes_linewidth=3,
        #     xline_color="dr",
        #     yline_color="dg",
        #     zline_color="db",
        #     xtitle_color="dr",
        #     ytitle_color="dg",
        #     ztitle_color="db",
        #     xtitle_size=0.1,
        #     ytitle_size=0.1,
        #     ztitle_size=0.1,
        #     title_font="VictorMono",
        # )

        self.at(0).add(self.volume, box, axe, self.usage, hist)
        #self.at(1).add(orig_volume, volume_axes_inset)
        self.at(0)  # set focus at renderer 0

    ####################################################################
    def on_key_press(self, evt):
        if evt.keypress == "q":
            self.break_interaction()
        elif evt.keypress.lower() == "h":
            t = self.usage
            if len(t.text()) > 50:
                self.usage.text("Press H to show help")
            else:
                self.usage.text(self.usage_txt)
            self.render()

    def cmap(self, lut=None, fix_scalar_range=False) -> "SimonSlicer2DPlotter":
        """
        Assign a LUT (Look Up Table) to colorize the slice, leave it `None`
        to reuse an existing Volume color map.
        Use "bw" for automatic black and white.
        """
        if lut is None and self.lut:
            self.volume.properties.SetLookupTable(self.lut)
        elif isinstance(lut, vtki.vtkLookupTable):
            self.volume.properties.SetLookupTable(lut)
        elif lut == "bw":
            self.volume.properties.SetLookupTable(None)
        self.volume.properties.SetUseLookupTableScalarRange(fix_scalar_range)
        return self

    def alpha(self, value: float) -> "SimonSlicer2DPlotter":
        """Set opacity to the slice"""
        self.volume.properties.SetOpacity(value)
        return self

    def auto_adjust_quality(self, value=True) -> "SimonSlicer2DPlotter":
        """Automatically reduce the rendering quality for greater speed when interacting"""
        self.volume.mapper.SetAutoAdjustImageQuality(value)
        return self

    def slab(self, thickness=0, mode=0, sample_factor=2) -> "SimonSlicer2DPlotter":
        """
        Make a thick slice (slab).

        Arguments:
            thickness : (float)
                set the slab thickness, for thick slicing
            mode : (int)
                The slab type:
                    0 = min
                    1 = max
                    2 = mean
                    3 = sum
            sample_factor : (float)
                Set the number of slab samples to use as a factor of the number of input slices
                within the slab thickness. The default value is 2, but 1 will increase speed
                with very little loss of quality.
        """
        self.volume.mapper.SetSlabThickness(thickness)
        self.volume.mapper.SetSlabType(mode)
        self.volume.mapper.SetSlabSampleFactor(sample_factor)
        return self

    def face_camera(self, value=True) -> "SimonSlicer2DPlotter":
        """Make the slice always face the camera or not."""
        self.volume.mapper.SetSliceFacesCameraOn(value)
        return self

    def jump_to_nearest_slice(self, value=True) -> "SimonSlicer2DPlotter":
        """
        This causes the slicing to occur at the closest slice to the focal point,
        instead of the default behavior where a new slice is interpolated between
        the original slices.
        Nothing happens if the plane is oblique to the original slices.
        """
        self.volume.mapper.SetJumpToNearestSlice(value)
        return self

    def fill_background(self, value=True) -> "SimonSlicer2DPlotter":
        """
        Instead of rendering only to the image border,
        render out to the viewport boundary with the background color.
        The background color will be the lowest color on the lookup
        table that is being used for the image.
        """
        self.volume.mapper.SetBackground(value)
        return self

    def lighting(self, window, level, ambient=1.0, diffuse=0.0) -> "SimonSlicer2DPlotter":
        """Assign the values for window and color level."""
        self.volume.properties.SetColorWindow(window)
        self.volume.properties.SetColorLevel(level)
        self.volume.properties.SetAmbient(ambient)
        self.volume.properties.SetDiffuse(diffuse)
        return self