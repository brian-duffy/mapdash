# -*- coding: utf-8 -*-

import os.path
import os #for file writing/folder actions
import shutil


class Custom_Utils:
    """
         Custom utility class for map dashboard to create and copy directories/files
                                                                                        """

    def copyDir(self,currPath, dirName, destName ):
        if isinstance(dirName, list):
            for dir in dirName:
                currentDir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'extras' + os.sep + dir
                newDir = os.path.join(os.getcwd(),currPath) + os.sep + destName + os.sep + str(dir)
                if not (os.path.exists(newDir)): shutil.copytree(currentDir, newDir)

    def copyFile(self,currPath, fileName, destName):
        currentDir = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'extras' + os.sep + destName + os.sep + fileName
        newDir = os.path.join(os.getcwd(), currPath) + os.sep + destName + os.sep + fileName
        if not (os.path.exists(newDir)): shutil.copyfile(currentDir, newDir)


    def makeDir(self, currPath, dirName):
        if isinstance(dirName, list):
            for dir in dirName:
                newDir = os.path.join(os.getcwd(),currPath, dir)
                if not (os.path.exists(newDir)): os.makedirs(newDir)

    def fileControl(self, currPath, fileDirectory, filename, editType, data):
        file = open(os.path.join(os.getcwd(),currPath) + os.sep + fileDirectory + os.sep + filename, editType)
        if isinstance(data, basestring):
            print "string passed, alter one file"
            file.write(data)
        elif isinstance(data, list):
            for str in data:
                file.write(str)
        file.close()


