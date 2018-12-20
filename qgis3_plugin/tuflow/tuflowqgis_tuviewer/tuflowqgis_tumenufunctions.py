import os
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
from qgis.core import *
from PyQt5.QtWidgets import *
from qgis.PyQt.QtXml import QDomDocument
from matplotlib.patches import Polygon
from tuflow.tuflowqgis_library import loadLastFolder, getResultPathsFromTCF, getScenariosFromTcf, getEventsFromTCF, tuflowqgis_find_layer, getUnit, getCellSizeFromTCF
from tuflow.tuflowqgis_dialog import tuflowqgis_scenarioSelection_dialog, tuflowqgis_eventSelection_dialog, TuOptionsDialog, TuSelectedElementsDialog, tuflowqgis_meshSelection_dialog, TuBatchPlotExportDialog, TuUserPlotDataManagerDialog
from tuflow.tuflowqgis_tuviewer.tuflowqgis_tuanimation import TuAnimationDialog


class TuMenuFunctions():
	"""
	Generic class for handling menu functions.
	
	"""
	
	def __init__(self, TuView):
		self.tuView = TuView
		self.iface = TuView.iface
	
	def load2dResults(self, **kwargs):
		"""
		Loads 2D results into map window and plotting ui

		:return: bool -> True for successful, False for unsuccessful
		"""

		result2D = kwargs['result_2D'] if 'result_2D' in kwargs.keys() else None  # list of xmdfs or dats
		
		if not result2D:
			# Get last loaded settings
			fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_2DResults/lastFolder")
			
			# User get 2D result file
			inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW 2D results file',
			                                           fpath,
			                                           "TUFLOW 2D Results (*.dat *.xmdf)")
			if not inFileNames[0]:  # empty list
				return False
			
		else:
			inFileNames = result2D
			
		# import into qgis
		loaded = self.tuView.tuResults.importResults('mesh', inFileNames[0])
		
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_2DResults/lastFolder", fpath)
		
		if not loaded:
			return False
		
		return True
	
	def load1dResults(self, **kwargs):
		"""
		Loads 1D results into ui and prompts user to load GIS files.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		result1D = kwargs['result_1D'] if 'result_1D' in kwargs.keys() else None
		unlock = kwargs['unlock'] if 'unlock' in kwargs else True
		
		if not result1D:
			# Get last loaded settings
			fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_1DResults/lastFolder")
			
			# User get 1D result file
			inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW 1D results file',
			                                           fpath,
			                                           "TUFLOW 1D Results (*.tpc *.info)")
			if not inFileNames[0]:  # empty list
				return False
			
		else:
			inFileNames = result1D
		
		# Prompt user if they want to load in GIS files
		for inFileName in inFileNames[0]:
			if os.path.splitext(inFileName)[1].lower() == '.tpc':
				alsoOpenGis = QMessageBox.question(self.iface.mainWindow(),
				                                   "Tuviewer", 'Do you also want to open result GIS layer?',
				                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
			else:
				alsoOpenGis = QMessageBox.No
		if alsoOpenGis == QMessageBox.Yes:
			self.tuView.tuResults.tuResults1D.openGis(inFileNames[0][0])
		elif alsoOpenGis == QMessageBox.Cancel:
			return False
		
		# import results
		self.tuView.tuResults.importResults('timeseries', inFileNames[0])
		
		# unlock map output timesteps only
		if unlock:
			if self.tuView.lock2DTimesteps:
				self.tuView.timestepLockChanged()
		
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_1DResults/lastFolder", fpath)
		
		return True
	
	def load1d2dResults(self):
		"""
		Loads 1D and 2D reuslts from TCF file.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		# Get last loaded settings
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/lastFolder")
		
		# User get TCF file
		inFileNames = QFileDialog.getOpenFileNames(self.iface.mainWindow(), 'Open TUFLOW results file',
		                                           fpath,
		                                           "TUFLOW Control File (*.tcf)")
		
		if not inFileNames[0]:  # empty list
			return False
		
		# get 1D and 2D results from TCF
		results1D, results2D = [], []
		for file in inFileNames[0]:
			
			# get scenarios from TCF and prompt user to select desired scenarios
			error, message, scenarios = getScenariosFromTcf(file)
			if scenarios:
				self.scenarioDialog = tuflowqgis_scenarioSelection_dialog(self.iface, file, scenarios)
				self.scenarioDialog.exec_()
				if self.scenarioDialog.scenarios is None:
					return False
				else:
					scenarios = self.scenarioDialog.scenarios
					
			# get events from TCF and prompt user to select desired events
			events = getEventsFromTCF(file)
			if events:
				self.eventDialog = tuflowqgis_eventSelection_dialog(self.iface, file, events)
				self.eventDialog.exec_()
				if self.eventDialog.events is None:
					return False
				else:
					events = self.eventDialog.events

			res1D, res2D = getResultPathsFromTCF(file, scenarios=scenarios, events=events)
			
			# since going through tcf, may as well grab cell size and use for cross section and flux line resolution
			if scenarios:
				# if there are scenarios, there may be a variable set for cell size
				cellSize = 99999
				for i, scenario in enumerate(scenarios):
					size = getCellSizeFromTCF(file, scenario=scenario)
					if size is not None:
						cellSize = min(cellSize, size)
			else:
				cellSize = getCellSizeFromTCF(file)
			if cellSize is not None and cellSize != 99999:
				self.tuView.tuOptions.resolution = cellSize / 2.0
			
			if res1D:
				if results1D:
					results1D[0] += res1D
				else:
					results1D.append(res1D)
			if res2D:
				if results2D:
					results2D[0] += res2D
				else:
					results2D.append(res2D)

		# load 2D results
		if results2D:
			self.load2dResults(result_2D=results2D)
		
		# load 1D results
		if results1D:
			self.load1dResults(result_1D=results1D, unlock=False)
			
		# finally save the last folder location
		fpath = os.path.dirname(inFileNames[0][0])
		settings = QSettings()
		settings.setValue("TUFLOW_Results/lastFolder", fpath)
		
		return True
	
	def remove1d2dResults(self):
		"""
		Removes the selected results from the ui.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		results = []
		for item in self.tuView.OpenResults.selectedItems():
			results.append(item.text())

		self.tuView.tuResults.removeResults(results)
		for result in results:
			layer = tuflowqgis_find_layer(result)
			self.tuView.project.removeMapLayer(layer)
		
		self.tuView.canvas.refresh()
		self.tuView.resultsChanged()
		
		return True
	
	def remove2dResults(self):
		"""
		Removes the selected results from the ui - 2D results only
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		results = []
		for item in self.tuView.OpenResults.selectedItems():
			layer = tuflowqgis_find_layer(item.text())
			self.tuView.project.removeMapLayer(layer)  # this will trigger the removal from results index
			
		self.tuView.canvas.refresh()
		self.tuView.resultsChanged()
		
		return True
	
	def remove1dResults(self):
		"""
		Removes the selected results from the ui - 1D results only
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		results = []
		for item in self.tuView.OpenResults.selectedItems():
			results.append(item.text())
		
		self.tuView.tuResults.tuResults1D.removeResults(results)
		
		self.tuView.resultsChanged()
		
		return True
	
	def updateMapPlotWindows(self):
		"""
		Update map window and all plot windows

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.renderMap()
		
		self.tuView.tuPlot.updateCurrentPlot(self.tuView.tabWidget.currentIndex())
		
		return True
	
	def options(self):
		"""
		Open options dialog
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		xAxisDatesPrev = self.tuView.tuOptions.xAxisDates
		self.tuOptionsDialog = TuOptionsDialog(self.tuView.tuOptions)
		self.tuOptionsDialog.exec_()
		self.tuView.tuPlot.updateCurrentPlot(self.tuView.tabWidget.currentIndex(), update='1d and 2d only')
		if self.tuView.tuMenuBar.showMedianEvent_action.isChecked() or self.tuView.tuMenuBar.showMeanEvent_action.isChecked():
			self.tuView.renderMap()
		if self.tuView.tuOptions.xAxisDates != xAxisDatesPrev:
			self.tuView.tuResults.updateResultTypes()
		
		return True
	
	def exportCSV(self):
		"""
		Export the data as a CSV.
		
		:return: bool -> True for successful, False for unsuccessful
		"""

		plotNo = self.tuView.tabWidget.currentIndex()
		
		dataHeader, data = self.getPlotData(plotNo)
		
		if dataHeader is None or data is None:
			QMessageBox.critical(self.iface.mainWindow(), 'TuView', 'Error exporting file')
			return False
		
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_csv")
		
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_csv", saveFile)
			if not os.path.splitext(saveFile)[-1]:  # no extension specified - default to csv
				saveFile = '{0}.csv'.format(saveFile)
		
		if saveFile is not None:
			retry = True
			while retry:
				try:
					file = open(saveFile, 'w')
					file.write('{0}\n'.format(dataHeader))
					for i, row in enumerate(data):
						line = ''
						for j, value in enumerate(row):
							if not np.isnan(data[i][j]):
								line += '{0},'.format(data[i][j])
							else:
								line += '{0},'.format('')
						line += '\n'
						file.write(line)
					file.close()
					QMessageBox.information(self.iface.mainWindow(), 'TuView', 'Successfully exported data.')
					retry = False
				except IOError:
					questionRetry = QMessageBox.question(self.iface.mainWindow(),
						                                 "Tuviewer", 'Could not access {0}. Check file is not open.'.format(saveFile),
						                                 QMessageBox.Retry | QMessageBox.Cancel)
					if questionRetry == QMessageBox.Cancel:
						retry = False
						return False
						
				except:
					QMessageBox.critical(self.iface.mainWindow(), 'TuView', 'Error exporting file')
					retry = False
					return False
		
		return True
		
	def getPlotData(self, plotNo):
		"""
		Collects all the plot data into one numpy array.
		
		:return: str Headers, numpy array data
		"""
		
		parentLayout, figure, subplot, plotWidget, isSecondaryAxis, artists, labels, unit, yAxisLabelTypes, yAxisLabels, xAxisLabels, xAxisLimits, yAxisLimits = \
			self.tuView.tuPlot.plotEnumerator(plotNo)
		
		# get lines and labels for both axis 1 and axis 2
		lines, labels = subplot.get_legend_handles_labels()
		lines2, labels2 = [], []
		if isSecondaryAxis[0]:
			subplot2 = self.tuView.tuPlot.getSecondaryAxis(plotNo)
			lines2, labels2 = subplot2.get_legend_handles_labels()
		
		# get maximum data length so we can adjust all lengths to be the same (easier to export that way)
		maxLen = 0
		for line in lines:
			if type(line) == Polygon:
				maxLen = max(maxLen, len(line.get_xy()))
			else:
				maxLen = max(maxLen, len(line.get_data()[0]))
		for line in lines2:
			if type(line) == Polygon:
				maxLen = max(maxLen, len(line.get_xy()))
			else:
				maxLen = max(maxLen, len(line.get_data()[0]))
			
		# put all data into one big numpy array and adjust data accordingly to max length - axis 1
		data = None
		for i, line in enumerate(lines):
			if i ==0:
				data = np.zeros((maxLen, 1))  # set up data array.. start with zeros and delete first column once populated
			if type(line) == Polygon:
				xy = line.get_xy()
				x = xy[:,0]
				y = xy[:,1]
			else:
				x, y = line.get_data()
			if type(x) is list:  # if not a numpy array, convert it to one
				x = np.array(x)
			if type(y) is list:  # if not a numpy array, convert it to one
				y = np.array(y)
			dataX = np.reshape(x, (len(x), 1))  # change the shape so it has 2 axis
			dataY = np.reshape(y, (len(y), 1))  # change the shape so it has 2 axis
			if len(dataX) < maxLen:
				diff = maxLen - len(dataX)
				fill = np.zeros([diff, 1]) * np.nan
				dataX = np.append(dataX, fill, axis=0)
			if len(dataY) < maxLen:
				diff = maxLen - len(dataY)
				fill = np.zeros([diff, 1]) * np.nan
				dataY = np.append(dataY, fill, axis=0)
			data = np.append(data, dataX, axis=1)
			data = np.append(data, dataY, axis=1)
			if i == 0:
				data = np.delete(data, 0, 1)  # delete initialised row of zeros
				
		# put all data into one big numpy array and adjust data accordingly to max length - axis 2
		needToDeleteFirstColumn = False
		for i, line in enumerate(lines2):
			if i == 0:
				if data is None:
					data = np.zeros((maxLen, 1))  # set up data array
					needToDeleteFirstColumn = True
			if type(line) == Polygon:
				xy = line.get_xy()
				x = xy[:,0]
				y = xy[:,1]
			else:
				x, y = line.get_data()
			if type(x) is list:  # if not a numpy array, convert it to one
				x = np.array(x)
			if type(y) is list:  # if not a numpy array, convert it to one
				y = np.array(y)
			dataX = np.reshape(x, (len(x), 1))  # change the shape so it has 2 axis
			dataY = np.reshape(y, (len(y), 1))  # change the shape so it has 2 axis
			if len(dataX) < maxLen:
				diff = maxLen - len(dataX)
				fill = np.zeros([diff, 1]) * np.nan
				dataX = np.append(dataX, fill, axis=0)
			if len(dataY) < maxLen:
				diff = maxLen - len(dataY)
				fill = np.zeros([diff, 1]) * np.nan
				dataY = np.append(dataY, fill, axis=0)
			data = np.append(data, dataX, axis=1)
			data = np.append(data, dataY, axis=1)
			if i == 0:
				if needToDeleteFirstColumn:
					data = np.delete(data, 0, 1)  # delete initialised row of zeros
			
		if plotNo == 0:
			dataHeader = self.getTimeSeriesPlotHeaders(labels, labels2)
		elif plotNo == 1:
			dataHeader = self.getLongPlotHeaders(labels, labels2)
		else:
			dataHeader = ''
			
		return dataHeader, data
	
	def getTimeSeriesPlotHeaders(self, labels, labels2):
		"""
		Returns column headings in comma delimiter format for time series export to csv.
		
		:param labels: list -> str label axis 1
		:param labels2: list -> str label axis 2
		:return: str column headers
		"""
		
		# get labels into one big comma delimiter string
		dataHeader = None
		for i, label in enumerate(labels):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				dataHeader = 'Time (hr)'
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Time (hr)'.format(dataHeader)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		for i, label in enumerate(labels2):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				if not labels:
					dataHeader = 'Time (hr)'
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				else:
					dataHeader = '{0},Time (hr)'.format(dataHeader)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Time (hr)'.format(dataHeader)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				
		return dataHeader
	
	def getLongPlotHeaders(self, labels, labels2):
		"""
		Return column headings in comma delimiter format for long plot export to csv.
		
		:param labels: list -> str label axis 1
		:param labels2: list -> str label axis 2
		:return: str column headers
		"""
		
		# get labels into one big comma delimiter string
		dataHeader = None
		xAxisUnit = getUnit(None, self.tuView.canvas, return_map_units=True)
		for i, label in enumerate(labels):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				dataHeader = 'Offset ({0})'.format(xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		for i, label in enumerate(labels2):
			labelUnit = getUnit(label, self.tuView.canvas)
			if i == 0:
				if not labels:
					dataHeader = 'Offset ({0})'.format(xAxisUnit)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
				else:
					dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
					dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
			else:
				dataHeader = '{0},Offset ({1})'.format(dataHeader, xAxisUnit)
				dataHeader = '{0},{1} ({2})'.format(dataHeader, label, labelUnit) if labelUnit else '{0},{1}'.format(dataHeader, label)
		
		return dataHeader
	
	def freezeAxisLimits(self, enum):
		"""
		Toggles Freeze Axis Y and X limits for both the menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisLimits_action.isChecked():
				# menu bar
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
				# context menu
				self.tuView.tuContextMenu.freezeAxisLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				# menu bar
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
				# context menu
				self.tuView.tuContextMenu.freezeAxisLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisLimits_action.isChecked():
				# menu bar
				self.tuView.tuMenuBar.freezeAxisLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
				# context menu
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				# menu bar
				self.tuView.tuMenuBar.freezeAxisLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
				# context menu
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		else:
			return False
			
		return True
	
	def freezeAxisXLimits(self, enum):
		"""
		Toggles Freeze X axis limits for menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisXLimits_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(True)
				self.tuView.tuPlot.tuPlotToolbar.freezeXAxisButton.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisXLimits_action.setChecked(False)
				self.tuView.tuPlot.tuPlotToolbar.freezeXAxisButton.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisXLimits_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisXLimits_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeAxisYLimits(self, enum):
		"""
		Toggles Freeze Y axis limits for menu bar and context menu.

		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisYLimits_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisYLimits_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisYLimits_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisYLimits_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeAxisLabels(self, enum):
		"""
		Toggles Freeze Axis Labels for menu bar and context menu
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeAxisLabels_action.isChecked():
				self.tuView.tuContextMenu.freezeAxisLabels_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeAxisLabels_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeAxisLabels_action.isChecked():
				self.tuView.tuMenuBar.freezeAxisLabels_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeAxisLabels_action.setChecked(False)
		else:
			return False
		
		return True
	
	def freezeLegendLabels(self, enum):
		"""
		Toggles Freeze Legend Labels for menu bar and context menu.
		
		:param enum: int -> 0: menu bar
							1: context menu
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		if enum == 0:
			if self.tuView.tuMenuBar.freezeLegendLabels_action.isChecked():
				self.tuView.tuContextMenu.freezeLegendLabels_action.setChecked(True)
			else:
				self.tuView.tuContextMenu.freezeLegendLabels_action.setChecked(False)
		elif enum == 1:
			if self.tuView.tuContextMenu.freezeLegendLabels_action.isChecked():
				self.tuView.tuMenuBar.freezeLegendLabels_action.setChecked(True)
			else:
				self.tuView.tuMenuBar.freezeLegendLabels_action.setChecked(False)
		else:
			return False
		
		self.tuView.tuPlot.setNewPlotProperties(enum)
		
		return True
		
	def exportTempLines(self):
		"""
		Export rubberband lines as shape file
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# User defined save path
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_shp")
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save Shape File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_shp", saveFile)
			if not os.path.splitext(saveFile)[-1] or os.path.splitext(saveFile)[-1].lower() != '.shp':
				saveFile = '{0}.shp'.format(saveFile)

		# create shape file
		crs = self.tuView.project.crs()
		crsId = crs.authid()
		uri = 'linestring?crs={0}'.format(crsId)
		shpLayer = QgsVectorLayer(uri, os.path.splitext(os.path.basename(saveFile))[0], 'memory')
		dp = shpLayer.dataProvider()
		dp.addAttributes([QgsField('Name', QVariant.String)])
		shpLayer.updateFields()
		feats = []  # list of QgsFeature objects
		for i, rubberBand in enumerate(self.tuView.tuPlot.tuRubberBand.rubberBands):
			geom = rubberBand.asGeometry().asPolyline()
			feat = QgsFeature()
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
			feat.setAttributes(['Line {0}'.format(i+1)])
			feats.append(feat)
		for i, line in enumerate(self.tuView.tuPlot.tuFlowLine.rubberBands):
			geom = line.asGeometry().asPolyline()
			feat = QgsFeature()
			feat.setGeometry(QgsGeometry.fromPolyline([QgsPoint(x) for x in geom]))
			feat.setAttributes(['Flow Location {0}'.format(i + 1)])
			feats.append(feat)
		error = dp.addFeatures(feats)
		shpLayer.updateExtents()
		QgsVectorFileWriter.writeAsVectorFormat(shpLayer, saveFile, 'CP1250', crs, 'ESRI Shapefile')
		
		# ask user if import or not
		importLayer = QMessageBox.question(self.iface.mainWindow(),
		                                   "Tuviewer", 'Successfully saved {0}. Open in workspace?'.format(os.path.basename(saveFile)),
		                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
		if importLayer == QMessageBox.Yes:
			self.iface.addVectorLayer(saveFile, os.path.splitext(os.path.basename(saveFile))[0], 'ogr')
			
		return True
	
	def exportTempPoints(self):
		"""
		Export marker points as shape file
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		# User defined save path
		fpath = loadLastFolder(self.tuView.currentLayer, "TUFLOW_Results/export_shp")
		saveFile = QFileDialog.getSaveFileName(self.iface.mainWindow(), 'Save Shape File', fpath)[0]
		if len(saveFile) < 2:
			return
		else:
			if saveFile != os.sep and saveFile.lower() != 'c:\\' and saveFile != '':
				QSettings().setValue("TUFLOW_Results/export_shp", saveFile)
			if not os.path.splitext(saveFile)[-1] or os.path.splitext(saveFile)[-1].lower() != '.shp':
				saveFile = '{0}.shp'.format(saveFile)
		
		# create shape file
		crs = self.tuView.project.crs()
		crsId = crs.authid()
		uri = 'point?crs={0}'.format(crsId)
		shpLayer = QgsVectorLayer(uri, os.path.splitext(os.path.basename(saveFile))[0], 'memory')
		dp = shpLayer.dataProvider()
		dp.addAttributes([QgsField('Name', QVariant.String)])
		shpLayer.updateFields()
		feats = []  # list of QgsFeature objects
		for i, point in enumerate(self.tuView.tuPlot.tuRubberBand.markerPoints):
			feat = QgsFeature()
			feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(point)))
			feat.setAttributes(['Point {0}'.format(i + 1)])
			feats.append(feat)
		error = dp.addFeatures(feats)
		shpLayer.updateExtents()
		QgsVectorFileWriter.writeAsVectorFormat(shpLayer, saveFile, 'CP1250', crs, 'ESRI Shapefile')
		
		# ask user if import or not
		importLayer = QMessageBox.question(self.iface.mainWindow(),
		                                   "Tuviewer", 'Successfully saved {0}. Open in workspace?'.format(
				os.path.basename(saveFile)),
		                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
		if importLayer == QMessageBox.Yes:
			self.iface.addVectorLayer(saveFile, os.path.splitext(os.path.basename(saveFile))[0], 'ogr')
		
		return True
	
	def updateLegend(self):
		"""
		Updates the legend on the figure.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuPlot.updateLegend(self.tuView.tabWidget.currentIndex())
		self.tuView.tuPlot.setNewPlotProperties(self.tuView.tabWidget.currentIndex())
		
		return True
	
	def showMeanEvent(self):
		"""
		Shows the mean event from all displayed lines. The mean event is either chosen from the closest or next above.

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuPlot.showStatResult(self.tuView.tabWidget.currentIndex(), 'Mean')
		
		return True
	
	def showMedianEvent(self):
		"""
		Shows the median event from all displayed lines. If even number, will show the n + 1 event

		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuPlot.showStatResult(self.tuView.tabWidget.currentIndex(), 'Median')
		
		return True
	
	def showSelectedElements(self):
		"""
		Displays a dialog of all the selected elements in the results.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		elements = self.tuView.tuResults.tuResults1D.ids
		
		self.selectedElementsDialog = TuSelectedElementsDialog(self.iface, elements)
		self.selectedElementsDialog.show()
		
		return True
	
	def toggleResultTypeToMax(self):
		"""
		Toggles the result type to max or temporal through context menu.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuContextMenu.resultTypeContextItem.toggleMaxActive()
		
		self.tuView.maxResultTypesChanged(None)
		
		return True
	
	def toggleResultTypeToSecondaryAxis(self):
		"""
		Toggles the result type to primary or secondary axis through context menu.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.tuView.tuContextMenu.resultTypeContextItem.toggleSecondaryActive()
		
		self.tuView.secondaryAxisResultTypesChanged(None)
		
		return True
		
	def saveDefaultStyleScalar(self, saveType, **kwargs):
		"""
		Saves the current active result type style as default for future similar result types.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no mesh layer or more than one active mesh layer
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Result Datasets')
			return False
		elif len(self.tuView.tuResults.tuResults2D.activeMeshLayers) > 1:
			self.meshDialog = tuflowqgis_meshSelection_dialog(self.iface, self.tuView.tuResults.tuResults2D.activeMeshLayers)
			self.meshDialog.exec_()
			if self.meshDialog.selectedMesh is None:
				return False
			else:
				meshLayer = tuflowqgis_find_layer(self.meshDialog.selectedMesh)
		else:
			meshLayer = self.tuView.tuResults.tuResults2D.activeMeshLayers[0]

		# get data provider and renderer settings
		dp = meshLayer.dataProvider()
		rs = meshLayer.rendererSettings()
		
		# get scalar renderer settings
		if useClicked:
			resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
			for i in range(dp.datasetGroupCount()):
				if dp.datasetGroupMetadata(i).name() == resultType or dp.datasetGroupMetadata(i).name() == '{0}/Maximums'.format(resultType):
					activeScalarGroupIndex = i
					break
		else:
			activeScalar = rs.activeScalarDataset()
			activeScalarGroupIndex = activeScalar.group()
			if activeScalarGroupIndex == -1:
				QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Scalar Dataset')
				return False
		activeScalarType = dp.datasetGroupMetadata(activeScalarGroupIndex).name()
		activeScalarType = activeScalarType.strip('/Maximums')
		rsScalar = rs.scalarSettings(activeScalarGroupIndex)
		
		# save color ramp if option chosen
		if saveType == 'color ramp':
			## get color ramp properties
			shader = rsScalar.colorRampShader()
			file = os.path.join(os.path.dirname(__file__), '_saved_styles', '{0}.xml'.format(activeScalarType))
			doc = QDomDocument(activeScalarType.replace(' ', '_'))
			element = shader.writeXml(doc)
			doc.appendChild(element)
			fo = open(file, 'w')
			fo.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			fo.write(doc.toString())
			fo.close()
			
			# save as default for that result type
			key = "TUFLOW_scalarRenderer/{0}_ramp".format(activeScalarType)
			settings = QSettings()
			settings.setValue(key, file)
			
			# remove color map key
			key = "TUFLOW_scalarRenderer/{0}_map".format(activeScalarType)
			settings = QSettings()
			settings.remove(key)
		
		# save color map if option chosen
		elif saveType == 'color map':
			file = os.path.join(os.path.dirname(__file__), '_saved_styles', '{0}.xml'.format(activeScalarType))
			doc = QDomDocument(activeScalarType.replace(' ', '_'))
			element = rsScalar.writeXml(doc)
			doc.appendChild(element)
			fo = open(file, 'w')
			fo.write('<?xml version="1.0" encoding="UTF-8"?>\n')
			fo.write(doc.toString())
			fo.close()
			
			# save setting so tuview knows to load it in
			key = "TUFLOW_scalarRenderer/{0}_map".format(activeScalarType)
			settings = QSettings()
			settings.setValue(key, file)
			
			# remove color ramp key
			key = "TUFLOW_scalarRenderer/{0}_ramp".format(activeScalarType)
			settings = QSettings()
			settings.remove(key)
		
		QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'Saved default style for {0}'.format(activeScalarType))
		
		return True
			
	def saveDefaultStyleVector(self, **kwargs):
		"""
		Save the current active vector renderer settings as default for future vector types.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no mesh layer or more than one active mesh layer
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Result Datasets')
			return False
		elif len(self.tuView.tuResults.tuResults2D.activeMeshLayers) > 1:
			self.meshDialog = tuflowqgis_meshSelection_dialog(self.iface, self.tuView.tuResults.tuResults2D.activeMeshLayers)
			self.meshDialog.exec_()
			if self.meshDialog.selectedMesh is None:
				return False
			else:
				meshLayer = tuflowqgis_find_layer(self.meshDialog.selectedMesh)
		else:
			meshLayer = self.tuView.tuResults.tuResults2D.activeMeshLayers[0]
			
		# get data provider and renderer settings
		dp = meshLayer.dataProvider()
		rs = meshLayer.rendererSettings()
		
		# get the active scalar dataset
		if useClicked:
			resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
			for i in range(dp.datasetGroupCount()):
				if dp.datasetGroupMetadata(i).name() == resultType or dp.datasetGroupMetadata(i).name() == '{0}/Maximums'.format(resultType):
					activeVectorGroupIndex = i
					break
		else:
			activeVector = rs.activeVectorDataset()
			activeVectorGroupIndex = activeVector.group()
			if activeVectorGroupIndex == -1:
				QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Vector Dataset')
				return False
		activeVectorType = dp.datasetGroupMetadata(activeVectorGroupIndex).name()
		activeVectorType = activeVectorType.strip('/Maximums')
		rsVector = rs.vectorSettings(activeVectorGroupIndex)
		
		# get vector properties
		properties = {
			'arrow head length ratio': rsVector.arrowHeadLengthRatio(),
			'arrow head width ratio': rsVector.arrowHeadWidthRatio(),
			'color': rsVector.color(),
			'filter max': rsVector.filterMax(),
			'filter min': rsVector.filterMin(),
			'fixed shaft length': rsVector.fixedShaftLength(),
			'line width': rsVector.lineWidth(),
			'max shaft length': rsVector.maxShaftLength(),
			'min shaft length': rsVector.minShaftLength(),
			'scale factor': rsVector.scaleFactor(),
			'shaft length method': rsVector.shaftLengthMethod()
		}
		
		# save as default for that result type
		key = "TUFLOW_vectorRenderer/vector"
		settings = QSettings()
		settings.setValue(key, properties)
		
		QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'Saved default style for vectors')
		
		return True
	
	def loadDefaultStyleScalar(self, **kwargs):
		"""
		Loads the default scalar style for result type.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no active mesh layers
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Result Datasets')
			return False
		
		for layer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			# get renderers and data provider
			dp = layer.dataProvider()
			rs = layer.rendererSettings()
			
			# get active dataset and check if it is scalar
			if useClicked:
				resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
				if self.tuView.tuContextMenu.resultTypeContextItem.isMax:
					resultType = "{0}/Maximums".format(resultType)
				for i in range(dp.datasetGroupCount()):
					if dp.datasetGroupMetadata(i).name() == resultType:
						activeScalarGroupIndex = i
						break
			else:
				activeScalar = rs.activeScalarDataset()
				activeScalarGroupIndex = activeScalar.group()
				if not activeScalar.isValid():
					QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Scalar Dataset')
					return False
			
			# get the name and try and apply default styling
			mdGroup = dp.datasetGroupMetadata(activeScalarGroupIndex)
			if mdGroup.isScalar():  # should be scalar considering we used activeScalarDataset
				resultType = mdGroup.name().strip('/Maximums')
				# try finding if style has been saved as a ramp first
				key = 'TUFLOW_scalarRenderer/{0}_ramp'.format(resultType)
				file = QSettings().value(key)
				if file:
					self.tuView.tuResults.tuResults2D.applyScalarRenderSettings(layer, activeScalarGroupIndex, file, type='ramp')
				# else try map
				key = 'TUFLOW_scalarRenderer/{0}_map'.format(resultType)
				file = QSettings().value(key)
				if file:
					self.tuView.tuResults.tuResults2D.applyScalarRenderSettings(layer, activeScalarGroupIndex, file, type='map')
					
		return True
	
	def loadDefaultStyleVector(self, **kwargs):
		"""
		Loads the default vector style for result type.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		useClicked = kwargs['use_clicked'] if 'use_clicked' in kwargs.keys() else False
		
		# what happens if there are no active mesh layers
		if not self.tuView.tuResults.tuResults2D.activeMeshLayers:
			QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Result Datasets')
			return False
		
		for layer in self.tuView.tuResults.tuResults2D.activeMeshLayers:
			# get renderers and data provider
			dp = layer.dataProvider()
			rs = layer.rendererSettings()
			
			# get active dataset and check if it is vector
			if useClicked:
				resultType = self.tuView.tuContextMenu.resultTypeContextItem.ds_name
				if self.tuView.tuContextMenu.resultTypeContextItem.isMax:
					resultType = "{0}/Maximums".format(resultType)
				for i in range(dp.datasetGroupCount()):
					if dp.datasetGroupMetadata(i).name() == resultType:
						activeVectorGroupIndex = i
						break
			else:
				activeVector = rs.activeVectorDataset()
				if not activeVector.isValid():
					QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'No Active Scalar Dataset')
					return False
				
			# get the name and try and apply default styling
			activeVectorGroupIndex = activeVector.group()
			mdGroup = dp.datasetGroupMetadata(activeVectorGroupIndex)
			if mdGroup.isVector():  # should be vector considering we used activeScalarDataset
				resultType = mdGroup.name()
				resultType = resultType.strip('/Maximums')
				mdGroup = dp.datasetGroupMetadata(activeVectorGroupIndex)
				rsVector = rs.vectorSettings(activeVectorGroupIndex)
				vectorProperties = QSettings().value('TUFLOW_vectorRenderer/vector')
				if vectorProperties:
					self.tuView.tuResults.tuResults2D.applyVectorRenderSettings(layer, activeVectorGroupIndex, vectorProperties)
					
		return True
	
	def resetDefaultStyles(self):
		"""
		Resets all the default styles back to original i.e. none
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		settings = QSettings()
		for key in settings.allKeys():
			if 'TUFLOW_scalarRenderer' in key:
				settings.remove(key)
			elif 'TUFLOW_vectorRenderer' in key:
				settings.remove(key)
		
		QMessageBox.information(self.iface.mainWindow(), 'Tuview', 'Reset Default Styles')
				
		return True

	def batchPlotExportInitialise(self):
		"""
		Initiates the dialog - automatically loops through all features in shape file (or selection of features in
		shape file) and exports set results to CSV or Image.
		
		:return: bool -> True for successful, False for unsuccessful
		"""
		
		self.batchPlotExportDialog = TuBatchPlotExportDialog(self.tuView)
		self.batchPlotExportDialog.exec_()
		
	def batchPlotExport(self, gisLayer, resultMesh, resultTypes, timestep, features, format, outputFolder, nameField, imageFormat):
		"""
		Automatically loops through all features in shape file (or selection of features in
		shape file) and exports set results to CSV or Image.
		
		:param gisLayer: str layer name
		:param resultMesh: list -> str mesh name e.g. 'M01_5m_001'
		:param resultTypes: list -> str result type e.g. 'depth'
		:param timestep: str time step e.g. '01:00:00'
		:param features: str 'all' or 'selection'
		:param format: str 'csv' or 'image'
		:param outputFolder: str output folder
		:param nameField: str attribute field used for naming files
		:param imageFormat: str extension e.g. '.png'
		:return: bool -> True for successful, False for unsuccessful
		"""

		# get features to iterate through
		vLayer = tuflowqgis_find_layer(gisLayer)
		if features == 'all':
			featIterator = vLayer.getFeatures()
			featureCount = vLayer.featureCount()
		elif features == 'selection':
			featIterator = vLayer.getSelectedFeatures()
			featureCount = vLayer.selectedFeatureCount()
		else:
			return False
			
		# get mesh layers (QgsMeshLayer)
		mLayers = []
		for mesh in resultMesh:
			mLayers.append(tuflowqgis_find_layer(mesh))
			
		# get attribute field index for name
		if nameField is not None and nameField != '-None-':
			nameIndex = vLayer.fields().names().index(nameField)
		else:
			nameIndex = None
			
		# convert formatted time back to what can be used to get results
		if timestep:
			if timestep == 'Maximum':
				timestepKey = timestep
			else:
				timestepKey = timestep.split(':')
				timestepKey = float(timestepKey[0]) + (float(timestepKey[1]) / 60.) + (float(timestepKey[2]) / 3600.)
				timestepKey = '{0:.4f}'.format(timestepKey)
			
		# setup progress bar
		if featureCount:
			complete = 0
			self.iface.messageBar().clearWidgets()
			progressWidget = self.iface.messageBar().createMessage("Tuview",
			                                                       " Exporting {0}s . . .".format(format))
			messageBar = self.iface.messageBar()
			progress = QProgressBar()
			progress.setMaximum(100)
			progressWidget.layout().addWidget(progress)
			messageBar.pushWidget(progressWidget, duration=1)
			self.iface.mainWindow().repaint()
			pComplete = 0
			complete = 0
		# loop through features and output
		for f in featIterator:
			if vLayer.geometryType() == 0:
				if nameIndex is not None:
					name = '{0}'.format(f.attributes()[nameIndex])
				else:
					name = 'Time_Series_{0}'.format(f.id())
				self.tuView.tuPlot.tuPlot2D.plotTimeSeriesFromMap(
					vLayer, f, bypass=True, mesh=mLayers, types=resultTypes, export=format,
					export_location=outputFolder, name=name, export_format=imageFormat)
			elif vLayer.geometryType() == 1:
				if nameIndex is not None:
					name = '{0}'.format(f.attributes()[nameIndex])
				else:
					name = 'Cross_Section_{0}'.format(f.id())
				self.tuView.tuPlot.tuPlot2D.plotCrossSectionFromMap(
					vLayer, f, bypass=True, mesh=mLayers, types=resultTypes, export=format,
					export_location=outputFolder, name=name, time=timestepKey, time_formatted=timestep, export_format=imageFormat)
			else:
				return False
			complete += 1
			pComplete = complete / featureCount * 100
			progress.setValue(pComplete)

		return True
	
	def openUserPlotDataManager(self):
		"""
		Opens the user plot data manage dialog
		
		:return:
		"""
		
		self.userPlotDataDialog = TuUserPlotDataManagerDialog(self.iface, self.tuView.tuPlot.userPlotData)
		self.userPlotDataDialog.exec_()
		self.tuView.tuPlot.clearPlot(self.tuView.tabWidget.currentIndex(), retain_1d=True, retain_2d=True, retain_flow=True)
		
		return True

	def toggleMeshRender(self):
		"""
		
		
		:return:
		"""
		
		if self.tuView.tuPlot.tuPlotToolbar.meshGridAction.isChecked():
			self.tuView.tuOptions.showGrid = True
		else:
			self.tuView.tuOptions.showGrid = False
			
		self.tuView.renderMap()
		
	def exportAnimation(self):
		self.animationDialog = TuAnimationDialog(self.tuView)
		self.animationDialog.exec_()