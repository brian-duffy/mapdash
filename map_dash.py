# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapDash
                                 A QGIS plugin
 This plugin transforms a QGIS project to a web dashboard
                              -------------------
        begin                : 2015-12-09
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Brian Duffy
        email                : duffy.brian.m@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import *
from PyQt4.QtCore import QSize
from qgis.core import *
from qgis import *
from qgis.gui import *
import qgis.utils
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from map_dash_dialog import MapDashDialog
import os.path
import os #for file writing/folder actions
import shutil #for reverse removing directories
import urllib # to get files from the web
import time
import re
import fileinput
import webbrowser 
import sys 
from custom_utils import *

class MapDash:
    """QGIS Plugin Implementation."""
    

    def __init__(self, iface):
        """Constructor. 
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'MapDash_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = MapDashDialog()
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Web Dashboard')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'MapDash')
        self.toolbar.setObjectName(u'MapDash')

       

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MapDash', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/MapDash/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Web Dashboard'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def errorMessage(self, message):
         widg = QMessageBox()
         widg.setWindowTitle("Error!")
         widg.setText(message)
         widg.exec_()


    def run(self):        
        # show the dialog
        canvas = qgis.utils.iface.mapCanvas()
        allLayers = canvas.layers()
        for layer in allLayers:
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.layerCombo.addItem( layer.name(), layer )
                self.dlg.iconLayerSelector.addItem(layer.name(), layer)
        layers = self.iface.legendInterface().layers()
        if (layers == []):
            self.errorMessage("To use this plugin please first load layers into the table of contents")
            return
        else:
            self.dlg.show()
            self.layersx = []
            for idx,layer in enumerate(layers):
                if layer.type() == QgsMapLayer.VectorLayer:
                    obj = [layer, layer.name(), self.dlg.ic_map_marker, 2 , 3]
                    self.layersx.insert(idx, obj)
                    self.saveMarker()
            # Layers exist, load plugin parameters
            self.zoomLevel()
            self.layersSelected = False
            self.iconPicker()
            self.iconColourSelect()
            self.markerColourSelect()
            self.saveCurrentIcon()
            self.getAllLayers()
            self.getMapCenter()
            self.dlg.getCenterButton.clicked.connect(self.getMapCenter)
            self.dlg.getFilePathButton.clicked.connect(self.getFilePath)
            self.dlg.attribCustom.stateChanged.connect(self.customAttrib)
            self.dlg.mapBoxCheckBox.stateChanged.connect(self.mapBox)
            self.dlg.osmCheckBox.stateChanged.connect(self.osmSelect)
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result == 1:
            if (self.layersSelected == True):
                self.executeMap()
                self.getAllParams()
                # do something useful, do checks here to ensure passed variables are correct.
                if (self.layersSelected == True):
                    index = self.dlg.layerCombo.currentIndex()
                    layer = self.dlg.layerCombo.itemData(index)
                    iter = layer.getFeatures()
                    for feature in iter:
                        geom = feature.geometry()
                        if geom.type() == QGis.Point:
                            x = geom.asPoint()
             # Case if no layer selected, use this for future error handling
            elif(self.layersSelected == False): self.errorMessage("Please fill in all of the fields before attempting to continue")


    def getAllLayers(self):
        self.layersSelected = True
        #layers = self.iface.legendInterface().layers()
        layerName = []
        layerFeature = []
        dataType = []
        canvas = qgis.utils.iface.mapCanvas()
        allLayers = canvas.layers()
        for layer in allLayers:
            layerType = layer.type()
            if layerType == QgsMapLayer.VectorLayer:
               layerName.append(layer.name())
               layerFeature.append(layer.featureCount())
            if not layer.isValid():
                print "Layer failed to load"
        self.listing = QStandardItemModel(0,2)
        self.listing.setHorizontalHeaderLabels(['Name','Features','Datatype'])       
        self.dlg.tableView.setModel(self.listing)
        i=0

        for ind in layerName:
            itemName = QStandardItem(layerName[i])
            itemFeature = QStandardItem('%d'  %layerFeature[i])
            itemName.setEditable(False)
            itemFeature.setEditable(False)
            self.listing.appendRow([itemName, itemFeature])
            i = i + 1
        # Check for duplicate names in layers
        if(len(layerName)!=len(set(layerName))): self.errorMessage('Duplicate layer names detected, please differentiate layers by name before continuing')


    def getMapCenter(self):
        str = self.dlg.layerCombo
        currentLayer =  str.itemData(str.currentIndex())
        self.dlg.centerLat.setText("%.4f" %currentLayer.extent().center().x())
        self.dlg.centerLong.setText("%.4f" %currentLayer.extent().center().y())
        layers = self.iface.legendInterface().layers()


    def zoomLevel(self):
        self.dlg.mapZoomLevel.valueChanged.connect(self.slider_moved)
        self.dlg.zoomVal.setText("%r" %self.dlg.mapZoomLevel.sliderPosition())
        
    def slider_moved(self,position):
        self.dlg.zoomVal.setText("%d" %position)

   # def layerChoice(self):
    #    print "choice"
     #   print self.layerChoice
      #  pass
        #self.dlg.visibleLayers.addItem("Show All")
        #self.dlg.visibleLayers.addItem("Show None")

    def mapBox(self):
        self.dlg.baseMaps.clear()
        mapBoxMaps = ['Mapbox Streets','Mapbox Light','Mapbox Dark','Mapbox Satellite','Mapbox Streets Satellite', 'Mapbox Wheatpaste',
                          'Mapbox Streets Basic', 'Mapbox Comic', 'Mapbox Outdoors','Mapbox Run/Bike/Hike','Mapbox Pencil','Mapbox Pirates',
                          'Mapbox Emerald','Mapbox High Contrast']
        if self.dlg.mapBoxCheckBox.isChecked(): 
            self.dlg.osmCheckBox.setChecked(False)
            self.dlg.mapboxAPIKey.setEnabled(True)
            for map in mapBoxMaps: self.dlg.baseMaps.addItem(str(map))
        else:
            self.dlg.mapboxAPIKey.setEnabled(False)

    def osmSelect(self):
        self.dlg.baseMaps.clear()
        OSMMaps = ['OSM Standard','OSM Black & White','Stamen Toner','OSM DE', 'OSM HOT','OpenSeaMap','Thunderforest Cycle','Thunderforest Transport',
                   'Thunderforest Landscape','Thunderforest Outdoors','OpenMapSurfer Roads','OpenMapSurfer adminb','OpenMapSurfer roadsg','MapQuestOpen OSM',
                   'MapQuestOpen Aerial','Stamen Terrain','Stamen Watercolor','OpenWeatherMap Clouds','OpenWeatherMap Precipitation','OpenWeatherMap Rain',
                   'OpenWeatherMap Pressure','OpenWeatherMap Wind','OpenWeatherMap Temp','OpenWeatherMap Snow']
        if self.dlg.osmCheckBox.isChecked(): 
            self.dlg.mapBoxCheckBox.setChecked(False)
            self.dlg.mapboxAPIKey.setEnabled(False)
            for map in OSMMaps: self.dlg.baseMaps.addItem(str(map))
        else:
            self.dlg.mapboxAPIKey.setEnabled(False)
        pass

    def customAttrib(self):
        if self.dlg.attribCustom.isChecked():
            self.dlg.attribCustomString.setEnabled(True)
        else:
            self.dlg.attribCustomString.setEnabled(False)
       

    def iconPicker(self):
        self.dlg.markerColourBox.activated.connect(self.markerColourSelect)
        self.dlg.iconColourBox.activated.connect(self.iconColourSelect)
        self.dlg.iconLayerSelector.activated.connect(self.saveMarker)


    def markerColourSelect(self):
        currText = self.dlg.markerColourBox.currentText()
        if (currText == "Custom"):
            self.dlg.markerColourRed.setEnabled(True)
            self.dlg.markerColourGreen.setEnabled(True)
            self.dlg.markerColourBlue.setEnabled(True)
        else:
            self.dlg.markerColourRed.setEnabled(False)
            self.dlg.markerColourGreen.setEnabled(False)
            self.dlg.markerColourBlue.setEnabled(False)
            currentLayer = self.dlg.iconLayerSelector.currentIndex()
            self.layersx[currentLayer][3] = self.dlg.markerColourBox.currentIndex()
        
    def iconColourSelect(self):
        currText = self.dlg.iconColourBox.currentText()
        if (currText == "Custom"):
            self.dlg.iconColourRed.setEnabled(True)
            self.dlg.iconColourGreen.setEnabled(True)
            self.dlg.iconColourBlue.setEnabled(True)
        else:
            self.dlg.iconColourRed.setEnabled(False)
            self.dlg.iconColourGreen.setEnabled(False)
            self.dlg.iconColourBlue.setEnabled(False)
            currentLayer = self.dlg.iconLayerSelector.currentIndex()
            self.layersx[currentLayer][4] = self.dlg.iconColourBox.currentIndex()

    def saveMarker(self):
        currentLayer = self.dlg.iconLayerSelector.currentIndex()
        self.dlg.markerColourBox.setCurrentIndex(self.layersx[currentLayer][3])
        self.dlg.iconColourBox.setCurrentIndex(self.layersx[currentLayer][4])
        self.dlg.iconSelectorGroup.buttonClicked.connect(self.saveCurrentIcon)
        savedIcon = self.layersx[currentLayer][2]
        savedIcon.setChecked(True)

    def saveCurrentIcon(self):
        currentLayer = self.dlg.iconLayerSelector.currentIndex()
        self.layersx[currentLayer][2] = self.dlg.iconSelectorGroup.checkedButton()

    def getFilePath(self):    
        self.outFileName = str(QFileDialog.getExistingDirectory(self.dlg.widget, "Output Project Name:"))
        self.dlg.filePathWindow.clear()
        self.dlg.filePathWindow.setText(self.outFileName)

    def getAllParams(self):
        print "Getting all parameters"
        print "Layer + icon list : " , self.layersx
        print "Center map at Lat: " , self.dlg.centerLat.toPlainText (), " Long: ", self.dlg.centerLong.toPlainText(), "\n"
        print "Zoom level: " , self.dlg.zoomVal.text()
        print "Show visible layers: " , self.dlg.visibleLayers.currentText()
        print "Is mapbox enabled? " , self.dlg.mapBoxCheckBox.isChecked()
        if (self.dlg.mapBoxCheckBox.isChecked()): print " Key: ", self.dlg.mapboxAPIKey.toPlainText()
        print "Is normal basemaps enabled ", self.dlg.osmCheckBox.isChecked()
        print "Using basemap: ", self.dlg.baseMaps.currentText()
        print "Current directory for output is ", self.dlg.filePathWindow.toPlainText() 
        print "Is side menu selected " , self.dlg.sideMenuButton.isChecked()
        print "Is horizontal menu selected ", self.dlg.horizontalLayout.isChecked()
        print "Is minimap normal selected: " , self.dlg.minimapButton.isChecked()
        print "Is globe minimap selected: " , self.dlg.globeMinimapButton.isChecked()
        print "Is scale bar selected: " , self.dlg.scaleBarButton.isChecked()
        print "Is fullscreen enabled: " , self.dlg.fullScreenButton.isChecked()
        print "Is cluttering enabled: " , self.dlg.clutterPointsButton.isChecked()
        print "Is loading icon enabled: " , self.dlg.loadingIconButton.isChecked()

        pass




    def executeMap(self):
        # Time to set up folder structure for the exported plugin
        newDir = ['js', 'css','images','lib','data','maps','reports']
        self.p = Custom_Utils()
        self.p.makeDir(self.dlg.filePathWindow.toPlainText(), newDir)
        
        # Copy the magical Leaflet directory and any addons
        copys = ['leaflet','leaflet.awesome-markers','leaflet.fullscreen','leaflet.globeminimap','chroma.js',
                 'leaflet.minimap','leaflet.cluster','heatmap.js','leaflet.heat','leaflet.loading','leaflet.search',
                 'jquery','chart.js','pure','pure-layout-side-menu']
        self.p.copyDir(self.dlg.filePathWindow.toPlainText(), copys, 'lib')
        dataFolder = os.path.join(os.getcwd(),self.dlg.filePathWindow.toPlainText(), 'data')
        self.p.copyFile(self.dlg.filePathWindow.toPlainText(),'maps.min.css','css')
        
        text = """@import url(http://yui.yahooapis.com/pure/0.3.0/pure-min.css);
html{background: #111;}
body{
  max-width: auto;
  max-height: auto;
  text-align: center;
  background: solid white;
  border-color: white;
  overflow:hidden;
  padding-bottom: 20cm;
}
#main-wrapper {
    width: 100%;
    color: solid white;
    height: 100%;
    position: relative;
    border-width: 10px;
    border-style: solid;
    border-width: 3px;
    border-top-color: white;
    border-right-color: white;
    border-bottom-color: white;
    padding-bottom: 20cm;
}
#map {
    width: 100%;
    height: 100%;
    position: relative;
    padding-bottom: 20cm;
}
#map img{
    width: 50px;
    height: 50px;
}
#maplogo img{
    display: block;
    width: 100% !important;
    height: auto !important;
}
.legend {
    line-height: 18px;
    color: #555;
    background: white;
    padding: 5px;
    bottom: 30px;
}
.legend i {
    width: 18px;
    height: 18px;
    float: left;
    margin-right: 8px;
    opacity: 0.7;
}
"""
        self.p.fileControl(self.dlg.filePathWindow.toPlainText(), 'css','main.css','w',text)
        canvas = qgis.utils.iface.mapCanvas()
        allLayers = canvas.layers()
        exp_crs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId)
        """
           *****  Credit goes to Tom Chadwin for the following lines of code to create JSON strings
             https://github.com/geolicious/qgis2leaf *****
        """     
        self.scripts = []        
        self.varNames =[]                                                             
        for id, i in enumerate(allLayers):
            if i.type() == 0:
                # This is for vectors
                qgis.core.QgsVectorFileWriter.writeAsVectorFormat(i, dataFolder + os.sep + 'exp_'  + 
                                      re.sub('[\W_]+', '', i.name()) + '.js', 'utf-8', exp_crs, 'GeoJson')
                f2 = open(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js', "r+")
                old = f2.read()
                f2.seek(0)
                f2.write("var exp_" + str(re.sub('[\W_]+', '', i.name())) + " = " + old) # Assign variable to json string
                f2.close()
                # Single marker points
                if i.rendererV2().dump()[0:6] == 'SINGLE' and i.geometryType() == 0:
                    # Get current colour scheme from QGIS TOC
                    color_str = str(i.rendererV2().symbol().color().name())
                    radius_str = str(i.rendererV2().symbol().size() * 2)
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    transp_str2 = str(i.rendererV2().symbol().alpha())
                    print color_str, radius_str
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                            "fillColor" : \"""" + color_str + """\",
                            "color": \"""" + color_str +"""\",
                            "radius_qgis2leaf": """ + radius_str + """, 
                            "transp_qgis2leaf": """ + transp_str + """, 
                            "transp_fill_qgis2leaf": """ + transp_str2 + """, 
                                """ )
                        sys.stdout.write(line)
                # Single marker polylines
                if i.rendererV2().dump()[0:6] == 'SINGLE' and i.geometryType() == 1:
                    color_str = str(i.rendererV2().symbol().color().name())
                    radius_str = str(i.rendererV2().symbol().width() * 5)
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    transp_str2 = str(i.rendererV2().symbol().alpha())
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                            "fillColor" : \"""" + color_str + """\",
                            "color": \"""" + color_str +"""\",
                            "radius_qgis2leaf": """ + radius_str + """, 
                            "transp_qgis2leaf": """ + transp_str + """, 
                            "transp_fill_qgis2leaf": """ + transp_str2 + """, 
                            """ )
                        sys.stdout.write(line)
                # Single marker polygons
                if i.rendererV2().dump()[0:6] == 'SINGLE' and i.geometryType() == 2:
                    if i.rendererV2().symbol().symbolLayer(0).layerType() == 'SimpleLine':
                        color_str = 'none'
                        borderColor_str = str(i.rendererV2().symbol().color().name())
                        radius_str = str(i.rendererV2().symbol().symbolLayer(0).width() * 5)
                    else:
                        color_str = str(i.rendererV2().symbol().color().name())
                        borderColor_str = str(i.rendererV2().symbol().symbolLayer(0).borderColor().name())
                        radius_str = str(i.rendererV2().symbol().symbolLayer(0).borderWidth() * 5)
                        transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                        transp_str2 = str(i.rendererV2().symbol().alpha())
                        for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                            line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                            "fillColor": \"""" +  color_str + """\",
                             "color": \"""" + color_str +"""\",
                            "border_color_qgis2leaf": '""" + borderColor_str + """',
                            "radius_qgis2leaf": """ + radius_str + """, 
                            "transp_qgis2leaf": """ + transp_str + """, 
                            "transp_fill_qgis2leaf": """ + transp_str2 + """,
                                 """ )
                            sys.stdout.write(line)
                # Begin Styling for categorized points
                if i.rendererV2().dump()[0:11] == 'CATEGORIZED' and i.geometryType() == 0:
                    iter = i.getFeatures()
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())
                    categories = i.rendererV2().categories()
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    for feat in iter:
                        fid = feat.id()
                        attribute_map = feat.attributes()
                        catindex = i.rendererV2().categoryIndexForValue(str(attribute_map[attrvalindex]))
                        #print catindex
                        if catindex != -1: 
                            color_str.append(str(categories[catindex].symbol().color().name()))
                            radius_str.append(str(categories[catindex].symbol().size() * 2))
                            transp_str2.append(str(categories[catindex].symbol().alpha()))
                        else: 
                            color_str.append('#FF00FF')
                            radius_str.append('4')
                            transp_str2.append('1')
	                        #print color_str
                    qgisLeafId = 0
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        addOne = str(line).count(""""type": "Feature", "properties": { """)
                        if qgisLeafId < len(color_str):
                            line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                                "id_qgis2leaf": """ + str(qgisLeafId) + """,
                                "fillColor": \"""" + str(color_str[qgisLeafId]) +"""\",
                                "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                                "radius_qgis2leaf": """ + str(radius_str[qgisLeafId]) + """,
                                "transp_qgis2leaf": """ + str(transp_str) + """,
                                "transp_fill_qgis2leaf": """ +str(transp_str2[qgisLeafId]) + """, 
                                    """ )
                        else:
                            line = line.replace(" "," ")
                        sys.stdout.write(line)
                        qgisLeafId = qgisLeafId+addOne
                # Categorized lines
                if i.rendererV2().dump()[0:11] == 'CATEGORIZED' and i.geometryType() == 1:
                    iter = i.getFeatures()
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())
                    categories = i.rendererV2().categories()
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    for feat in iter:
                        fid = feat.id()
                        attribute_map = feat.attributes()
                        catindex = i.rendererV2().categoryIndexForValue(str(attribute_map[attrvalindex]))
                        #print catindex
                        if catindex != -1: 
                            color_str.append(str(categories[catindex].symbol().color().name()))
                            radius_str.append(str(categories[catindex].symbol().width() * 5))
                            transp_str2.append(str(categories[catindex].symbol().alpha()))
                        else: 
                            color_str.append('#FF00FF')
                            radius_str.append('4')
                            transp_str2.append('1')
                            #print color_str
                    qgisLeafId = 0
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        addOne = str(line).count(""""type": "Feature", "properties": { """)
                        if qgisLeafId < len(color_str):
                            line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": {
                            "id_qgis2leaf": """ + str(qgisLeafId) + """, 
                            "color_qgis2leaf": \"""" + str(color_str[qgisLeafId]) +"""\",
                            "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                            "radius_qgis2leaf": """ + str(radius_str[qgisLeafId]) + """,
                            "transp_qgis2leaf": """ + str(transp_str) + """, 
                            "transp_fill_qgis2leaf": """ + str(transp_str2[qgisLeafId]) + """,
                            """)
                        else:
                            line = line.replace(" "," ")
                        sys.stdout.write(line)
                        qgisLeafId = qgisLeafId+addOne
                # Categorized polygons
                if i.rendererV2().dump()[0:11] == 'CATEGORIZED' and i.geometryType() == 2:
                    iter = i.getFeatures()
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())
                    categories = i.rendererV2().categories()
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    for feat in iter:
                        fid = feat.id()
                        attribute_map = feat.attributes()
                        catindex = i.rendererV2().categoryIndexForValue(str(attribute_map[attrvalindex]))
                        #print catindex
                        if catindex != -1: 
                            color_str.append(str(categories[catindex].symbol().color().name()))
                            transp_str2.append(str(categories[catindex].symbol().alpha()))
                        else: 
                            color_str.append('#FF00FF')
                            transp_str2.append('1')
                            #print color_str
                        qgisLeafId = 0
                        for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                            addOne = str(line).count(""""type": "Feature", "properties": { """)
                            if qgisLeafId < len(color_str):
                                line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                                    "id_qgis2leaf": """ +  str(qgisLeafId) + """, 
                                    "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                                    "color_qgis2leaf": \"""" + str(color_str[qgisLeafId]) + """\", 
                                    "transp_qgis2leaf": """ +  str(transp_str) + """, 
                                    "transp_fill_qgis2leaf": """ + str(transp_str2[qgisLeafId]) + """,
                                             """ )
                            else:
                                line = line.replace(" "," ")
                            sys.stdout.write(line)
                            qgisLeafId = qgisLeafId+addOne	
                # Graduated marker points
                if i.rendererV2().dump()[0:9] == 'GRADUATED' and i.geometryType() == 0:
				    # every json entry needs a unique id:
                    iter = i.getFeatures()
                    #what is the value based on:
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())	
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    for feat in iter:
                        if str(feat.attributes()[attrvalindex]) != 'NULL':
                            value = int(feat.attributes()[attrvalindex])
                        elif str(feat.attributes()[attrvalindex]) == 'NULL':
                            value = None
                        for r in i.rendererV2().ranges():
                            if value >= r.lowerValue() and value <= r.upperValue() and value != None:
                                color_str.append(str(r.symbol().color().name()))
                                radius_str.append(str(r.symbol().size() * 2))
                                transp_str2.append(str(r.symbol().alpha()))
                                break
                            elif value == None:
                                color_str.append('#FF00FF')
                                radius_str.append('4')
                                transp_str2.append('1')
                                break
                    qgisLeafId = 0
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        addOne = str(line).count(""""type": "Feature", "properties": { """)
                        if qgisLeafId < len(color_str):
                            line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                                "id_qgis2leaf": """ + str(qgisLeafId) + """,
                                "color_qgis2leaf": '""" + str(color_str[qgisLeafId]) + """', 
                                "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                                "radius_qgis2leaf": """ + str(radius_str[qgisLeafId]) + """, 
                                "transp_qgis2leaf": """ + str(transp_str) + """, 
                                "transp_fill_qgis2leaf": """ +str(transp_str2[qgisLeafId]) + """,
                                         """ )
                        else:
                            line = line.replace(" "," ")
                        sys.stdout.write(line)
                        qgisLeafId = qgisLeafId+addOne
                # Graduated polyines styling               
                if i.rendererV2().dump()[0:9] == 'GRADUATED' and i.geometryType() == 1:
                    # every json entry needs a unique id:
                    iter = i.getFeatures()
                    #what is the value based on:
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())	
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    for feat in iter:
                        if str(feat.attributes()[attrvalindex]) != 'NULL':
                            value = int(feat.attributes()[attrvalindex])
                        elif str(feat.attributes()[attrvalindex]) == 'NULL':
                            value = None
                        for r in i.rendererV2().ranges():
                            if value >= r.lowerValue() and value <= r.upperValue() and value != None:
                                color_str.append(str(r.symbol().color().name()))
                                radius_str.append(str(r.symbol().width() * 5))
                                transp_str2.append(str(r.symbol().alpha()))
                                break
                            elif value == None:
                                color_str.append('#FF00FF')
                                radius_str.append('4')
                                transp_str2.append('1')
                                break
                    qgisLeafId = 0
                    for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                        addOne = str(line).count(""""type": "Feature", "properties": { """)
                        if qgisLeafId < len(color_str):
                            line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": {
                                "id_qgis2leaf": """ +  str(qgisLeafId) + """, 
                                "color_qgis2leaf": \"""" + str(color_str[qgisLeafId]) + """\", 
                                "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                                "radius_qgis2leaf": """ +  str(radius_str[qgisLeafId]) + """,
                                "transp_qgis2leaf": """ + str(transp_str) + """, 
                                "transp_fill_qgis2leaf": """ +  str(transp_str2[qgisLeafId]) + """, 
                                """ )
                        else:
                            line = line.replace(" "," ")
                        sys.stdout.write(line)
                        qgisLeafId = qgisLeafId+addOne
                # Time for graduated polygons
                if i.rendererV2().dump()[0:9] == 'GRADUATED' and i.geometryType() == 2:
                    # every json entry needs a unique id:
                    iter = i.getFeatures()
                    #what is the value based on:
                    provider = i.dataProvider()
                    attrvalindex = provider.fieldNameIndex(i.rendererV2().classAttribute())	
                    transp_str = str(1 - ( float(i.layerTransparency()) / 100 ) )
                    color_str = []
                    radius_str = []
                    transp_str2 = []
                    for feat in iter:
                        if str(feat.attributes()[attrvalindex]) != 'NULL':
                            value = int(feat.attributes()[attrvalindex])
                        elif str(feat.attributes()[attrvalindex]) == 'NULL':
                            value = None
                        for r in i.rendererV2().ranges():
                            if value >= r.lowerValue() and value <= r.upperValue() and value != None:
                                color_str.append(str(r.symbol().color().name()))
                                transp_str2.append(str(r.symbol().alpha()))
                                break
                            elif value == None:
                                color_str.append('#FF00FF')
                                transp_str2.append('1')
                                break
                        qgisLeafId = 0
                        for line in fileinput.FileInput(dataFolder + os.sep + 'exp_' + re.sub('[\W_]+', '', i.name()) + '.js',inplace=1):
                            addOne = str(line).count(""""type": "Feature", "properties": { """)
                            if qgisLeafId < len(color_str):
                                line = line.replace(""""type": "Feature", "properties": { """,""""type": "Feature", "properties": { 
                                    "id_qgis2leaf": """ +  str(qgisLeafId) + """, 
                                    "color_qgis2leaf": \"""" + str(color_str[qgisLeafId]) + """\",
                                    "color": \"""" + str(color_str[qgisLeafId]) +"""\",
                                    "transp_qgis2leaf": """ + str(transp_str) + """, 
                                    "transp_fill_qgis2leaf": """ + str(transp_str2[qgisLeafId]) + """, 
                                            """ )
                            else:
                                line = line.replace(" "," ")
                            sys.stdout.write(line)
                            qgisLeafId = qgisLeafId+addOne		        
                # Add the js files as data input for the map.     
                print "Now do js files"
                script = """
                <script src='""" + '../data/' + """exp_""" + re.sub('[\W_]+', '', i.name()) + """.js' ></script>"""
                self.scripts.append(script)
                self.varNames.append("""exp_""" + re.sub('[\W_]+', '', i.name()))
            elif i.type() == 1:
                # This is for rasters
                print "Raster file"

            """
                 Credit goes to Tom Chadwin for the previous lines of code to create JSON strings
                            https://github.com/geolicious/qgis2leaf                                                                                  """
        # After for loop
        self.createHTMLPage()
        self.createJavascript()
        

    def createHTMLPage(self):
        currentPath = self.dlg.filePathWindow.toPlainText()
        htmlHead = """
<!DOCTYPE html>
<html>
<head>
	<title>QGIS2web dashboard</title>
	<meta charset="utf-8" />
		<link href="../css/maps.min.css" rel="stylesheet" /> 
		<link href="../css/main.css" rel="stylesheet" />
        <!-- Pure -->
		<link href="../lib/pure/pure-min.css" rel="stylesheet" />
		<!-- Pure Layout Side Menu -->
		<link href="../lib/pure-layout-side-menu/css/layouts/side-menu.css" rel="stylesheet" />
		<!-- Font Awesome -->
		<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.4.0/css/font-awesome.min.css">
		<!-- Leaflet -->
		<link href="../lib/leaflet/leaflet.css" rel="stylesheet" />
		<!-- Leaflet.fullscreen -->
		<link href="../lib/leaflet.fullscreen/dist/leaflet.fullscreen.css" rel="stylesheet" />
		<!-- Leaflet.cluster -->
		<link href="../lib/leaflet.cluster/dist/markercluster.css" rel="stylesheet" />
		<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
		<!-- Leaflet.Awesome-Markers -->
		<link href="../lib/leaflet.awesome-markers/dist/leaflet.awesome-markers.css" rel="stylesheet" />
		<!-- Leaflet.Loading -->
		<link href="../lib/leaflet.loading/src/Control.Loading.css" rel="stylesheet" />
		<!-- Leaflet Search -->
		<link href ="../lib/leaflet.search/src/leaflet-search.css" rel="stylesheet" />
</head>"""
        self.p.fileControl(currentPath,'maps','index.html','w',htmlHead)
        htmlBody = """
<body>
		<div id="layout">
			<!-- Menu toggle -->
			<a href="#menu" id="menuLink" class="menu-link"></a>
			<div id="menu">
				<div class="pure-menu pure-menu-open">
					<a class="pure-menu-heading" href="#">
						<img style="width:75%; height: 75%" src="../images/tweets.png"></img>
					</a>
					<ul>
						<li class="menu-item-divided pure-menu-selected"><a href="../maps"><b>Maps</b></a></li>
						<li class = "menu-item-divided pure-menu-unselected"><a href="../reports">Reports</a></li>
						<li class = "menu-item-divided pure-menu-unselected"><a href="../analytics">Analytics</a></li>						
					</ul>
				</div>
			</div>
			<!-- Maps container -->
			<div id="map-wrapper">
			<div id="map"></div>"""
        self.p.fileControl(currentPath, 'maps','index.html','a',htmlBody)
        self.p.fileControl(currentPath,'maps','index.html','a',self.scripts)
        bodyScripts = """
        		<!-- Leaflet -->
				<script src="../lib/leaflet/leaflet.js"></script>
                <!-- Map Js -->
                <script src="../js/map.js"></script>"""
        self.p.fileControl(currentPath,'maps','index.html','a',bodyScripts)
        pass
        
    def createJavascript(self):
        currentPath = self.dlg.filePathWindow.toPlainText()
        # Time to add libraries to html body
        initMap = """
var map
var basemap = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
var map = L.map('map').setView([51.505, -0.09], 13);
basemap.addTo(map);

function initMap(){
    var osmAttribution = "&copy; <a href='http://osm.org/copyright'>OpenStreetMap</a> contributors";

map = L.map("map", {
      fullscreenControl: true

    });

    osmLayer = L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
      attribution: osmAttribution
    }).addTo(map);

    osmGrayscaleLayer = L.tileLayer.grayscale("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
      attribution: osmAttribution
    });
    map.setView([55.95, -3.18], 13);

}

"""
        self.p.fileControl(currentPath, 'js', 'map.js','w', initMap)

        for j in self.varNames:
            func = """
function onEachFeature""" + j + """(feature, layer){
        if(feature.properties && feature.properties.html_exp){
            layer.bindPopup(feature.properties.html_exp);
            }
        else{
            layer.bindPopup("tweet")
            }
        }
var style""" + j + """={
    "color": \"""" + j + """.features.properties.color\",
    } 
L.geoJson(""" + j + """,{
    onEachFeature: onEachFeature""" + j + """,
    style: style""" + j + """
}).addTo(map);"""
            self.p.fileControl(currentPath, 'js','map.js','a',func)

        pass