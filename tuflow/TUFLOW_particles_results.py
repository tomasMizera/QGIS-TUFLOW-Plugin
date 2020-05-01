# to co mame my v prototype

from tuflow.particles_layer import TuflowParticlesLayer
from PyQt5.QtWidgets import QAction, QFileDialog
from PyQt5.QtCore import QVariant, QSettings, Qt
# from PyQt5.QtGui import QIcon
from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog, QgsFeature,\
    QgsPoint, QgsPointXY, QgsGeometry, QgsField, QgsMessageLog
# from .particlesParser import ParticlesParser
import os
# from .timeSliderDockWidget import TimeSliderDockWidget
from tuflow.netcdf_particles_parser import NetCDFParticlesParser

class TuflowParticles:
    def __init__(self, tuview):
        self.tuview = tuview
        self.tuview.scatteredFileLoaded.connect(self.handleFileLoad)
        # self.vlayer = TuflowParticlesLayer()
        # self.iface = iface
        # self.time_slider = TimeSliderDockWidget(None)
        self.particlesParser = None
        # self.vlayer = None
        # self.action = None
        # self.filename = None

        # self.time_slider.hide()

        # dir_path = os.path.dirname(os.path.realpath(__file__))
        # self.icon = QIcon(os.path.join(dir_path, "logo.png"))
        # self.style_file = os.path.join(dir_path, "layer_style.qml")

        # self.time_slider.changedCurrentTime.connect(self.populate_particles)

    def openFileIfValid(self, filename):
        if self.particlesParser is None:
            self.particlesParser = NetCDFParticlesParser()

        try:
            self.particlesParser.load_file(filename)
        except:
            return False

        if not self.particlesParser.is_valid_file():
            return False

        return True

    def handleFileLoad(self, filename):
        if not self.openFileIfValid(filename):
            # inform user that the loaded file is incorrect
            # reset particles parser
            self.unload()
            return

        self.buildLayer()

    def unload(self):
        self.particlesParser = None
        self.filename = None
        if self.vlayer:
            QgsProject.instance().removeMapLayer(self.vlayer)
            self.vlayer = None

    def buildLayer(self):
        self.vlayer = TuflowParticlesLayer()
        self.vlayer.willBeDeleted.connect(self.unload)


# class TuflowPlugin:
#     def __init__(selfiface):
#         pass

        # self.iface.removeDockWidget(self.time_slider)
        # self.time_slider = None
        # if self.action:
        #     self.iface.removeToolBarIcon(self.action)
        #     self.action = None
    #
    # def load_file(self):
    #     s = QSettings()
    #     last_input_folder = s.value("TUFLOWParticles/last_input_folder", os.path.expanduser("~"), type=str)
    #     fileName = QFileDialog.getOpenFileName(self.iface.mainWindow(), "Open TUFLOW Particles", last_input_folder, "TUFLOW Particle File (*.nc)")
    #     if fileName:
    #         self.filename = fileName[0]
    #         s.setValue("TUFLOWParticles/last_input_folder", os.path.dirname(fileName[0]))
    #         self.process_file()
    #
    # def process_file(self):
    #     self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.time_slider)
    #
    #     if self.particles_parser is None:
    #         self.particles_parser = ParticlesParser()
    #
    #     self.particles_parser.load_file(self.filename)
    #     if self.particles_parser.is_valid_file():
    #         self.build_layer()
    #         self.time_slider.reset(self.particles_parser.get_all_timedate_texts())
    #         self.time_slider.show()
    #     else:
    #         QgsMessageLog.logMessage("Unable to load file " + self.filename)
    #         self.filename = None
    #         self.time_slider.reset()
    #         self.time_slider.hide()
    #
    # def build_layer(self):
    #     if self.vlayer is None:
    #         self.vlayer = QgsVectorLayer("PointZ", "TUFLOW Particles", "memory")
    #         self.vlayer.dataProvider().addAttributes(self.get_attributes_list())
    #         self.vlayer.updateFields()
    #         self.vlayer.loadNamedStyle(self.style_file)
    #         QgsProject.instance().addMapLayer(self.vlayer)
    #         self.iface.setActiveLayer(self.vlayer)
    #         self.vlayer.willBeDeleted.connect(self.handle_layer_deleted)
    #
    # def handle_layer_deleted(self):
    #     self.vlayer = None
    #     self.particles_parser = None
    #     self.time_slider.hide()
    #     self.time_slider.reset()
    #
    # def populate_particles(self, at_time):
    #     if self.vlayer is not None:
    #         data = self.particles_parser.read_data_at_time(at_time)
    #         if data is None:
    #             return
    #         x = data.pop('x')
    #         y = data.pop('y')
    #         z = data.pop('z')
    #         groupID = data.pop('groupID')
    #         stats = data.get('stat')
    #
    #         points = []
    #         for i, stat in enumerate(stats):
    #             # ignore inactive particles
    #             if int(stat) > 0:
    #                 feat = QgsFeature()
    #                 point = QgsPoint(x[i], y[i], z[i])
    #                 feat.setGeometry(QgsGeometry(point))
    #                 feat.setFields(self.vlayer.fields())
    #                 for attr in data.keys():
    #                     feat['id'] = i
    #                     feat['groupID'] = int(groupID)
    #                     feat[attr] = float(data.get(attr)[i])  # must be converted to primitive type, otherwise feature data wont be stored
    #                 points.append(feat)
    #
    #         # add to layer
    #         self.vlayer.dataProvider().truncate()
    #         self.vlayer.dataProvider().addFeatures(points)
    #         self.vlayer.updateExtents()
    #         self.vlayer.triggerRepaint()
    #
    # def get_attributes_list(self):
    #     attrs = []
    #
    #     # add mandatory attributes
    #     attrs.extend([
    #         QgsField("id", QVariant.Int),
    #         QgsField("stat", QVariant.Int),
    #         QgsField("groupID", QVariant.Int)
    #     ])
    #
    #     # add optional attributes (variables) that are in file
    #     dataset_vars = self.particles_parser.get_all_variable_names()
    #     for var in dataset_vars:
    #         attrs.append(QgsField(var, QVariant.Double))
    #
    #     return attrs