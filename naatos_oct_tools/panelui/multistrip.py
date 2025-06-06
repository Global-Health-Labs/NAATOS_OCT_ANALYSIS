import panel as pn
import param

import plotly.express as px

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import itertools
import numpy as np

import naatos_oct_tools.thorlabs_oct_file_reading
import naatos_oct_tools.oct_linear_scan_processing
import naatos_oct_tools.panelui.metricdefs as metricdefs
metrics = metricdefs.metrics;

from naatos_oct_tools.paths import folder_octexport_root


class OCTMultiStripMetricViewer(pn.viewable.Viewer):
    # follow https://panel.holoviz.org/tutorials/intermediate/interactivity.html
    # from   the "with pn.rx" class
    test_names = [];
    dfloaded = param.DataFrame();

    plotstyle = param.Selector(objects=['scatterVsLength','boxplotOfStrip'],default='boxplotOfStrip');

    metrics = param.ListSelector(
        default=['wax_width_px','seg_area_to_areafilled','num_paths'],
        objects=list(metrics.keys())
    );

    scans = param.ListSelector(
        default=[],
        objects=[],
    );

    plotpane = pn.pane.Plotly(sizing_mode='stretch_both', width_policy='max');

    def __init__(self, test_names, dfloaded, **params):
        super().__init__(**params)
        self.test_names = test_names;
        self.dfloaded = dfloaded;
        print('Loaded with {:d} tests:'.format(len(self.test_names)),self.test_names)

    def _mkfig(self):
        #df = dfloaded.copy();

        # restrict to test names
        df = self.dfloaded[self.dfloaded['Test name'].isin(self.test_names)].copy();

        #--------------- make some calculations ------------------
        df = naatos_oct_tools.oct_linear_scan_processing.process_along_strip_data_frame(df);
    
        #---------------- trace label generation ---------------
        trace_labels = [];
        trace_info = [];

        #trace_colors = [];

        #cyc_color = itertools.cycle(px.colors.qualitative.Alphabet)
        cyc_color = itertools.cycle(px.colors.qualitative.Light24)
        df_grouped_by_test = df.groupby('Test name');
        for studyname,dfv in df_grouped_by_test:
            #print(studyname)
            df1 = dfv.iloc[0];
            
            octstudy = df1['octstudy']
            #octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);

            trace_labels.append( octstudy.name )
            #trace_colors.append( next(cyc_color) );
            trace_info.append(
                dict(
                    octstudyname = octstudy.name,
                    
                    tracelabel = octstudy.name,
                    tracecolor = next(cyc_color),
                )
            )

        #----------------- plot creation --------------------
        # Make Detailed Metrics Plots Of 1-Device
        #metrics_to_show = ['wax_width_px','seg_area','seg_area_holes','wax_thickness2'];
        #metrics_to_show = ['wax_width_px','seg_area_to_areafilled','num_paths'];
        metrics_to_show = self.metrics;
        #metrics_to_show = self.param.metrics;
        nrows = len(metrics_to_show)
        fig = make_subplots(rows=nrows,shared_xaxes=True,vertical_spacing=0.02, )

        myrow = 0;

        #legendgroup = 'distances';
        for metric_col_name in metrics_to_show:
            myrow+=1;
            
            if True:
                for this_trace_info in trace_info:
                    dfv = df_grouped_by_test.get_group(this_trace_info['octstudyname'])

                    datax = dfv['slice'];
                    datay = dfv[metric_col_name]

                    fig.add_trace(
                        go.Scattergl(
                            x = datax,
                            y = datay,
                            mode='markers',
                            #type = 'heatmap',
                            #colorscale = 'jet'
                            name=this_trace_info['tracelabel'],
                            marker_color=this_trace_info['tracecolor'],
                            legendgroup=this_trace_info['tracelabel'],
                            showlegend=myrow==1,
                            #hoverinfo='name',
                            visible='legendonly',
                        ),
                        row=myrow,col=1,
                    )
            
            fig.update_yaxes(title=metric_col_name,row=myrow);

            if False:
                figtmp = px.scatter(df,x='slice',y=metric_col_name,color='Test name')
                fig.add_traces(figtmp.data,rows=myrow,cols=1);

            #break;




        # # setup legends per row
        # for i, yaxis in enumerate(fig.select_yaxes(col=1), 1):
        #     legend_name = f"legend{i}"
        #     fig.update_layout({legend_name: dict(y=yaxis.domain[1], yanchor="top")}, showlegend=True)
        #     fig.update_traces(row=i, legend=legend_name)
        fig.update_traces(marker_size=4)
        fig.update_layout(legend_tracegroupgap=0)

        fig.update_traces(xaxis='x{:}'.format(nrows))

        # fig.update_yaxes(title='pixels',row=1);
        # fig.update_yaxes(title='pixels^2',row=2);
        # fig.update_yaxes(title='ratios',row=3);
        # fig.update_yaxes(title='counts',row=4);

        fig.update_xaxes(title='distance along strip (px)',row=nrows,col=1);

        #fig.update_layout(hovermode='x',hoversubplots="axis",spikedistance=-1);
        #fig.update_layout(hovermode='x unified',spikedistance=-1,hoverdistance=5);
        fig.update_xaxes(showspikes=True, spikesnap="cursor", spikemode="across");

        #fig = px.imshow(sum_wax_strip_along_length[:,0:]);

        #fig.show(renderer='browser')
        #fig
        return fig;

    def _mkfig2(self):
        #df = dfloaded.copy();

        # restrict to test names
        df = self.dfloaded[self.dfloaded['Test name'].isin(self.test_names)].copy();

        #--------------- make some calculations ------------------
        df = naatos_oct_tools.oct_linear_scan_processing.process_along_strip_data_frame(df);
    
        #---------------- trace label generation ---------------
        trace_labels = [];
        trace_info = [];

        #trace_colors = [];
        import itertools
        #cyc_color = itertools.cycle(px.colors.qualitative.Alphabet)
        cyc_color = itertools.cycle(px.colors.qualitative.Light24)
        df_grouped_by_test = df.groupby('Test name');
        for studyname,dfv in df_grouped_by_test:
            #print(studyname)
            df1 = dfv.iloc[0];
            
            octstudy = df1['octstudy']
            #octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);

            trace_labels.append( octstudy.name )
            #trace_colors.append( next(cyc_color) );
            trace_info.append(
                dict(
                    octstudyname = octstudy.name,
                    
                    tracelabel = octstudy.name,
                    tracecolor = next(cyc_color),
                )
            )

        #----------------- plot creation --------------------
        # Make Detailed Metrics Plots Of 1-Device
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        #metrics_to_show = ['wax_width_px','seg_area','seg_area_holes','wax_thickness2'];
        #metrics_to_show = ['wax_width_px','seg_area_to_areafilled','num_paths'];
        metrics_to_show = self.metrics;
        #metrics_to_show = self.param.metrics;
        nrows = len(metrics_to_show)
        fig = make_subplots(rows=nrows,shared_xaxes=True,vertical_spacing=0.02, )

        myrow = 0;

        #legendgroup = 'distances';
        for metric_col_name in metrics_to_show:
            myrow+=1;
            
            if True:
                for this_trace_info in trace_info:
                    dfv = df_grouped_by_test.get_group(this_trace_info['octstudyname'])

                    datax = dfv['slice'];
                    datay = dfv[metric_col_name]

                    fig.add_trace(
                        go.Box(
                            y = datay,
                            #mode='markers',
                            name=this_trace_info['tracelabel'],
                            #marker_color=this_trace_info['tracecolor'],
                            legendgroup=this_trace_info['tracelabel'],
                            showlegend=myrow==1,
                            #hoverinfo='name',
                            #visible='legendonly',
                        ),
                        row=myrow,col=1,
                    )
            
            fig.update_yaxes(title=metric_col_name,row=myrow);

            if False:
                figtmp = px.scatter(df,x='slice',y=metric_col_name,color='Test name')
                fig.add_traces(figtmp.data,rows=myrow,cols=1);

            #break;

        fig.update_traces(marker_size=4)
        fig.update_layout(legend_tracegroupgap=0)

        fig.update_traces(xaxis='x{:}'.format(nrows))

        fig.update_xaxes(title='distance along strip (px)',row=nrows,col=1);
        return fig;

    #@pn.depends(plotpane.param.click_data, watch=True)
    def _click_handling(self,event):
        #print("click datatype:{:s} data:{:s}", type(event), str(event));
        if not event:
            return "No point clicked"
        try:
            point = event["points"][0]
            curvenumber = point['curveNumber'];
            index = point['pointIndex']
            x = point['x']
            y = point['y']
            if(type(x) is not str):
                # x was a number
                # so.... find the name
                scanname = self.plotpane.object.data[curvenumber].name;
            else:
                scanname = x;
        except Exception as ex:
            return f"You clicked the Plotly Chart! I could not determine the point: {ex}"
        
        return f"**You clicked point index {index} at ({x}, {y}) on curve ({scanname}) in the Plotly Chart!**"

    def _mkfigure(self,plotstyle,metrics):
        if(plotstyle=='scatterVsLength'):
            fig = self._mkfig();
        elif(plotstyle=='boxplotOfStrip'):
            fig = self._mkfig2();
        fig.layout.autosize = True;

        # self.plotpane = pn.pane.Plotly(
        #     fig,sizing_mode='stretch_both', width_policy='max',
        # );
        self.plotpane.object=fig;

        #pn.bind(self._click_handling,self.plotpane.param.click_data);
        iclicker_view = pn.bind(self._click_handling, self.plotpane.param.click_data);
        return pn.Column(self.plotpane,iclicker_view);
    
    def _launch_study_vlc(self,studyname,xpospx):
        import subprocess
        octstudy = naatos_oct_tools.thorlabs_oct_file_reading.OCT_Study_Folder(studyname,folder_octexport_root);
        subprocess.Popen([ "C:\Program Files\VideoLAN\VLC\vlc.exe" , str(octstudy.folder_study_processed.as_posix()) ] );
        


    def __panel__(self):
        return pn.Column(
            pn.Row(
                self.param.plotstyle,
                self.param.metrics,
                self.param.scans,
            ),
            #plotly_fig
            pn.bind(self._mkfigure,self.param.plotstyle,self.param.metrics)
        )
    
