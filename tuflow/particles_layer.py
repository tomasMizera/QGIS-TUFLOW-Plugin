# Slider zobrazuje najblizsi nizsi cas

from qgis.core import QgsVectorLayer, QgsProject, QgsField,\
    QgsFeature, QgsGeometry, QgsPoint
from PyQt5.QtCore import QVariant
import os
import glob


class TuflowParticlesLayer:

    def __init__(self, layerName, particlesParser):
        self.layer = QgsVectorLayer("PointZ", layerName, "memory")
        self.particlesParser = particlesParser
        # catch delete signal on layer
        # self.layer.willBeDeleted.connect(self.destroyLayer)
        self.currentTime = 0
        self.__build_attributes()
        self.__add_styles()
        self.__show()

    def destroyLayer(self):
        if self.layer is not None:
            QgsProject.instance().removeMapLayer(self.layer)
            self.layer = None

    def loadNext(self):
        self.currentTime += 1
        self.__populate_particles(self.currentTime)

    def __build_attributes(self):
        attrs = []

        # add mandatory attributes
        attrs.extend([
            QgsField("id", QVariant.Int),
            QgsField("stat", QVariant.Int),
            QgsField("groupID", QVariant.Int)
        ])

        # add optional attributes (variables) that are in file
        dataset_vars = self.particlesParser.get_all_variable_names()
        for var in dataset_vars:
            attrs.append(QgsField(var, QVariant.Double))

        self.layer.dataProvider().addAttributes(attrs)
        self.layer.updateFields()

    def __add_styles(self):
        styles_dir = os.path.dirname(os.path.realpath(__file__))
        styles_folder = os.path.join(styles_dir, "QGIS_Styles/particles_qml/")
        styles = glob.glob(styles_folder + '*.qml', recursive=True)
        style_manager = self.layer.styleManager()
        for style in styles:
            style_name = os.path.basename(style).strip('.qml')
            (_, success) = self.layer.loadNamedStyle(style)
            if not success:
                style_manager.removeStyle(style)

            style_manager.addStyleFromLayer(style_name)

        style_manager.setCurrentStyle("default")

    def __show(self):
        if self.layer:
            QgsProject.instance().addMapLayer(self.layer)

    def __populate_particles(self, at_time):
        if self.layer is not None:
            data = self.particlesParser.read_data_at_time(at_time)
            if data is None:
                return
            x = data.pop('x')
            y = data.pop('y')
            z = data.pop('z')
            stats = data.get('stat')

            points = []
            for i, stat in enumerate(stats):
                # ignore inactive particles
                if int(stat) > 0:
                    feat = QgsFeature()
                    point = QgsPoint(x[i], y[i], z[i])
                    feat.setGeometry(QgsGeometry(point))
                    feat.setFields(self.layer.fields())
                    for attr in data.keys():
                        feat['id'] = i
                        # must be converted to primitive type, otherwise feature data wont be stored
                        feat[attr] = float(data.get(attr)[i])
                    points.append(feat)

            # add to layer
            self.layer.dataProvider().truncate()
            self.layer.dataProvider().addFeatures(points)
            self.layer.updateExtents()
            self.layer.triggerRepaint()
