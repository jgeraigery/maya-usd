#!/usr/bin/env mayapy
#
# Copyright 2020 Autodesk
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from pxr import Usd
from pxr import UsdShade

from maya import cmds
from maya import standalone
from maya.api import OpenMaya as OM

import mayaUsd.lib as mayaUsdLib

import os
import unittest

import fixturesUtils


class testUsdExportUVSetMappings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._inputPath = fixturesUtils.setUpClass(__file__)

    @classmethod
    def tearDownClass(cls):
        standalone.uninitialize()

    def baseExportUVSetMappings(self, extraOptions, expected):
        '''
        Tests that exporting multiple Maya planes with varying UV mappings
        setups results in USD data with material specializations:
        '''
        mayaFile = os.path.join(self._inputPath, 'UsdExportUVSetMappingsTest',
            'UsdExportUVSetMappingsTest.ma')
        cmds.file(mayaFile, force=True, open=True)

        # Export to USD.
        usdFilePath = os.path.abspath('UsdExportUVSetMappingsTest')
        if extraOptions["preserveUVSetNames"]:
            usdFilePath += "_preserved"
        if len(extraOptions["remapUVSetsTo"]) > 1:
            usdFilePath += "_remapped"
        usdFilePath += ".usda"
        cmds.mayaUSDExport(mergeTransformAndShape=True, file=usdFilePath,
            shadingMode='useRegistry', convertMaterialsTo=['UsdPreviewSurface'],
            materialsScopeName='Materials', legacyMaterialScope=False,
            **extraOptions)

        stage = Usd.Stage.Open(usdFilePath)

        for mesh_name, mat_name, f1_name, f2_name, f3_name in expected:
            plane_prim = stage.GetPrimAtPath(mesh_name)
            binding_api = UsdShade.MaterialBindingAPI(plane_prim)
            mat = binding_api.ComputeBoundMaterial()[0]
            self.assertEqual(mat.GetPath(), mat_name)

            self.assertEqual(mat.GetInput("file1:varname").GetAttr().Get(), f1_name)
            self.assertEqual(mat.GetInput("file2:varname").GetAttr().Get(), f2_name)
            self.assertEqual(mat.GetInput("file3:varname").GetAttr().Get(), f3_name)

        # Initial code had a bug where a material with no UV mappings would
        # specialize itself. Make sure it stays fixed:
        plane_prim = stage.GetPrimAtPath("/pPlane8")
        binding_api = UsdShade.MaterialBindingAPI(plane_prim)
        mat = binding_api.ComputeBoundMaterial()[0]
        self.assertEqual(mat.GetPath(), "/Materials/blinn2SG")
        self.assertFalse(mat.GetPrim().HasAuthoredSpecializes())

        # Gather some original information:
        expected_uvs = []
        for i in range(1, 9):
            xform_name = "|pPlane%i" % i
            selectionList = OM.MSelectionList()
            selectionList.add(xform_name)
            dagPath = selectionList.getDagPath(0)
            dagPath = dagPath.extendToShape()
            mayaMesh = OM.MFnMesh(dagPath.node())
            expected_uvs.append(("pPlane%iShape" % i, mayaMesh.getUVSetNames()))

        expected_sg = set([sg if sg.startswith('initial') else "Test:"+sg for sg in cmds.ls(type="shadingEngine")])

        expected_links = []
        for file_name in cmds.ls(type="file"):
            links = []
            for link in cmds.uvLink(texture=file_name):
                # The name of the geometry does not survive roundtripping, but
                # we know the pattern: pPlaneShapeX -> pPlaneXShape
                plugPath = link.split(".")
                selectionList = OM.MSelectionList()
                selectionList.add(link)
                mayaMesh = OM.MFnMesh(selectionList.getDependNode(0))
                meshName = mayaMesh.name()
                plugPath[0] = "Test:pPlane" + meshName[-1] + "Shape"
                links.append(".".join(plugPath))
            expected_links.append((file_name, set(links)))

        # Test roundtripping:
        cmds.file(newFile=True, force=True)

        # Import back:
        options = ["shadingMode=[[useRegistry,UsdPreviewSurface]]",
                   "primPath=/"]
        cmds.file(usdFilePath, i=True, type="USD Import",
                  ignoreVersion=True, ra=True, mergeNamespacesOnClash=False,
                  namespace="Test", pr=True, importTimeRange="combine",
                  options=";".join(options))

        # Names should have been restored:
        for mesh_name, mesh_uvs in expected_uvs:
            selectionList = OM.MSelectionList()
            selectionList.add("Test:"+mesh_name)
            mayaMesh = OM.MFnMesh(selectionList.getDependNode(0))
            self.assertEqual(mayaMesh.getUVSetNames(), mesh_uvs)

        # Same list of shading engines:
        self.assertEqual(set(cmds.ls(type="shadingEngine")), expected_sg)

        # All links correctly restored:
        for file_name, links in expected_links:
            self.assertEqual(set(cmds.uvLink(texture='Test:'+file_name)), links)

    def testExportRenamedUVSetMappings(self):
        '''
        Tests that exporting multiple Maya planes with varying UV mappings
        setups results in USD data with material specializations:
        '''
        expected = [
            ("/pPlane1", "/Materials/blinn1SG", "st", "st", "st"),
            ("/pPlane2", "/Materials/blinn1SG", "st", "st", "st"),
            ("/pPlane3", "/Materials/blinn1SG", "st", "st", "st"),
            ("/pPlane4", "/Materials/blinn1SG", "st", "st", "st"),
            ("/pPlane5", "/Materials/blinn1SG_st_st1_st2", "st", "st1", "st2"),
            ("/pPlane6", "/Materials/blinn1SG_st1_st2_st", "st1", "st2", "st"),
            ("/pPlane7", "/Materials/blinn1SG_st2_st_st1", "st2", "st", "st1"),
        ]
        self.baseExportUVSetMappings({"preserveUVSetNames": False, "remapUVSetsTo": [['','']]}, expected)

    def testExportAndPreserveUVSetMappings(self):
        '''
        Tests those material specializations when we preserve the UV set names:
        '''
        expected = [
            ("/pPlane1", '/Materials/blinn1SG_map1_map1_map1', 'map1', 'map1', 'map1'),
            ("/pPlane2", '/Materials/blinn1SG', 'st1', 'st1', 'st1'),
            ("/pPlane3", '/Materials/blinn1SG', 'st1', 'st1', 'st1'),
            ("/pPlane4", '/Materials/blinn1SG_st2_st2_st2', 'st2', 'st2', 'st2'),
            ("/pPlane5", '/Materials/blinn1SG_p5a_p5b_p5c', 'p5a', 'p5b', 'p5c'),
            ("/pPlane6", '/Materials/blinn1SG_p62_p63_p61', 'p62', 'p63', 'p61'),
            ("/pPlane7", '/Materials/blinn1SG_p7r_p7p_p7q', 'p7r', 'p7p', 'p7q'),
        ]
        self.baseExportUVSetMappings({"preserveUVSetNames": True, "remapUVSetsTo": [['','']]}, expected)

    def testExportAndRemapUVSetMappings(self):
        '''
        Tests when remapping a few names:
        '''
        expected = [
            ['/pPlane1', '/Materials/blinn1SG_mmap1_mmap1_mmap1', 'mmap1', 'mmap1', 'mmap1'],
            ['/pPlane2', '/Materials/blinn1SG', 'sst1', 'sst1', 'sst1'],
            ['/pPlane3', '/Materials/blinn1SG', 'sst1', 'sst1', 'sst1'],
            ['/pPlane4', '/Materials/blinn1SG_st_st_st', 'st', 'st', 'st'],
            ['/pPlane5', '/Materials/blinn1SG_st_st1_st2', 'st', 'st1', 'st2'],
            ['/pPlane6', '/Materials/blinn1SG_st1_st2_st', 'st1', 'st2', 'st'],
            ['/pPlane7', '/Materials/blinn1SG_st2_st_st1', 'st2', 'st', 'st1'],            
        ]
        self.baseExportUVSetMappings({"preserveUVSetNames": False, "remapUVSetsTo": [['map1','mmap1'], ["st1", "sst1"]]}, expected)

    def testSimpleMultiUVS(self):
        mayaFile = os.path.join(self._inputPath, 'UsdExportUVSetMappingsTest',
                                'multi_uv_simple.ma')
        cmds.file(mayaFile, force=True, open=True)
        cmds.select("mesh_template24x")
        testDir = os.path.abspath('UsdExportUVSetMappingsTest')
        if not os.path.exists(testDir):
            os.mkdir(testDir)

        usdFilePath = os.path.join(testDir, "multi_uv_sets.usda")

        cmds.mayaUSDExport(mergeTransformAndShape=True, file=usdFilePath,
                           shadingMode='useRegistry', convertMaterialsTo=['UsdPreviewSurface'],
                           preserveUVSetNames=False, remapUVSetsTo=[['','']], 
                           materialsScopeName='Materials', legacyMaterialScope=False,
                           selection=True)

        stage = Usd.Stage.Open(usdFilePath)

        materialPath = "/Materials/multi_uv_set_matSG"
        materialPrim = stage.GetPrimAtPath(materialPath)
        self.assertTrue(materialPrim, "Could not find material node at {}".format(materialPath))
        material = UsdShade.Material(materialPrim)

        uvMap = {
            "uv_grid_ao": "st",
            "uv_grid_ao_opacity": "st",
            "texcoord_checker_up_bc": "st1"
        }

        # Verify that both uv sets are there
        for key, value in uvMap.items():
            self.assertEqual(material.GetInput("{}:varname".format(key)).GetAttr().Get(), value)

        # Verify that things were written properly
        if not os.environ.get("MAYAUSD_PROVIDE_DEFAULT_TEXCOORD_PRIMVAR_NAME"):
            return

        for prim in materialPrim.GetChildren():
            shader = UsdShade.Shader(prim)
            if not shader:
                continue

            if shader.GetShaderId() != "UsdPrimvarReader_float2":
                continue

            varname = shader.GetInput("varname")
            (connectableAPI, outputName, outputType) = varname.GetConnectedSource()
            self.assertEqual(varname.Get(), material.GetInput(outputName).Get())


if __name__ == '__main__':
    unittest.main(verbosity=2)