#obj2 = OCTMultiStripMetricViewer(['GHL_pyapp_20250512T0947', 'GHL_pyapp_20250512T0951', 'GHL_pyapp_20250512T0955', 'GHL_pyapp_20250512T0959', 'GHL_pyapp_20250512T1002', 'GHL_pyapp_20250512T1117', 'GHL_pyapp_20250512T1121', 'GHL_pyapp_20250512T1125', 'GHL_pyapp_20250512T1130', 'GHL_pyapp_20250512T1133', 'GHL_pyapp_20250512T1137', 'GHL_pyapp_20250512T1140', 'GHL_pyapp_20250512T1144', 'GHL_pyapp_20250512T1149', 'GHL_pyapp_20250512T1152', 'GHL_pyapp_20250512T1158', 'GHL_pyapp_20250512T1201', 'GHL_pyapp_20250512T1204', 'GHL_pyapp_20250512T1208', 'GHL_pyapp_20250512T1211', 'GHL_pyapp_20250512T1215', 'GHL_pyapp_20250512T1218', 'GHL_pyapp_20250512T1222', 'GHL_pyapp_20250512T1225', 'GHL_pyapp_20250512T1230', 'GHL_pyapp_20250512T1238', 'GHL_pyapp_20250512T1241', 'GHL_pyapp_20250512T1245', 'GHL_pyapp_20250512T1248', 'GHL_pyapp_20250512T1251', 'GHL_pyapp_20250512T1254', 'GHL_pyapp_20250512T1258', 'GHL_pyapp_20250512T1303']);
# finpn = pn.Column(obj);
