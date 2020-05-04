# to co mame my v prototype

from tuflow.particles_layer import TuflowParticlesLayer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QVariant, QSettings, Qt
# from PyQt5.QtGui import QIcon
from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog, QgsFeature,\
    QgsPoint, QgsPointXY, QgsGeometry, QgsField, QgsMessageLog
# from .particlesParser import ParticlesParser
import os
# from .timeSliderDockWidget import TimeSliderDockWidget
from tuflow.netcdf_particles_parser import NetCDFParticlesParser


"""
This class handles integration part, timeslider, particlesparser, data population, opening file.
"""


class TuflowParticles:
    def __init__(self, tuview):
        self.tuview = tuview
        self.tuview.scatteredFileLoaded.connect(self.handleFileLoad)
        self.tuview.cboTime.currentIndexChanged.connect(self.timeChanged)
        # self.vlayer = TuflowParticlesLayer()
        # self.iface = iface
        # self.time_slider = TimeSliderDockWidget(None)
        self.particlesParser = None

        # layer handler
        self.lh = None

        # self.action = None
        # self.filename = None

        # self.time_slider.hide()

        # dir_path = os.path.dirname(os.path.realpath(__file__))
        # self.icon = QIcon(os.path.join(dir_path, "logo.png"))
        # self.style_file = os.path.join(dir_path, "layer_style.qml")

        # self.time_slider.changedCurrentTime.connect(self.populate_particles)

    def unload(self):
        self.particlesParser = None
        self.filename = None
        if self.lh:
            self.lh.destroyLayer()
            self.lh = None

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
            QMessageBox.information(self.iface.mainWindow(), "Info", "Requested file is not valid.")
            # reset particles parser
            self.unload()
            return

        self.buildLayerHandler()

    def buildLayerHandler(self):
        if self.lh is None:
            self.lh = TuflowParticlesLayer("TUFLOW Particles", self.particlesParser)
            self.lh.layer.willBeDeleted.connect(self.unload)

        self.lh.loadNext()

    def timeChanged(self, value):
        print(value)
