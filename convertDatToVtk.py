# =================================================================================================
# 
# AUTHOR: Matteo Smaila
# DATE: 12 and 13 April 2020
# 
# This software was written by Matteo Smaila for Massimiliano Marrazzo.
# The purpose of this software is to convert text files containing simulation output files. These
# files are generated by a custom simulator and written out to plain ASCII files, usally with .dat
# extension. This converter allows those custom files to be written in legacy .vtk file format to
# make visualisation of those simulation results possible inside ParaView.
#
# This work is licensed under the GNU General Public License v3.0
# See https://www.gnu.org/licenses/gpl-3.0.html for more details.
#
# THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN
# OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS
# IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK
# AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.  SHOULD THE PROGRAM PROVE DEFECTIVE,
# YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
# 
# IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL ANY COPYRIGHT HOLDER,
# OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU
# FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF
# THE USE OR INABILITY TO USE THE PROGRAM (INCLUDING BUT NOT LIMITED TO LOSS OF DATA OR DATA BEING
# RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO
# OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGES.
#
# =================================================================================================

import re
import os

CRACK_FILETYPE = 'c'
DAMAGE_FILETYPE = 'd'
VON_MISES_FILETYPE = 'v'

CRACK_INITIAL_NUMBER_REGEXP = r"^[0123456789\.E-]+$"
END_OF_FILE_REGEXP = r"^#+ *#+$"
TIMESTEP_LAST_LINE_REGEXP = r"^Load factor *= *[0123456789\.E-]+ *Total deformation *= *[0123456789\.E-]+ Iter *= *(\d+)$"
TITLE_REGEXP = r"^TITLE *= *\"(.*)\"$"
VARIABLES_REGEXP = r"^VARIABLES *=(?: *\"[^\"]*\",?)+$"
ZONE_REGEXP = r"^ZONE.*$"
ZONE_FULL_HEADER_REGEXP = r"^ZONE *T *= *\"([^\"]*)\" *SOLUTIONTIME *= *(\d+) *I *= *(\d+) *, *J *= *(\d+) *,.*$"
ZONE_PARTIAL_HEADER_REGEXP = r"^ZONE *T *= *(\"[^\"]*\") *SOLUTIONTIME *= *(\d+)$"


class LineReader:
    def __init__(self, file):
        self.file = file
        self.latestLine = ''
        self.pushedBack = False

    def getNextNotEmptyLine(self):
        return self.__nextLine(False)

    def peekNextNotEmptyLine(self):
        return self.__nextLine(True)

    def isEndOfFile(self):
        return not self.peekNextNotEmptyLine()

    def __nextLine(self, peeking):
        result = ''
        if self.pushedBack:
            result = self.latestLine
        else:
            while not result.strip():
                result = self.file.readline()
                if not result:
                    break
        self.pushedBack = peeking
        self.latestLine = result
        return result

    def nextLineMatches(self, regex):
        line = self.peekNextNotEmptyLine()
        match = re.search(regex, line.strip())
        return True if match else False

    def nextLineMatchesIgnoreCase(self, regex):
        line = self.peekNextNotEmptyLine()
        match = re.search(regex, line.strip(), re.IGNORECASE)
        return True if match else False



class VTKPolyData:
    def __init__(self):
        self.title = ''
        self.time = -1
        self.points = []
        self.cells = []
        self.fields = []

    def setTitle(self, title):
        self.title = title

    def setTime(self, time):
        self.time = time

    def setPoints(self, points):
        self.points = points

    def setCells(self, cells):
        self.cells = cells

    def setFields(self, fields):
        self.fields = fields

    def writeToFile(self, originalFileName, fileType):
        if not os.path.exists('./converted' + originalFileName):
            os.mkdir('./converted' + originalFileName)
        with open(self.__getFileName(originalFileName), 'w') as file:
            self.__writeHeaderToFile(file)
            self.__writePointsToFile(file)
            if fileType != VON_MISES_FILETYPE:
                self.__writeCellsToFile(file)
            self.__writePointDataToFile(file)
            file.close()

    def __getFileName(self, originalFileName):
        return './converted' + originalFileName + '/' + originalFileName + '_' + self.title.replace(" ", "") + '_' + str(self.time).zfill(6) + ".vtk"

    def __writeHeaderToFile(self, file):
        file.write('# vtk DataFile Version 3.0' + '\n')
        file.write(self.title.replace(" ", "") + '\n')
        file.write('ASCII' + '\n')
        file.write('DATASET POLYDATA' + '\n')

    def __writePointsToFile(self, file):
        file.write('POINTS ' + str(len(self.points)) + ' double' + '\n')
        for point in self.points:
            file.write(str(point[0]) + ' ' + str(point[1]) + ' ' + str(point[2]) + '\n')

    def __writeCellsToFile(self, file):
        cellSize = len(self.cells[0])
        file.write(self.__getCellType(cellSize) + ' ' + str(len(self.cells)) + ' ' + str(self.__getTotalCellsSize()) + '\n')
        for cell in self.cells:
            file.write(self.__getCellTextLine(cell) + '\n')

    def __getCellType(self, cellSize):
        if cellSize == 2:
            return 'LINES'
        else:
            return 'POLYGONS'

    def __getTotalCellsSize(self):
        result = 0
        for cell in self.cells:
            result += 1 + len(cell)
        return result

    def __getCellTextLine(self, cell):
        result = str(len(cell)) + ' '
        for pointIndex in cell:
            result += str(pointIndex) + ' '
        return result.strip()

    def __writePointDataToFile(self, file):
        file.write('POINT_DATA ' + str(len(self.points)) + '\n')
        for fieldName in self.fields.keys():
            self.__writeFieldToFile(fieldName, file)

    def __writeFieldToFile(self, fieldName, file):
        file.write('SCALARS ' + fieldName.replace(" ", "") + ' double 1' + '\n')
        file.write('LOOKUP_TABLE default' + '\n')

        field = self.fields[fieldName]
        for point in self.points:
            file.write(str(field[point]) + '\n')

    def toString(self):
        result = 'VTKPolyData:'
        result += 'title: ' + self.title + '\n'
        result += 'time: ' + str(self.time) + '\n'
        result += 'points: ' + str(self.points) + '\n'
        result += 'cells: ' + str(self.cells) + '\n'
        result += 'fields: ' + str(self.fields) + '\n'
        return result



class Zone:
    def __init__(self):
        self.title = ""
        self.solutionTime = -1
        self.rowCount = -1
        self.columnCount = -1
        self.table = []

    def setTitle(self, title):
        self.title = title

    def getTitle(self):
        return self.title

    def setSolutionTime(self, solutionTime):
        self.solutionTime = solutionTime

    def getSolutionTime(self):
        return self.solutionTime

    def setRowCount(self, rowCount):
        self.rowCount = rowCount

    def getRowCount(self):
        return self.rowCount

    def setColumnCount(self, columnCount):
        self.columnCount = columnCount

    def getColumnCount(self):
        return self.columnCount

    def addRow(self, row):
        self.table.append(row)

    def getRow(self, rowNumber):
        return self.table[rowNumber]

    def getRows(self):
        return self.table

    def readFromFile(self, timestep, lineReader):
        header = lineReader.getNextNotEmptyLine().strip()
        matchFull = re.search(ZONE_FULL_HEADER_REGEXP, header)
        matchPartial = re.search(ZONE_PARTIAL_HEADER_REGEXP, header)
        if matchFull:
            self.__readFullHeader(matchFull)
        elif matchPartial:
            self.__readPartialHeader(matchPartial)
        i = 0;
        while self.__nextRowAvailable(i, lineReader):
            row = []
            currentLine = lineReader.getNextNotEmptyLine()
            numbers = re.split(r' +', currentLine.strip())
            for j in range(self.getColumnCount()):
                element = dict()
                for k in range(len(timestep.getVariables())):
                    element[timestep.getVariable(k)] = float(numbers[j + k])
                row.append(element)
            self.addRow(row)
            i += 1

    def __readPartialHeader(self, match):
        self.title = match.group(1)
        self.solutionTime = int(match.group(2))
        self.rowCount = -1
        self.columnCount = 1

    def __readFullHeader(self, match):
        self.title = match.group(1)
        self.solutionTime = int(match.group(2))
        self.rowCount = int(match.group(3))
        self.columnCount = int(match.group(4))

    def __nextRowAvailable(self, i, lineReader):
        if self.rowCount == -1:
            if (lineReader.nextLineMatches(ZONE_REGEXP) or
                lineReader.nextLineMatchesIgnoreCase(TIMESTEP_LAST_LINE_REGEXP) or
                lineReader.nextLineMatches(END_OF_FILE_REGEXP) or
                lineReader.nextLineMatches(CRACK_INITIAL_NUMBER_REGEXP)):
                return False
            return True
        return i < self.rowCount

    def toString(self):
        result = 'title: ' + self.title + '\n'
        result += 'solutionTime: ' + str(self.solutionTime) + '\n'
        result += 'rowCount: ' + str(self.rowCount) + '\n'
        result += 'columnCount: ' + str(self.columnCount) + '\n'
        result += 'table:\n'
        for row in self.table:
            for column in row:
                for key in column.keys():
                    result += key + '=' + str(column[key]) + ' '
                result += '; '
            result += '\n'
        return result



class Timestep:
    def __init__(self):
        self.title = ""
        self.time = -1
        self.variables = []
        self.zones = []

    def setTitle(self, title):
        self.title = title

    def getTitle(self):
        return self.title

    def setTime(self, time):
        self.time = time

    def getTime(self):
        return self.time

    def addVariable(self, variable):
        self.variables.append(variable)

    def getVariables(self):
        return self.variables

    def getVariable(self, index):
        return self.variables[index]

    def addZone(self, zone):
        self.zones.append(zone)

    def getZones(self):
        return self.zones

    def readFromFile(self, lineReader, fileType):
        if fileType == CRACK_FILETYPE: # CRACK
            self.__skipNumberBeforeTitle(lineReader)
        match = re.search(TITLE_REGEXP, lineReader.getNextNotEmptyLine().strip())
        self.setTitle(match.group(1))
        match = re.search(VARIABLES_REGEXP, lineReader.getNextNotEmptyLine().strip())
        [*_, variablesText] = match.group(0).split('=')
        variables = variablesText.split(',')
        for variable in variables:
            self.addVariable(variable.strip().replace('"', ''))
        while lineReader.nextLineMatches(ZONE_REGEXP):
            zone = Zone()
            zone.readFromFile(self, lineReader)
            self.addZone(zone)
        if fileType == CRACK_FILETYPE:
            self.setTime(self.zones[0].getSolutionTime())
        else:
            match = re.search(TIMESTEP_LAST_LINE_REGEXP, lineReader.getNextNotEmptyLine().strip(), re.IGNORECASE)
            self.setTime(int(match.group(1)))

    def __skipNumberBeforeTitle(self, lineReader):
        if lineReader.nextLineMatches(CRACK_INITIAL_NUMBER_REGEXP):
            lineReader.getNextNotEmptyLine()

    def checkZonesSolutionTimes(self):
        result = True
        for zone in self.zones:
            if zone.getSolutionTime() != self.time:
                print("zone " + zone.getTitle() + " has solutionTime " + str(zone.getSolutionTime()) + " instead of " + str(self.time) + "!")
                result = False
        return result

    def convertToVTKPolyData(self):
        fields = dict()
        for variable in self.variables:
            if variable != 'X' and variable != 'Y':
                fields[variable] = dict()

        tempPoints = set()
        tempCells = []
        for zone in self.zones:
            cell = []
            for row in zone.getRows():
                for element in row:
                    point = (element['X'], element['Y'], 0.0)
                    tempPoints.add(point)
                    cell.append(point)
                    for key in fields.keys():
                        fields[key][point] = element[key]
            tempCells.append(cell)

        points = []
        for point in tempPoints:
            points.append(point)

        cells = []
        for tempCell in tempCells:
            cell = []
            for point in tempCell:
                cell.append(points.index(point))
            cells.append(cell)

        result = VTKPolyData()
        result.setTitle(self.title)
        result.setTime(self.time)
        result.setPoints(points)
        result.setCells(cells)
        result.setFields(fields)
        return result

    def toString(self):
        result = 'title: ' + self.title + '\n'
        result += 'time: ' + str(self.time) + '\n'
        result += 'variables: '
        for variable in self.variables:
            result += variable + ' '
        result += '\n'
        result += 'zones:\n'
        for zone in self.zones:
            result += zone.toString()
            result += '\n'
        return result



# =============================================================================
#
#                                CONVERTER SCRIPT
#
# =============================================================================

print('Specify input file path:')
scriptPath = input()

print('Specify type of file (d for DAMAGE, c for CRACK, v for VON MISES [d/c/v]:')
fileType = input()
while fileType not in (CRACK_FILETYPE, DAMAGE_FILETYPE, VON_MISES_FILETYPE):
    print('Wrong type selected!')
    print('Specify type of file (d for DAMAGE, c for CRACK, v for VON MISES [d/c/v]:')
    fileType = input()

originalFileName = ''
match = re.match(r"(?:.*\/)?(.*)\..*$", scriptPath)
if match:
    originalFileName = match.group(1)
    with open(scriptPath) as file:
        lineReader = LineReader(file)
        success = True
        while not lineReader.nextLineMatches(END_OF_FILE_REGEXP) and not lineReader.isEndOfFile():
            timestep = Timestep()
            timestep.readFromFile(lineReader, fileType)
            if timestep.checkZonesSolutionTimes():
                polyData = timestep.convertToVTKPolyData()
                polyData.writeToFile(originalFileName, fileType)
            else:
                print('ERROR - there is a ZONE with wrong SOLUTIONTIME')
                success = False
                break
        file.close()
        if success:
            print('Conversion done! Exiting...')
else:
    print('Invalid path')